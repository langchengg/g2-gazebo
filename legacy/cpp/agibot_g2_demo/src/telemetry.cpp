#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "agibot_g2_demo/core.hpp"
#include "rcl_interfaces/msg/parameter_descriptor.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "std_msgs/msg/string.hpp"

namespace {
using SteadyClock = std::chrono::steady_clock;
double steady_seconds() {
  return std::chrono::duration<double>(SteadyClock::now().time_since_epoch()).count();
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

class Telemetry final : public rclcpp::Node {
 public:
  Telemetry() : Node("telemetry", "/g2") {
    const auto backend = parameter<std::string>("backend", "mock");
    if (backend != "mock") {
      throw std::invalid_argument(backend == "gdk" ?
        "GDK backend BLOCKED/UNIMPLEMENTED: no verified SDK adapter; refusing mock fallback" :
        "backend must be mock or gdk");
    }
    if (get_parameter("use_sim_time").as_bool()) {
      throw std::invalid_argument(
        "mock telemetry requires use_sim_time=false and the owner's local ROS system-time domain");
    }
    clock_parameter_guard_ = add_on_set_parameters_callback(
      [](const std::vector<rclcpp::Parameter> &parameters) {
        rcl_interfaces::msg::SetParametersResult result;
        result.successful = true;
        for (const auto &value : parameters) {
          if (value.get_name() == "use_sim_time" &&
              (value.get_type() != rclcpp::ParameterType::PARAMETER_BOOL || value.as_bool())) {
            result.successful = false;
            result.reason = "mock telemetry requires use_sim_time=false; source age uses local ROS system time";
            break;
          }
        }
        return result;
      });
    rcl_interfaces::msg::ParameterDescriptor source_descriptor;
    source_descriptor.read_only = true;
    source_descriptor.description = "Actual implementation source, cannot be overridden";
    declare_parameter<std::string>("source", backend, source_descriptor, true);
    publish_hz_ = parameter<double>("publish_hz", 10.0);
    timeout_ = parameter<double>("feedback_timeout", 0.6);
    future_tolerance_ = parameter<double>("future_tolerance", 0.05);
    if (!std::isfinite(publish_hz_) || publish_hz_ <= 0.0 || publish_hz_ > 50.0 ||
        !std::isfinite(timeout_) || timeout_ <= 0.0) {
      throw std::invalid_argument("publish_hz must be in (0,50] and feedback_timeout finite and positive");
    }
    if (!std::isfinite(future_tolerance_) || future_tolerance_ < 0.0 || future_tolerance_ > 0.1) {
      throw std::invalid_argument("future_tolerance must be finite and in [0,0.1] seconds for local mock timestamps");
    }
    freshness_ = std::make_unique<agibot_g2_demo::SourceFreshness>(timeout_);
    publisher_ = create_publisher<sensor_msgs::msg::JointState>(
      "joint_states", rclcpp::QoS(10).reliable().durability_volatile());
    health_publisher_ = create_publisher<std_msgs::msg::String>(
      "telemetry_health", rclcpp::QoS(1).reliable().transient_local());
    subscription_ = create_subscription<sensor_msgs::msg::JointState>(
      "internal/joint_states", rclcpp::QoS(10).reliable().durability_volatile(),
      [this](sensor_msgs::msg::JointState::ConstSharedPtr message) { receive(*message); });
    timer_ = create_wall_timer(std::chrono::milliseconds(100), [this]() { health(); });
    started_ = steady_seconds();
    publish_health("WAITING", "waiting for a valid advancing source observation");
    RCLCPP_INFO(get_logger(), "source=mock; JointState radians/rad/s; effort unavailable; source timestamps are local ROS observation time, never hardware time");
  }

 private:
  template<typename T> T parameter(const std::string &name, const T &fallback) {
    rcl_interfaces::msg::ParameterDescriptor descriptor;
    descriptor.read_only = true;
    descriptor.description = "Project configuration; restart to change";
    return declare_parameter<T>(name, fallback, descriptor);
  }

  std::pair<std::string, std::string> check_mock_sample_age(std::int64_t stamp) {
    // This subtraction is justified ONLY for the demo's co-located mock nodes:
    // the owner stamps with local ROS system time and simulated time is rejected.
    // A future GDK adapter must establish its own hardware-clock mapping first.
    if (get_parameter("use_sim_time").as_bool() || get_clock()->ros_time_is_active()) {
      return {"INVALID", "mock local ROS system-time domain unavailable; use_sim_time must remain false"};
    }
    const auto local_ros_time = now().nanoseconds();
    if (local_ros_time <= 0) {
      return {"INVALID", "mock local ROS system time is unset or invalid"};
    }
    const double age = static_cast<double>(
      (static_cast<long double>(local_ros_time) - static_cast<long double>(stamp)) * 1.0e-9L);
    if (!std::isfinite(age)) {
      return {"INVALID", "mock source sample age is not finite"};
    }
    if (age < -future_tolerance_) {
      return {"INVALID", "mock source sample is in the future beyond future_tolerance"};
    }
    if (age > timeout_) {
      return {"STALE", "mock source sample expired: age exceeds feedback_timeout"};
    }
    return {};
  }

  void receive(const sensor_msgs::msg::JointState &message) {
    const double received = steady_seconds();
    agibot_g2_demo::Observation observation;
    observation.names = message.name;
    observation.positions = message.position;
    observation.velocities = message.velocity;
    observation.efforts = message.effort;
    const auto error = agibot_g2_demo::validate_observation(observation);
    if (!error.empty() || message.name != agibot_g2_demo::mock_joint_names()) {
      invalid_ = error.empty() ? "unexpected joint names or order" : error;
      publish_health("INVALID", invalid_);
      return;
    }
    if (message.header.stamp.sec < 0 || message.header.stamp.nanosec >= 1000000000U ||
        (message.header.stamp.sec == 0 && message.header.stamp.nanosec == 0)) {
      invalid_ = "invalid or unset source timestamp";
      publish_health("INVALID", invalid_);
      return;
    }
    const std::int64_t stamp = static_cast<std::int64_t>(message.header.stamp.sec) *
      1000000000LL + message.header.stamp.nanosec;
    rejected_time_ = check_mock_sample_age(stamp);
    if (!rejected_time_.first.empty()) {
      invalid_.clear();
      publish_health(rejected_time_.first, rejected_time_.second);
      return;
    }
    // SourceFreshness independently compares exact integer source markers and
    // uses monotonic time for receive/progress timeouts. Rejected old/future
    // samples never renew either source freshness or the accepted stamp.
    const bool advanced = freshness_->observe(
      static_cast<std::uint64_t>(stamp), std::nullopt, received);
    if (!advanced) {
      invalid_.clear();
      non_advancing_ = true;
      publish_health("STALE", "source timestamp did not advance: " + freshness_->reason(received));
      return;
    }
    invalid_.clear();
    non_advancing_ = false;
    seen_ = true;
    accepted_stamp_ = stamp;
    arrivals_.push_back(received);
    while (arrivals_.size() > 1 && received - arrivals_.front() > 5.0) {
      arrivals_.pop_front();
    }
    // The owner sets the configured source rate. Forward each new source sample
    // once; an arrival-time throttle would incorrectly drop jittered samples.
    // Lower source rates remain lower: no interpolation or repeated samples.
    publisher_->publish(message);
    ++published_;
    publish_health("HEALTHY", "valid advancing source observation");
  }

  void health() {
    const double current = steady_seconds();
    if (!invalid_.empty()) {
      publish_health("INVALID", invalid_);
    } else if (!rejected_time_.first.empty()) {
      publish_health(rejected_time_.first, rejected_time_.second);
    } else if (non_advancing_) {
      publish_health("STALE", "source timestamp did not advance: " + freshness_->reason(current));
    } else if (!seen_ && current - started_ < timeout_) {
      publish_health("WAITING", "waiting for source observation");
    } else if (!freshness_->healthy(current)) {
      publish_health("STALE", freshness_->reason(current));
    } else if (accepted_stamp_) {
      const auto time_issue = check_mock_sample_age(*accepted_stamp_);
      if (!time_issue.first.empty()) {
        publish_health(time_issue.first, time_issue.second);
      } else {
        publish_health("HEALTHY", "valid advancing source observation");
      }
    } else {
      publish_health("HEALTHY", "valid advancing source observation");
    }
  }

  void publish_health(const std::string &status, const std::string &reason) {
    const double current = steady_seconds();
    double source_hz = 0.0;
    if (arrivals_.size() >= 2 && current - arrivals_.back() <= timeout_) {
      source_hz = static_cast<double>(arrivals_.size() - 1) /
        (arrivals_.back() - arrivals_.front());
    }
    std::ostringstream payload;
    payload << "{\"source\":\"mock\",\"status\":" << json_string(status)
      << ",\"reason\":" << json_string(reason)
      << ",\"source_hz\":" << source_hz
      << ",\"configured_hz\":" << publish_hz_
      << ",\"future_tolerance_s\":" << future_tolerance_
      << ",\"source_clock_domain\":\"mock_local_ros_system_time\""
      << ",\"source_rate_basis\":\"unique_samples_local_receive_time\""
      << ",\"published_samples\":" << published_
      << ",\"stamp_kind\":\"local_ros_observation_time\",\"position_unit\":\"rad\"}";
    std_msgs::msg::String message;
    message.data = payload.str();
    health_publisher_->publish(message);
    if (status != last_health_) {
      if (status == "STALE" || status == "INVALID") {
        RCLCPP_WARN(get_logger(), "source=mock status=%s reason=%s", status.c_str(), reason.c_str());
      }
      last_health_ = status;
    }
  }

  double publish_hz_{10.0};
  double timeout_{0.6};
  double future_tolerance_{0.05};
  double started_{0.0};
  bool seen_{false};
  bool non_advancing_{false};
  std::string invalid_;
  std::string last_health_;
  std::pair<std::string, std::string> rejected_time_;
  std::optional<std::int64_t> accepted_stamp_;
  std::unique_ptr<agibot_g2_demo::SourceFreshness> freshness_;
  std::deque<double> arrivals_;
  std::uint64_t published_{0};
  rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr publisher_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr health_publisher_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr clock_parameter_guard_;
};
}  // namespace

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  int result = 0;
  try {
    rclcpp::spin(std::make_shared<Telemetry>());
  } catch (const std::exception &error) {
    std::fprintf(stderr, "telemetry fatal: %s\n", error.what());
    result = 2;
  }
  rclcpp::shutdown();
  return result;
}
