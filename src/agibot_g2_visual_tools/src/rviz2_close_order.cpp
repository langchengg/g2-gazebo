/*
 * Copyright (c) 2011, Willow Garage, Inc.
 * Copyright (c) 2017, Open Source Robotics Foundation, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of the Willow Garage, Inc. nor the names of its
 *       contributors may be used to endorse or promote products derived from
 *       this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <memory>
#include <string>
#include <vector>

#include <QEvent>
#include <QPointer>
#include <QApplication>  // NOLINT: cpplint is unable to handle the include order here

#include "rclcpp/rclcpp.hpp"
#include "rviz_common/logging.hpp"
#include "rviz_common/ros_integration/ros_client_abstraction.hpp"
#include "rviz_common/visualizer_app.hpp"
#include "rviz_common/visualization_frame.hpp"
#include "rviz_common/visualization_manager.hpp"

// Project adaptation of the official Humble entry point. The RViz application,
// ROS signal handling, configuration, rendering, displays and plugins remain upstream.
class CloseOrderedApplication : public QApplication
{
public:
  using QApplication::QApplication;

  void watch(rviz_common::VisualizationFrame * frame)
  {
    frame_ = frame;
    frame_->installEventFilter(this);
    connect(this, &QCoreApplication::aboutToQuit, this, [this]() {
      quitting_ = true;
      stopUpdates("aboutToQuit");
    });
  }

  bool notify(QObject * receiver, QEvent * event) override
  {
    const bool frame_close = receiver == frame_.data() && event->type() == QEvent::Close;
    const bool result = QApplication::notify(receiver, event);
    // Check only after closeEvent (and any nested save dialog) returns. A queued
    // callback could execute inside that dialog and restart rendering too early.
    if (frame_close && frame_ && !event->isAccepted() && !quitting_) {
      frame_->getManager()->startUpdate();
      RCLCPP_INFO(rclcpp::get_logger("rviz2"), "close-order: cancelled Close; updates resumed");
    }
    return result;
  }

protected:
  bool eventFilter(QObject * receiver, QEvent * event) override
  {
    if (receiver == frame_.data() && event->type() == QEvent::Close) {
      stopUpdates("before Close");
    }
    // Deliver the original event exactly once; preserve acceptance and cancellation.
    return QApplication::eventFilter(receiver, event);
  }

private:
  void stopUpdates(const char * reason)
  {
    if (frame_ && frame_->getManager()) {
      frame_->getManager()->stopUpdate();
      RCLCPP_INFO(rclcpp::get_logger("rviz2"), "close-order: updates stopped (%s)", reason);
    }
  }
  QPointer<rviz_common::VisualizationFrame> frame_;
  bool quitting_ = false;
};

int main(int argc, char ** argv)
{
  // remove ROS arguments before passing to QApplication
  std::vector<std::string> non_ros_args = rclcpp::remove_ros_arguments(argc, argv);
  std::vector<char *> non_ros_args_c_strings;
  for (auto & arg : non_ros_args) {
    non_ros_args_c_strings.push_back(&arg.front());
  }
  int non_ros_argc = static_cast<int>(non_ros_args_c_strings.size());

  CloseOrderedApplication qapp(non_ros_argc, non_ros_args_c_strings.data());

  // TODO(wjwwood): use node's logger here in stead
  auto logger = rclcpp::get_logger("rviz2");
  // install logging handlers to route logging through ROS's logging system
  rviz_common::set_logging_handlers(
    [logger](const std::string & msg, const std::string &, size_t) {
      RCLCPP_DEBUG(logger, "%s", msg.c_str());
    },
    [logger](const std::string & msg, const std::string &, size_t) {
      RCLCPP_INFO(logger, "%s", msg.c_str());
    },
    [logger](const std::string & msg, const std::string &, size_t) {
      RCLCPP_WARN(logger, "%s", msg.c_str());
    },
    [logger](const std::string & msg, const std::string &, size_t) {
      RCLCPP_ERROR(logger, "%s", msg.c_str());
    }
  );

  rviz_common::VisualizerApp vapp(
    std::make_unique<rviz_common::ros_integration::RosClientAbstraction>());
  vapp.setApp(&qapp);
  if (vapp.init(argc, argv)) {
    rviz_common::VisualizationFrame * frame = nullptr;
    for (QWidget * widget : QApplication::topLevelWidgets()) {
      if (auto * candidate = qobject_cast<rviz_common::VisualizationFrame *>(widget)) {
        if (frame) {
          RCLCPP_ERROR(logger, "close-order: multiple VisualizationFrames; refusing ambiguity");
          return 2;
        }
        frame = candidate;
      }
    }
    if (!frame || !frame->getManager()) {
      RCLCPP_ERROR(logger, "close-order: no initialized VisualizationFrame found");
      return 2;
    }
    qapp.watch(frame);
    RCLCPP_INFO(logger, "close-order: initialized official VisualizationFrame hook");
    return qapp.exec();
  } else {
    return 1;
  }
}
