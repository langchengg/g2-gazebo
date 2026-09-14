#include "agibot_g2_demo/core.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace demo = agibot_g2_demo;
namespace {

demo::Config enabled() {
  demo::Config result;
  result.enable_motion = true;
  return result;
}

demo::Observation valid_observation() {
  return {demo::mock_joint_names(), std::vector<double>(6, 0.1), {}, {}, 1, 0.0};
}

// An independently controlled input fixture, not a fabricated vendor SDK.
class InputBackend final : public demo::RobotBackend {
 public:
  demo::Observation next = valid_observation();
  int polls{0};
  int commands{0};
  int holds{0};
  bool command_error{false};
  bool hold_error{false};
  std::vector<double> last_command;
  std::optional<demo::Observation> poll(double now) override {
    ++polls;
    next.sample_time = now;
    next.sequence = static_cast<std::uint64_t>(polls);
    return next;
  }
  void command_positions(const std::vector<double> &positions, double) override {
    ++commands;
    if (command_error) throw std::runtime_error("test command rejected");
    last_command = positions;
  }
  void hold(double) override {
    ++holds;
    if (hold_error) throw std::runtime_error("test hold rejected");
  }
  void set_fault(const std::string &) override {}
};

TEST(Configuration, SafeDefaultsAndUnknownBackend) {
  demo::Config c;
  EXPECT_FALSE(c.enable_motion);
  EXPECT_EQ(c.backend, "mock");
  EXPECT_NO_THROW(demo::validate_config(c));
  c.backend = "mystery";
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
}

TEST(Configuration, RejectsEveryNonFiniteAndNonPositiveBound) {
  const std::vector<double demo::Config::*> fields = {
      &demo::Config::duration, &demo::Config::publish_hz, &demo::Config::max_displacement,
      &demo::Config::max_velocity, &demo::Config::max_acceleration, &demo::Config::position_limit,
      &demo::Config::feedback_timeout, &demo::Config::watchdog_timeout, &demo::Config::motion_timeout,
      &demo::Config::position_tolerance, &demo::Config::velocity_tolerance,
      &demo::Config::stable_duration, &demo::Config::tracking_time_constant};
  for (auto field : fields) {
    for (double bad : {0.0, -1.0, std::numeric_limits<double>::infinity(),
                       std::numeric_limits<double>::quiet_NaN()}) {
      auto c = enabled();
      c.*field = bad;
      EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
    }
  }
}

TEST(Configuration, RejectsInvalidMotionAndProfileLimits) {
  for (double bad : {0.0, 0.11, -0.11, std::numeric_limits<double>::infinity(),
                     std::numeric_limits<double>::quiet_NaN()}) {
    auto c = enabled();
    c.displacement = bad;
    EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  }
  auto c = enabled();
  c.target_joint = "g2_joint_unverified";
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  c = enabled(); c.duration = 0.1;
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  c = enabled(); c.max_velocity = 0.001;
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  c = enabled(); c.max_acceleration = 0.001;
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  c = enabled(); c.motion_timeout = c.duration;
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  c = enabled(); c.position_tolerance = c.displacement;
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  c = enabled(); c.fault = "unknown";
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
  c = enabled(); c.publish_hz = 51.0;
  EXPECT_THROW(demo::Engine{c}, std::invalid_argument);
}

TEST(Configuration, GdkSelectionFailsWithoutAnyFallback) {
  auto c = enabled(); c.backend = "gdk";
  EXPECT_THROW(demo::Engine{c}, std::runtime_error);
  EXPECT_THROW(demo::make_backend(c), std::runtime_error);
  EXPECT_THROW((demo::Engine{c, std::make_unique<InputBackend>()}), std::runtime_error);
}

TEST(Observations, DimensionsNamesFiniteValuesAndUnknownFields) {
  auto o = valid_observation();
  EXPECT_TRUE(demo::validate_observation(o).empty());
  EXPECT_TRUE(o.velocities.empty());
  EXPECT_TRUE(o.efforts.empty());
  o.positions.pop_back(); EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.names[0].clear(); EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.names[1] = o.names[0]; EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.velocities = {0.0}; EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.efforts = {0.0}; EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.positions[0] = std::numeric_limits<double>::quiet_NaN();
  EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.velocities.assign(6, std::numeric_limits<double>::infinity());
  EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.efforts.assign(6, std::numeric_limits<double>::infinity());
  EXPECT_FALSE(demo::validate_observation(o).empty());
  o = valid_observation(); o.sample_time = std::numeric_limits<double>::quiet_NaN();
  EXPECT_FALSE(demo::validate_observation(o).empty());
  EXPECT_FALSE(demo::validate_observation({}).empty());
}

TEST(Freshness, SeparatesSourceClockFromMonotonicReceiveClock) {
  demo::SourceFreshness guard(0.5);
  EXPECT_FALSE(guard.healthy(0.0));
  EXPECT_TRUE(guard.observe(1, 1900000000.0, 1.0));
  EXPECT_TRUE(guard.healthy(1.1));
  EXPECT_TRUE(guard.observe(2, 1900000000.1, 1.2));
  EXPECT_TRUE(guard.healthy(1.6));
  EXPECT_FALSE(guard.healthy(1.8));
  EXPECT_NE(guard.reason(1.8).find("receive timeout"), std::string::npos);
}

TEST(Freshness, RepeatedOldSamplesDoNotRenewSourceFreshness) {
  demo::SourceFreshness guard(0.5);
  ASSERT_TRUE(guard.observe(1, 1234.0, 0.0));
  double receive_time = 0.0;
  for (int i = 1; i <= 6; ++i) {
    receive_time = i * 0.1;
    EXPECT_FALSE(guard.observe(1, 1234.0, receive_time));
  }
  // Inspect at the exact injected receive instant: 6 * 0.1 and literal 0.6
  // need not be the same double, which would accidentally test clock reversal.
  EXPECT_FALSE(guard.healthy(receive_time));
  EXPECT_NE(guard.reason(receive_time).find("stopped advancing"), std::string::npos);
}

TEST(Freshness, BothAvailableMarkersMustAdvance) {
  demo::SourceFreshness guard(0.5);
  ASSERT_TRUE(guard.observe(1, 10.0, 0.0));
  EXPECT_FALSE(guard.observe(2, 10.0, 0.1));
  EXPECT_FALSE(guard.observe(1, 11.0, 0.2));
  EXPECT_TRUE(guard.observe(2, 11.0, 0.3));
  EXPECT_FALSE(guard.observe(1, 12.0, 0.4));
  EXPECT_FALSE(guard.healthy(0.4));
}

TEST(Freshness, RejectsClockAndMarkerFailures) {
  demo::SourceFreshness guard(0.5);
  ASSERT_TRUE(guard.observe(1, 10.0, 1.0));
  EXPECT_FALSE(guard.observe(2, 11.0, 0.9));
  EXPECT_FALSE(guard.healthy(1.0));
  EXPECT_FALSE(guard.observe(2, std::numeric_limits<double>::quiet_NaN(), 1.1));
  EXPECT_FALSE(guard.observe(std::nullopt, 11.0, 1.2));
  demo::SourceFreshness unclocked(0.5);
  EXPECT_TRUE(unclocked.observe(std::nullopt, std::nullopt, 0.0));
  EXPECT_NE(unclocked.reason(0.1).find("unverified"), std::string::npos);
  EXPECT_FALSE(unclocked.healthy(std::numeric_limits<double>::infinity()));
}

TEST(MockBackend, CommandAndObservedStateAreSeparateAndEffortIsUnknown) {
  auto backend = demo::make_backend(enabled());
  const auto first = backend->poll(0.0).value();
  auto command = first.positions;
  command[0] += 0.05;
  backend->command_positions(command, 0.0);
  const auto second = backend->poll(0.02).value();
  EXPECT_GT(second.positions[0], first.positions[0]);
  EXPECT_LT(second.positions[0], command[0]);
  EXPECT_TRUE(second.efforts.empty());
  EXPECT_GT(second.sequence, first.sequence);
  EXPECT_EQ(second.sample_time, 0.02);
  for (std::size_t i = 1; i < command.size(); ++i) EXPECT_DOUBLE_EQ(second.positions[i], first.positions[i]);
  backend->hold(0.02);
  const auto held = backend->poll(0.04).value();
  EXPECT_EQ(held.positions, second.positions);
  EXPECT_THROW(backend->command_positions({}, 0.04), std::invalid_argument);
  command[0] = std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(backend->command_positions(command, 0.04), std::invalid_argument);
  command[0] = 2.0;
  EXPECT_THROW(backend->command_positions(command, 0.04), std::invalid_argument);
}

TEST(Engine, StartupNeverMovesAndDisabledRequestIsRejected) {
  demo::Engine engine{demo::Config{}};
  engine.tick(0.0);
  const auto initial = engine.observation()->positions;
  for (int i = 1; i <= 250; ++i) engine.tick(i * 0.02);
  EXPECT_EQ(engine.observation()->positions, initial);
  EXPECT_EQ(engine.status().state, demo::MotionState::IDLE);
  const auto result = engine.request(5.0);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("enable_motion=false"), std::string::npos);
}

TEST(Engine, RequiresFreshFeedbackBeforeAcceptingAnyRequest) {
  demo::Engine engine{enabled()};
  EXPECT_FALSE(engine.request(0.0).accepted);
  engine.tick(0.0);
  EXPECT_FALSE(engine.request(1.0).accepted);
  EXPECT_FALSE(engine.request(std::numeric_limits<double>::quiet_NaN()).accepted);
  EXPECT_FALSE(engine.request(-1.0).accepted);
}

TEST(Engine, RoundTripUsesObservedExcursionAndStableReturnWithNewRunIds) {
  auto c = enabled();
  demo::Engine engine{c};
  engine.tick(0.0);
  const auto initial = engine.observation()->positions;
  const auto first = engine.request(0.0);
  ASSERT_TRUE(first.accepted);
  ASSERT_FALSE(first.run_id.empty());
  EXPECT_EQ(engine.status().state, demo::MotionState::RUNNING);
  EXPECT_FALSE(engine.request(0.0).accepted);  // serialized simultaneous requests
  double peak = 0.0;
  double last_velocity = 0.0;
  double completed_at = -1.0;
  for (int i = 1; i <= 350; ++i) {
    const double now = i * 0.02;
    engine.tick(now);
    const auto &sample = engine.observation().value();
    peak = std::max(peak, sample.positions[0] - initial[0]);
    EXPECT_LE(std::abs(sample.velocities[0]), c.max_velocity);
    EXPECT_LE(std::abs((sample.velocities[0] - last_velocity) / 0.02), c.max_acceleration);
    last_velocity = sample.velocities[0];
    for (std::size_t j = 1; j < initial.size(); ++j) EXPECT_DOUBLE_EQ(sample.positions[j], initial[j]);
    ASSERT_NE(engine.status().state, demo::MotionState::FAILED) << engine.status().reason;
    if (engine.status().state == demo::MotionState::SUCCEEDED) { completed_at = now; break; }
  }
  EXPECT_GT(peak, c.displacement * 0.9);
  EXPECT_LE(peak, c.displacement);
  ASSERT_GE(completed_at, c.duration + c.stable_duration);
  EXPECT_NEAR(engine.observation()->positions[0], initial[0], c.position_tolerance);
  EXPECT_EQ(engine.status().run_id, first.run_id);
  const auto second = engine.request(completed_at);
  EXPECT_TRUE(second.accepted);
  EXPECT_NE(second.run_id, first.run_id);
}

TEST(Engine, DifferentEnginesDoNotReuseCachedRunIds) {
  demo::Engine a{enabled()}, b{enabled()};
  a.tick(0.0); b.tick(0.0);
  EXPECT_NE(a.request(0.0).run_id, b.request(0.0).run_id);
}

TEST(Engine, NegativeDisplacementAndAlternateJointAreSupported) {
  auto c = enabled(); c.displacement = -0.05; c.target_joint = "mock_right_arm_joint2";
  demo::Engine engine{c}; engine.tick(0.0);
  const auto baseline = engine.observation()->positions;
  ASSERT_TRUE(engine.request(0.0).accepted);
  double minimum = baseline[4];
  for (int i = 1; i <= 350; ++i) {
    engine.tick(i * 0.02);
    minimum = std::min(minimum, engine.observation()->positions[4]);
    if (engine.status().state != demo::MotionState::RUNNING) break;
  }
  EXPECT_LT(minimum, baseline[4] - 0.045);
  EXPECT_EQ(engine.status().state, demo::MotionState::SUCCEEDED) << engine.status().reason;
  EXPECT_NEAR(engine.observation()->positions[4], baseline[4], c.position_tolerance);
  EXPECT_DOUBLE_EQ(engine.observation()->positions[0], baseline[0]);
}

TEST(Engine, RejectsTargetOutsideSyntheticLimits) {
  auto c = enabled(); c.displacement = 0.1; c.position_limit = 0.11;
  demo::Engine engine{c}; engine.tick(0.0);
  EXPECT_FALSE(engine.request(0.0).accepted);
  EXPECT_EQ(engine.status().state, demo::MotionState::IDLE);
}

class FeedbackFault : public testing::TestWithParam<const char *> {};
TEST_P(FeedbackFault, NeverReportsSuccessAndDoesNotResumeAfterRecovery) {
  demo::Engine engine{enabled()}; engine.tick(0.0);
  const auto request = engine.request(0.0);
  ASSERT_TRUE(request.accepted);
  for (int i = 1; i <= 20; ++i) engine.tick(i * 0.02);
  engine.set_fault(GetParam());
  for (int i = 21; i <= 400; ++i) {
    engine.tick(i * 0.02);
    ASSERT_NE(engine.status().state, demo::MotionState::SUCCEEDED);
    if (engine.status().state == demo::MotionState::FAILED) break;
  }
  EXPECT_EQ(engine.status().state, demo::MotionState::FAILED) << GetParam();
  EXPECT_EQ(engine.status().run_id, request.run_id);
  engine.set_fault("none");
  engine.tick(9.0);
  EXPECT_FALSE(engine.request(9.0).accepted);
  EXPECT_EQ(engine.status().state, demo::MotionState::FAILED);
}
INSTANTIATE_TEST_SUITE_P(Mock, FeedbackFault,
                        testing::Values("freeze", "repeat", "error", "nan", "inf", "invalid", "timeout", "watchdog"));

TEST(Engine, WatchdogStopsWithoutReplayingCommandsOrReturningToBaseline) {
  auto input = std::make_unique<InputBackend>();
  auto *raw = input.get();
  demo::Engine engine{enabled(), std::move(input)}; engine.tick(0.0);
  ASSERT_TRUE(engine.request(0.0).accepted);
  engine.tick(0.02);
  const int before = raw->commands;
  engine.tick(1.0);
  EXPECT_EQ(engine.status().state, demo::MotionState::FAILED);
  EXPECT_EQ(raw->commands, before);
  EXPECT_EQ(raw->polls, 2);
  EXPECT_EQ(raw->holds, 1);
}

TEST(Engine, MonotonicClockFailuresAreTerminal) {
  for (double bad : {-0.1, std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity()}) {
    demo::Engine engine{enabled()}; engine.tick(0.0);
    ASSERT_TRUE(engine.request(0.0).accepted);
    engine.tick(bad);
    EXPECT_EQ(engine.status().state, demo::MotionState::FAILED);
  }
}

TEST(Engine, RejectsChangedJointNamesAndOutOfBoundsFeedback) {
  for (int fault = 0; fault < 3; ++fault) {
    auto input = std::make_unique<InputBackend>(); auto *raw = input.get();
    demo::Engine engine{enabled(), std::move(input)}; engine.tick(0.0);
    ASSERT_TRUE(engine.request(0.0).accepted);
    if (fault == 0) raw->next.names[0] = "unknown_joint";
    if (fault == 1) std::swap(raw->next.names[0], raw->next.names[1]);
    if (fault == 2) raw->next.positions[0] = 1.1;
    engine.tick(0.02);
    EXPECT_EQ(engine.status().state, demo::MotionState::FAILED);
    EXPECT_EQ(raw->commands, 0);
  }
}

TEST(Engine, BackendCommandAndHoldFailuresAreReported) {
  auto input = std::make_unique<InputBackend>(); auto *raw = input.get();
  demo::Engine engine{enabled(), std::move(input)}; engine.tick(0.0);
  ASSERT_TRUE(engine.request(0.0).accepted);
  raw->command_error = true; raw->hold_error = true;
  EXPECT_NO_THROW(engine.tick(0.02));
  EXPECT_EQ(engine.status().state, demo::MotionState::FAILED);
  EXPECT_NE(engine.status().reason.find("command failure"), std::string::npos);
  EXPECT_NE(engine.status().reason.find("hold failed"), std::string::npos);
}

TEST(Engine, ShutdownIsBoundedIdempotentAndDoesNotCommandReturn) {
  auto input = std::make_unique<InputBackend>(); auto *raw = input.get();
  demo::Engine engine{enabled(), std::move(input)}; engine.tick(0.0);
  ASSERT_TRUE(engine.request(0.0).accepted);
  engine.tick(0.02);
  const int before = raw->commands;
  engine.shutdown(0.02);
  engine.shutdown(0.03);
  engine.tick(0.04);
  EXPECT_EQ(engine.status().state, demo::MotionState::FAILED);
  EXPECT_EQ(raw->commands, before);
  EXPECT_EQ(raw->holds, 1);
  EXPECT_FALSE(engine.request(0.04).accepted);
}

}  // namespace
