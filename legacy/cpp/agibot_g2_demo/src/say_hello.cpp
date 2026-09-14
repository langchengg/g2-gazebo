#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>

#include "agibot_g2_demo/core.hpp"
#include "rcl_interfaces/msg/parameter_descriptor.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "std_msgs/msg/string.hpp"
#include "std_srvs/srv/trigger.hpp"

namespace {
double steady_seconds() {
  return std::chrono::duration<double>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
}

std::string json_string(const std::string &value) {
  std::ostringstream stream;
  stream << '"';
  for (const unsigned char c : value) {
    if (c == '"' || c == '\\') { stream << '\\' << c; }
    else if (c == '\n') { stream << "\\n"; }
    else if (c == '\r') { stream << "\\r"; }
    else if (c == '\t') { stream << "\\t"; }
    else if (c < 0x20) { stream << '?'; }
    else { stream << c; }
  }
  stream << '"';
  return stream.str();
}

// Only this node owns a RobotBackend. All calls are serialized by the default
// mutually exclusive callback group and the single-threaded executor below.
class SayHello final : public rclcpp::Node {
 public:
  SayHello() : Node("sayHello", "/g2") {
    agibot_g2_demo::Config config;
    config.backend = parameter<std::string>("backend", config.backend);
    config.enable_motion = parameter<bool>("enable_motion", config.enable_motion);
    config.target_joint = parameter<std::string>("target_joint", config.target_joint);
    config.displacement = parameter<double>("displacement", config.displacement);
    config.duration = parameter<double>("duration", config.duration);
    config.publish_hz = parameter<double>("publish_hz", config.publish_hz);
    config.max_displacement = parameter<double>("max_displacement", config.max_displacement);
    config.max_velocity = parameter<double>("max_velocity", config.max_velocity);
    config.max_acceleration = parameter<double>("max_acceleration", config.max_acceleration);
    config.position_limit = parameter<double>("position_limit", config.position_limit);
    config.feedback_timeout = parameter<double>("feedback_timeout", config.feedback_timeout);
    config.watchdog_timeout = parameter<double>("watchdog_timeout", config.watchdog_timeout);
    config.motion_timeout = parameter<double>("motion_timeout", config.motion_timeout);
    config.position_tolerance = parameter<double>("position_tolerance", config.position_tolerance);
    config.velocity_tolerance = parameter<double>("velocity_tolerance", config.velocity_tolerance);
    config.stable_duration = parameter<double>("stable_duration", config.stable_duration);
    config.tracking_time_constant = parameter<double>("tracking_time_constant", config.tracking_time_constant);
    fault_mode_ = parameter<std::string>("fault_mode", "none");
    fault_after_ = parameter<double>("fault_after", 0.5);
    if (!agibot_g2_demo::valid_fault(fault_mode_) || !std::isfinite(fault_after_) ||
        fault_after_ < 0.0 || fault_after_ > 60.0) {
      throw std::invalid_argument("invalid mock fault_mode or fault_after outside [0,60] seconds");
    }
    // Faults are deliberately delayed until an accepted mock run. This allows
    // tests to acquire a genuine baseline before disrupting the observation.
    config.fault = "none";
    engine_ = std::make_unique<agibot_g2_demo::Engine>(config);
    rcl_interfaces::msg::ParameterDescriptor source_descriptor;
    source_descriptor.read_only = true;
    source_descriptor.description = "Actual backend, cannot be overridden independently";
    declare_parameter<std::string>("source", config.backend, source_descriptor, true);
    publisher_ = create_publisher<sensor_msgs::msg::JointState>(
      "internal/joint_states", rclcpp::QoS(10).reliable().durability_volatile());
    status_publisher_ = create_publisher<std_msgs::msg::String>(
      "hello_status", rclcpp::QoS(1).reliable().transient_local());
    service_ = create_service<std_srvs::srv::Trigger>("say_hello",
      [this](const std_srvs::srv::Trigger::Request::SharedPtr,
             std_srvs::srv::Trigger::Response::SharedPtr response) {
        const double current = steady_seconds();
        const auto result = engine_->request(current);
        response->success = result.accepted;
        response->message = "{\"source\":\"mock\",\"run_id\":" +
          json_string(result.run_id) + ",\"reason\":" + json_string(result.reason) + "}";
        if (result.accepted) {
          run_started_ = current;
          fault_applied_ = false;
        }
        publish_status(current, true);
      }, rmw_qos_profile_services_default);
    const double tick_hz = std::max(50.0, config.publish_hz);
    timer_ = create_wall_timer(
      std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::duration<double>(1.0 / tick_hz)), [this]() { tick(); });
    publish_status(steady_seconds(), true);
    RCLCPP_INFO(get_logger(), "source=mock enable_motion=%s; startup never requests movement; synthetic joints only",
      config.enable_motion ? "true" : "false");
  }

  void stop() {
    if (timer_) { timer_->cancel(); }
    if (engine_) { engine_->shutdown(steady_seconds()); }
  }

  ~SayHello() override { stop(); }

 private:
  template<typename T> T parameter(const std::string &name, const T &fallback) {
    rcl_interfaces::msg::ParameterDescriptor descriptor;
    descriptor.read_only = true;
    descriptor.description = "Project configuration; mock values are not G2 safety limits; restart to change";
    return declare_parameter<T>(name, fallback, descriptor);
  }

  void tick() {
    const double current = steady_seconds();
    const rclcpp::Time ros_sample_time = now();
    if (engine_->status().state == agibot_g2_demo::MotionState::RUNNING &&
        !fault_applied_ && fault_mode_ != "none" && current - run_started_ >= fault_after_) {
      engine_->set_fault(fault_mode_);
      fault_applied_ = true;
      RCLCPP_WARN(get_logger(), "injecting synthetic fault_mode=%s", fault_mode_.c_str());
    }
    engine_->tick(current);
    const auto &observation = engine_->observation();
    if (observation && (!observed_sequence_ || observation->sequence != *observed_sequence_)) {
      observed_sequence_ = observation->sequence;
      // The mock sampling and ROS observation clocks are read in this callback.
      // This local mapping is specific to the synthetic backend, never G2 time.
      mapped_stamp_ = ros_sample_time;
    }
    if (current >= next_publication_) {
      if (observation && mapped_stamp_ && engine_->healthy(current) &&
          (!published_sequence_ || observation->sequence != *published_sequence_) &&
          agibot_g2_demo::validate_observation(*observation).empty()) {
        sensor_msgs::msg::JointState message;
        message.header.stamp = *mapped_stamp_;
        message.header.frame_id = "mock_joint_observation";
        message.name = observation->names;
        message.position = observation->positions;
        message.velocity = observation->velocities;
        message.effort = observation->efforts;
        publisher_->publish(message);
        published_sequence_ = observation->sequence;
      }
      // One current sample at most, with no catch-up burst of historical commands.
      const double period = 1.0 / engine_->config().publish_hz;
      next_publication_ += period;
      if (next_publication_ <= current) { next_publication_ = current + period; }
    }
    publish_status(current, false);
  }

  void publish_status(double current, bool force) {
    const auto &status = engine_->status();
    const std::string payload = "{\"source\":\"mock\",\"state\":" +
      json_string(agibot_g2_demo::state_name(status.state)) +
      ",\"run_id\":" + json_string(status.run_id) +
      ",\"reason\":" + json_string(status.reason) +
      ",\"healthy\":" + (engine_->healthy(current) ? "true" : "false") +
      ",\"health_reason\":" + json_string(engine_->health_reason(current)) + "}";
    if (force || payload != last_status_ || current - last_status_time_ >= 0.5) {
      std_msgs::msg::String message;
      message.data = payload;
      status_publisher_->publish(message);
      if (payload != last_status_) {
        RCLCPP_INFO(get_logger(), "%s", payload.c_str());
      }
      last_status_ = payload;
      last_status_time_ = current;
    }
  }

  std::unique_ptr<agibot_g2_demo::Engine> engine_;
  std::string fault_mode_;
  double fault_after_{0.5};
  double run_started_{0.0};
  bool fault_applied_{false};
  double next_publication_{0.0};
  std::optional<std::uint64_t> observed_sequence_;
  std::optional<std::uint64_t> published_sequence_;
  std::optional<rclcpp::Time> mapped_stamp_;
  std::string last_status_;
  double last_status_time_{0.0};
  rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr publisher_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_publisher_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr service_;
  rclcpp::TimerBase::SharedPtr timer_;
};
}  // namespace

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  int result = 0;
  try {
    auto node = std::make_shared<SayHello>();
    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(node);
    executor.spin();
    node->stop();
  } catch (const std::exception &error) {
    std::fprintf(stderr, "sayHello fatal: %s\n", error.what());
    result = 2;
  }
  rclcpp::shutdown();
  return result;
}
