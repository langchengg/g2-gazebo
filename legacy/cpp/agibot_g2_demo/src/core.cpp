#include "agibot_g2_demo/core.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace agibot_g2_demo {
namespace {

void positive(double value, const char *name) {
  if (!std::isfinite(value) || value <= 0.0) {
    throw std::invalid_argument(std::string(name) + " must be finite and positive");
  }
}

bool finite_values(const std::vector<double> &values) {
  return std::all_of(values.begin(), values.end(), [](double v) { return std::isfinite(v); });
}

// q(u)=10u^3-15u^4+6u^5 has zero endpoint velocity and acceleration.
double smoothstep(double u) {
  u = std::clamp(u, 0.0, 1.0);
  return u * u * u * (10.0 + u * (-15.0 + 6.0 * u));
}

class MockBackend final : public RobotBackend {
 public:
  explicit MockBackend(const Config &config) : config_(config), fault_(config.fault) {
    const double scale = std::min(0.1, config_.position_limit * 0.25);
    positions_ = {scale, -scale, 0.5 * scale, -0.5 * scale, 0.75 * scale, -0.75 * scale};
    commands_ = positions_;
  }

  std::optional<Observation> poll(double now) override {
    if (!std::isfinite(now)) throw std::runtime_error("invalid mock clock");
    if (last_time_ && now < *last_time_) throw std::runtime_error("mock clock moved backward");
    if (fault_ == "error") throw std::runtime_error("injected mock backend error");
    if (fault_ == "watchdog") throw std::runtime_error("injected mock backend watchdog failure");
    if (fault_ == "freeze") return std::nullopt;
    if (fault_ == "repeat" && cached_) return cached_;
    if (last_time_ && now == *last_time_) return cached_;

    std::vector<double> velocities(positions_.size(), 0.0);
    if (last_time_) {
      const double dt = now - *last_time_;
      // Exact integration of a first-order follower under the previous held command.
      // A timeout fault leaves the physical state stationary but keeps observations fresh.
      const double alpha = fault_ == "timeout" ? 0.0 : -std::expm1(-dt / config_.tracking_time_constant);
      for (std::size_t i = 0; i < positions_.size(); ++i) {
        const double change = alpha * (commands_[i] - positions_[i]);
        positions_[i] += change;
        velocities[i] = change / dt;
      }
    }
    last_time_ = now;
    Observation result{mock_joint_names(), positions_, velocities, {}, ++sequence_, now};
    if (fault_ == "nan") result.positions.front() = std::numeric_limits<double>::quiet_NaN();
    if (fault_ == "inf") result.positions.front() = std::numeric_limits<double>::infinity();
    if (fault_ == "invalid") result.positions.pop_back();
    cached_ = result;
    return result;
  }

  void command_positions(const std::vector<double> &positions, double now) override {
    if (!std::isfinite(now) || positions.size() != positions_.size() || !finite_values(positions)) {
      throw std::invalid_argument("invalid mock command dimensions, clock or numbers");
    }
    for (double value : positions) {
      if (std::abs(value) > config_.position_limit) throw std::invalid_argument("mock command exceeds position limit");
    }
    commands_ = positions;
  }

  void hold(double) override {
    // Freeze at the actual simulated state. Never issue a return-to-start command.
    commands_ = positions_;
  }

  void set_fault(const std::string &fault) override {
    if (!valid_fault(fault)) throw std::invalid_argument("unknown mock fault: " + fault);
    fault_ = fault;
  }

 private:
  Config config_;
  std::string fault_;
  std::vector<double> positions_;
  std::vector<double> commands_;
  std::optional<double> last_time_;
  std::uint64_t sequence_{0};
  std::optional<Observation> cached_;
};

}  // namespace

std::vector<std::string> mock_joint_names() {
  return {"mock_left_arm_joint1", "mock_left_arm_joint2", "mock_left_arm_joint3",
          "mock_right_arm_joint1", "mock_right_arm_joint2", "mock_right_arm_joint3"};
}

bool valid_fault(const std::string &fault) {
  return fault == "none" || fault == "freeze" || fault == "repeat" || fault == "error" ||
         fault == "nan" || fault == "inf" || fault == "invalid" || fault == "timeout" || fault == "watchdog";
}

void validate_config(const Config &c) {
  if (c.backend != "mock" && c.backend != "gdk") throw std::invalid_argument("backend must be mock or gdk");
  const auto names = mock_joint_names();
  if (c.backend == "mock" && std::find(names.begin(), names.end(), c.target_joint) == names.end()) {
    throw std::invalid_argument("target_joint is not a synthetic mock joint");
  }
  if (!valid_fault(c.fault)) throw std::invalid_argument("unknown mock fault: " + c.fault);
  positive(c.duration, "duration");
  positive(c.publish_hz, "publish_hz");
  positive(c.max_displacement, "max_displacement");
  positive(c.max_velocity, "max_velocity");
  positive(c.max_acceleration, "max_acceleration");
  positive(c.position_limit, "position_limit");
  positive(c.feedback_timeout, "feedback_timeout");
  positive(c.watchdog_timeout, "watchdog_timeout");
  positive(c.motion_timeout, "motion_timeout");
  positive(c.position_tolerance, "position_tolerance");
  positive(c.velocity_tolerance, "velocity_tolerance");
  positive(c.stable_duration, "stable_duration");
  positive(c.tracking_time_constant, "tracking_time_constant");
  if (c.publish_hz > 50.0) throw std::invalid_argument("publish_hz cannot exceed the 50 Hz mock source tick");
  if (!std::isfinite(c.displacement) || c.displacement == 0.0 || std::abs(c.displacement) > c.max_displacement) {
    throw std::invalid_argument("displacement must be finite, nonzero and within max_displacement");
  }
  const double half = c.duration * 0.5;
  const double peak_velocity = 1.875 * std::abs(c.displacement) / half;
  const double peak_acceleration = (10.0 / std::sqrt(3.0)) * std::abs(c.displacement) / (half * half);
  if (!std::isfinite(peak_velocity) || peak_velocity > c.max_velocity) {
    throw std::invalid_argument("quintic mock profile exceeds max_velocity");
  }
  if (!std::isfinite(peak_acceleration) || peak_acceleration > c.max_acceleration) {
    throw std::invalid_argument("quintic mock profile exceeds max_acceleration");
  }
  if (c.position_tolerance >= std::abs(c.displacement) * 0.25) {
    throw std::invalid_argument("position_tolerance must be less than one quarter of displacement magnitude");
  }
  if (!std::isfinite(c.duration + c.stable_duration) || c.motion_timeout <= c.duration + c.stable_duration) {
    throw std::invalid_argument("motion_timeout must exceed duration plus stable_duration");
  }
}

std::string validate_observation(const Observation &o) {
  if (o.names.empty()) return "empty joint names";
  if (o.positions.size() != o.names.size()) return "position/name dimension mismatch";
  if ((!o.velocities.empty() && o.velocities.size() != o.names.size()) ||
      (!o.efforts.empty() && o.efforts.size() != o.names.size())) return "optional array dimension mismatch";
  std::set<std::string> unique;
  for (const auto &name : o.names) {
    if (name.empty() || !unique.insert(name).second) return "empty or duplicate joint name";
  }
  if (!finite_values(o.positions) || !finite_values(o.velocities) || !finite_values(o.efforts)) return "non-finite joint value";
  if (!std::isfinite(o.sample_time)) return "non-finite source timestamp";
  return {};
}

SourceFreshness::SourceFreshness(double timeout) : timeout_(timeout) { positive(timeout, "freshness timeout"); }

bool SourceFreshness::observe(std::optional<std::uint64_t> sequence,
                              std::optional<double> source_time, double receive_time) {
  if (!std::isfinite(receive_time) || (source_time && !std::isfinite(*source_time))) {
    valid_ = false;
    invalid_reason_ = "non-finite freshness timestamp";
    return false;
  }
  if (seen_ && receive_time < last_receive_) {
    valid_ = false;
    invalid_reason_ = "local monotonic clock moved backward";
    return false;
  }
  if (seen_ && (sequence.has_value() != sequence_.has_value() || source_time.has_value() != source_time_.has_value())) {
    valid_ = false;
    invalid_reason_ = "source marker availability changed";
    return false;
  }
  last_receive_ = receive_time;
  if (seen_ && ((sequence && *sequence < *sequence_) || (source_time && *source_time < *source_time_))) {
    valid_ = false;
    invalid_reason_ = "source marker moved backward";
    return false;
  }
  if (seen_ && ((sequence && *sequence == *sequence_) || (source_time && *source_time == *source_time_))) {
    return false;
  }
  sequence_ = sequence;
  source_time_ = source_time;
  last_progress_ = receive_time;
  seen_ = true;
  valid_ = true;
  invalid_reason_.clear();
  return true;
}

bool SourceFreshness::healthy(double now) const {
  return seen_ && valid_ && std::isfinite(now) && now >= last_receive_ &&
         now - last_receive_ <= timeout_ && now - last_progress_ <= timeout_;
}

std::string SourceFreshness::reason(double now) const {
  if (!std::isfinite(now)) return "non-finite local clock";
  if (!seen_) return invalid_reason_.empty() ? "waiting for first observation" : invalid_reason_;
  if (!valid_) return invalid_reason_;
  if (now < last_receive_) return "local monotonic clock moved backward";
  if (now - last_receive_ > timeout_) return "feedback receive timeout";
  if (now - last_progress_ > timeout_) return "source sequence/timestamp stopped advancing";
  return sequence_ || source_time_ ? "healthy" : "receive active; source sample age unverified";
}

std::unique_ptr<RobotBackend> make_backend(const Config &config) {
  validate_config(config);
  if (config.backend == "gdk") {
    throw std::runtime_error("GDK backend BLOCKED/UNIMPLEMENTED: verified GDK 2.6.3 SDK headers, libraries and adapter are unavailable; no mock fallback");
  }
  return std::make_unique<MockBackend>(config);
}

std::string state_name(MotionState state) {
  switch (state) {
    case MotionState::IDLE: return "IDLE";
    case MotionState::RUNNING: return "RUNNING";
    case MotionState::SUCCEEDED: return "SUCCEEDED";
    case MotionState::FAILED: return "FAILED";
  }
  return "FAILED";
}

Engine::Engine(Config config, std::unique_ptr<RobotBackend> backend)
    : config_(std::move(config)), backend_(std::move(backend)), freshness_(config_.feedback_timeout) {
  validate_config(config_);
  // Even an injected test backend cannot turn an unsupported gdk selection into mock success.
  if (config_.backend == "gdk") backend_ = make_backend(config_);
  if (!backend_) backend_ = make_backend(config_);
  std::random_device random;
  std::ostringstream id;
  id << std::hex << std::setfill('0');
  for (int i = 0; i < 4; ++i) id << std::setw(8) << random();
  process_id_ = id.str();
}

Engine::~Engine() {
  if (!stopped_ && backend_) {
    try { backend_->hold(last_tick_.value_or(0.0)); } catch (...) { /* Destructor cannot report a hardware stop. */ }
  }
}

void Engine::fail(const std::string &reason, double now) {
  fault_latched_ = true;
  backend_ok_ = false;
  backend_error_ = reason;
  status_.state = MotionState::FAILED;
  status_.reason = reason;
  stable_since_.reset();
  try {
    backend_->hold(now);
  } catch (const std::exception &error) {
    status_.reason += "; hold failed: " + std::string(error.what());
    backend_error_ = status_.reason;
  }
}

void Engine::tick(double now) {
  if (stopped_ || fault_latched_) return;
  if (!std::isfinite(now)) { fail("non-finite monotonic clock", last_tick_.value_or(0.0)); return; }
  if (last_tick_ && now < *last_tick_) { fail("monotonic clock moved backward", now); return; }
  if (last_tick_ && now - *last_tick_ > config_.watchdog_timeout) {
    fail("scheduler watchdog exceeded; historical commands were not replayed", now);
    return;
  }
  last_tick_ = now;
  bool new_observation = false;
  try {
    auto incoming = backend_->poll(now);
    if (incoming) {
      const auto error = validate_observation(*incoming);
      if (!error.empty()) { fail("invalid feedback: " + error, now); return; }
      if (incoming->names != mock_joint_names()) { fail("unexpected mock joint names or order", now); return; }
      if (incoming->sample_time > now || now - incoming->sample_time > config_.feedback_timeout) {
        fail("mock feedback sample time is future or stale", now); return;
      }
      if (std::any_of(incoming->positions.begin(), incoming->positions.end(), [this](double v) { return std::abs(v) > config_.position_limit; })) {
        fail("feedback exceeds synthetic position limit", now); return;
      }
      new_observation = freshness_.observe(incoming->sequence, incoming->sample_time, now);
      if (new_observation) observation_ = std::move(incoming);
      if (!freshness_.healthy(now)) { fail(freshness_.reason(now), now); return; }
    }
  } catch (const std::exception &error) {
    fail("backend failure: " + std::string(error.what()), now);
    return;
  }
  if (observation_ && !freshness_.healthy(now)) { fail(freshness_.reason(now), now); return; }
  if (status_.state != MotionState::RUNNING) return;
  if (!observation_) { fail("missing feedback during motion", now); return; }
  const double elapsed = now - started_;
  if (elapsed > config_.motion_timeout) { fail("motion timeout; completion not observed", now); return; }

  const double excursion = (observation_->positions[target_index_] - baseline_[target_index_]) *
                           (config_.displacement > 0.0 ? 1.0 : -1.0);
  if (new_observation && excursion >= std::abs(config_.displacement) * 0.8) observed_excursion_ = true;
  bool settled = new_observation && observed_excursion_ && elapsed >= config_.duration;
  for (std::size_t i = 0; i < baseline_.size(); ++i) {
    settled = settled && std::abs(observation_->positions[i] - baseline_[i]) <= config_.position_tolerance;
    if (!observation_->velocities.empty()) settled = settled && std::abs(observation_->velocities[i]) <= config_.velocity_tolerance;
  }
  if (new_observation) {
    if (!settled) stable_since_.reset();
    else if (!stable_since_) stable_since_ = now;
    else if (now - *stable_since_ >= config_.stable_duration) {
      status_.state = MotionState::SUCCEEDED;
      status_.reason = "observed outward excursion and stable return to baseline";
      // Keep the already-issued baseline command; success does not invent a final observation.
      return;
    }
  }
  const double half = config_.duration * 0.5;
  const double weight = elapsed <= half ? smoothstep(elapsed / half) : 1.0 - smoothstep((elapsed - half) / half);
  auto command = baseline_;
  command[target_index_] += config_.displacement * weight;
  try { backend_->command_positions(command, now); }
  catch (const std::exception &error) { fail("command failure: " + std::string(error.what()), now); }
}

RequestResult Engine::request(double now) {
  if (stopped_) return {false, {}, "node is stopping"};
  if (status_.state == MotionState::RUNNING) return {false, status_.run_id, "another motion is RUNNING; no queue"};
  if (!config_.enable_motion) return {false, {}, "enable_motion=false"};
  if (!healthy(now)) return {false, {}, health_reason(now)};
  const auto found = std::find(observation_->names.begin(), observation_->names.end(), config_.target_joint);
  if (found == observation_->names.end()) return {false, {}, "target joint missing from feedback"};
  target_index_ = static_cast<std::size_t>(found - observation_->names.begin());
  const double target = observation_->positions[target_index_] + config_.displacement;
  if (!std::isfinite(target) || std::abs(target) > config_.position_limit) return {false, {}, "requested target exceeds synthetic position limit"};
  baseline_ = observation_->positions;
  started_ = now;
  stable_since_.reset();
  observed_excursion_ = false;
  status_ = {MotionState::RUNNING, process_id_ + "-" + std::to_string(++request_count_), "request accepted; completion requires feedback"};
  return {true, status_.run_id, status_.reason};
}

bool Engine::healthy(double now) const {
  return !stopped_ && !fault_latched_ && backend_ok_ && observation_.has_value() && freshness_.healthy(now) &&
         last_tick_ && std::isfinite(now) && now >= *last_tick_ && now - *last_tick_ <= config_.watchdog_timeout;
}

std::string Engine::health_reason(double now) const {
  if (stopped_) return "stopped";
  if (fault_latched_ || !backend_ok_) return "fault latched; restart required: " + backend_error_;
  if (!freshness_.healthy(now)) return freshness_.reason(now);
  if (!last_tick_ || now < *last_tick_ || now - *last_tick_ > config_.watchdog_timeout) return "scheduler heartbeat is stale or invalid";
  return "healthy mock observation; local simulation sampling clock";
}

void Engine::shutdown(double now) {
  if (stopped_) return;
  if (status_.state == MotionState::RUNNING) fail("shutdown cancelled active motion; no return motion commanded", now);
  else {
    try { backend_->hold(now); }
    catch (const std::exception &error) { fail("shutdown hold failed: " + std::string(error.what()), now); }
  }
  stopped_ = true;
}

void Engine::set_fault(const std::string &fault) { backend_->set_fault(fault); }

}  // namespace agibot_g2_demo
