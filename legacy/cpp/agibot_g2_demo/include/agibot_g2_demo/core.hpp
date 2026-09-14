#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace agibot_g2_demo {

// Every name, parameter and API in this header belongs to this demo, not GDK.
struct Config {
  std::string backend{"mock"};
  bool enable_motion{false};
  std::string target_joint{"mock_left_arm_joint1"};
  double displacement{0.05};                 // mock radians, signed
  double duration{4.0};                      // desired round trip seconds
  double publish_hz{10.0};
  double max_displacement{0.1};
  double max_velocity{0.2};                  // rad/s, command profile bound
  double max_acceleration{0.5};              // rad/s^2, command profile bound
  double position_limit{1.0};                // symmetric synthetic joint bound
  double feedback_timeout{0.6};              // monotonic receive/progress age
  double watchdog_timeout{0.5};              // maximum tick scheduling gap
  double motion_timeout{7.0};
  double position_tolerance{0.002};
  double velocity_tolerance{0.01};
  double stable_duration{0.2};
  double tracking_time_constant{0.08};
  std::string fault{"none"};                 // deterministic, mock only
};

struct Observation {
  std::vector<std::string> names;
  std::vector<double> positions;
  std::vector<double> velocities;            // empty means unavailable
  std::vector<double> efforts;               // mock never invents effort
  std::uint64_t sequence{0};
  double sample_time{0.0};                   // injected local monotonic seconds
};

std::vector<std::string> mock_joint_names();
void validate_config(const Config &config);  // throws std::invalid_argument
std::string validate_observation(const Observation &observation);
bool valid_fault(const std::string &fault);

class SourceFreshness {
 public:
  explicit SourceFreshness(double timeout);
  // Source time is used ONLY to check progression, never subtracted from local time.
  // Both supplied source markers must advance; unknown markers may be omitted.
  bool observe(std::optional<std::uint64_t> sequence,
               std::optional<double> source_time, double receive_time);
  bool healthy(double now) const;
  std::string reason(double now) const;
 private:
  double timeout_;
  bool seen_{false};
  bool valid_{false};
  std::optional<std::uint64_t> sequence_;
  std::optional<double> source_time_;
  double last_receive_{0.0};
  double last_progress_{0.0};
  std::string invalid_reason_;
};

class RobotBackend {
 public:
  virtual ~RobotBackend() = default;
  virtual std::optional<Observation> poll(double now) = 0;
  virtual void command_positions(const std::vector<double> &positions, double now) = 0;
  virtual void hold(double now) = 0;
  virtual void set_fault(const std::string &fault) = 0;
};

// "gdk" always throws in this SDK-free build. There is no fallback.
std::unique_ptr<RobotBackend> make_backend(const Config &config);

enum class MotionState { IDLE, RUNNING, SUCCEEDED, FAILED };
std::string state_name(MotionState state);
struct Status {
  MotionState state{MotionState::IDLE};
  std::string run_id;
  std::string reason{"ready; no automatic motion"};
};
struct RequestResult {
  bool accepted{false};
  std::string run_id;
  std::string reason;
};

// Single-owner API: wrapper must serialize tick/request/shutdown/set_fault.
// No threads or sleeps; callers inject std::chrono::steady_clock time in seconds.
class Engine {
 public:
  explicit Engine(Config config, std::unique_ptr<RobotBackend> backend = nullptr);
  ~Engine();
  void tick(double now);
  RequestResult request(double now);
  void shutdown(double now);
  void set_fault(const std::string &fault);
  const std::optional<Observation> &observation() const { return observation_; }
  const Status &status() const { return status_; }
  bool healthy(double now) const;
  std::string health_reason(double now) const;
  const Config &config() const { return config_; }
 private:
  void fail(const std::string &reason, double now);
  Config config_;
  std::unique_ptr<RobotBackend> backend_;
  SourceFreshness freshness_;
  std::optional<Observation> observation_;
  Status status_;
  std::string process_id_;
  std::uint64_t request_count_{0};
  bool stopped_{false};
  bool backend_ok_{true};
  bool fault_latched_{false};
  std::string backend_error_;
  std::optional<double> last_tick_;
  double started_{0.0};
  std::optional<double> stable_since_;
  std::vector<double> baseline_;
  std::size_t target_index_{0};
  bool observed_excursion_{false};
};

}  // namespace agibot_g2_demo
