#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <geometry_msgs/msg/pose.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit/planning_scene/planning_scene.h>
#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <moveit/task_constructor/task.h>
#include <moveit/task_constructor/solvers.h>
#include <moveit/task_constructor/stages.h>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <thread>
#include <chrono>
#include <sstream>
#include <iomanip>

static const rclcpp::Logger LOGGER = rclcpp::get_logger("brain_arm_node");
namespace mtc = moveit::task_constructor;

// Simple JSON helpers for fixed command formats from task002.md
class JsonHelper
{
public:
  static std::string extractString(const std::string& json, const std::string& key)
  {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos)
      return "";
    pos = json.find(":", pos + search.length());
    if (pos == std::string::npos)
      return "";
    pos = json.find_first_of("\"[", pos + 1);
    if (pos == std::string::npos)
      return "";
    if (json[pos] == '[')
      return "";
    size_t end = json.find("\"", pos + 1);
    if (end == std::string::npos)
      return "";
    return json.substr(pos + 1, end - pos - 1);
  }

  static double extractDouble(const std::string& json, const std::string& key)
  {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos)
      return 0.0;
    pos = json.find(":", pos + search.length());
    if (pos == std::string::npos)
      return 0.0;
    ++pos;
    // skip whitespace
    while (pos < json.length() && std::isspace(json[pos]))
      ++pos;
    size_t end = pos;
    while (end < json.length() && (std::isdigit(json[end]) || json[end] == '.' || json[end] == '-' || json[end] == 'e' || json[end] == 'E' || json[end] == '+'))
      ++end;
    try
    {
      return std::stod(json.substr(pos, end - pos));
    }
    catch (...)
    {
      return 0.0;
    }
  }

  static std::vector<double> extractDoubleArray(const std::string& json, const std::string& key)
  {
    std::vector<double> result;
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos)
      return result;
    pos = json.find(":", pos + search.length());
    if (pos == std::string::npos)
      return result;
    pos = json.find("[", pos + 1);
    if (pos == std::string::npos)
      return result;
    size_t end = json.find("]", pos + 1);
    if (end == std::string::npos)
      return result;
    std::string inner = json.substr(pos + 1, end - pos - 1);
    std::stringstream ss(inner);
    std::string token;
    while (std::getline(ss, token, ','))
    {
      try
      {
        result.push_back(std::stod(token));
      }
      catch (...)
      {
      }
    }
    return result;
  }
};

class BrainArmNode
{
public:
  BrainArmNode(const rclcpp::NodeOptions& options);

  rclcpp::node_interfaces::NodeBaseInterface::SharedPtr getNodeBaseInterface();

  void setupPlanningScene();

private:
  void commandCallback(const std_msgs::msg::String::SharedPtr msg);
  void publishFeedback(const std::string& status, const std::string& action_id, const std::string& message);

  void handleMoveTo(const std::string& json, const std::string& action_id);
  void handleMoveJoints(const std::string& json, const std::string& action_id);
  void handleGripper(const std::string& json, const std::string& action_id);
  void handleHome(const std::string& action_id);
  void handleStop(const std::string& action_id);
  void handlePickPlace(const std::string& action_id);

  void stopArmService(const std::shared_ptr<std_srvs::srv::Trigger::Request> request,
                      std::shared_ptr<std_srvs::srv::Trigger::Response> response);
  void goHomeService(const std::shared_ptr<std_srvs::srv::Trigger::Request> request,
                     std::shared_ptr<std_srvs::srv::Trigger::Response> response);

  mtc::Task createPickPlaceTask();

  rclcpp::Node::SharedPtr node_;
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr command_sub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr feedback_pub_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr stop_service_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr home_service_;

  std::shared_ptr<moveit::planning_interface::MoveGroupInterface> arm_group_;
  std::shared_ptr<moveit::planning_interface::MoveGroupInterface> hand_group_;

  // MTC task and introspection need to persist
  std::shared_ptr<mtc::Task> pick_place_task_;

  std::atomic<bool> stop_requested_{ false };
  int action_counter_ = 0;
};

rclcpp::node_interfaces::NodeBaseInterface::SharedPtr BrainArmNode::getNodeBaseInterface()
{
  return node_->get_node_base_interface();
}

BrainArmNode::BrainArmNode(const rclcpp::NodeOptions& options)
  : node_{ std::make_shared<rclcpp::Node>("brain_arm_node", options) }
{
  // Wait a moment for robot_description to be available
  rclcpp::sleep_for(std::chrono::seconds(2));

  // Initialize MoveGroup interfaces
  arm_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(node_, "panda_arm");
  hand_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(node_, "hand");

  arm_group_->setPlanningTime(5.0);
  arm_group_->setMaxVelocityScalingFactor(0.3);
  arm_group_->setMaxAccelerationScalingFactor(0.3);

  hand_group_->setPlanningTime(2.0);
  hand_group_->setMaxVelocityScalingFactor(0.5);
  hand_group_->setMaxAccelerationScalingFactor(0.5);

  // Subscribers and publishers
  command_sub_ = node_->create_subscription<std_msgs::msg::String>(
      "/brain/action_command", 10,
      std::bind(&BrainArmNode::commandCallback, this, std::placeholders::_1));

  feedback_pub_ = node_->create_publisher<std_msgs::msg::String>("/brain/action_feedback", 10);

  // Services
  stop_service_ = node_->create_service<std_srvs::srv::Trigger>(
      "/brain/stop_arm",
      std::bind(&BrainArmNode::stopArmService, this, std::placeholders::_1, std::placeholders::_2));

  home_service_ = node_->create_service<std_srvs::srv::Trigger>(
      "/brain/go_home",
      std::bind(&BrainArmNode::goHomeService, this, std::placeholders::_1, std::placeholders::_2));

  RCLCPP_INFO(LOGGER, "Brain-Arm node initialized. Waiting for commands on /brain/action_command");
}

void BrainArmNode::publishFeedback(const std::string& status, const std::string& action_id,
                                   const std::string& message)
{
  std_msgs::msg::String feedback;
  std::stringstream ss;
  ss << "{\"status\":\"" << status << "\","
     << "\"action_id\":\"" << action_id << "\","
     << "\"message\":\"" << message << "\"}";
  feedback.data = ss.str();
  feedback_pub_->publish(feedback);
  RCLCPP_INFO(LOGGER, "Feedback: %s", feedback.data.c_str());
}

void BrainArmNode::commandCallback(const std_msgs::msg::String::SharedPtr msg)
{
  std::string json = msg->data;
  RCLCPP_INFO(LOGGER, "Received command: %s", json.c_str());

  std::string action_type = JsonHelper::extractString(json, "action_type");
  if (action_type.empty())
  {
    publishFeedback("failed", "unknown", "Missing action_type field");
    return;
  }

  ++action_counter_;
  std::string action_id = action_type + "_" + std::to_string(action_counter_);

  stop_requested_ = false;
  publishFeedback("running", action_id, "Received " + action_type + " command");

  if (action_type == "move_to")
    handleMoveTo(json, action_id);
  else if (action_type == "move_joints")
    handleMoveJoints(json, action_id);
  else if (action_type == "home")
    handleHome(action_id);
  else if (action_type == "stop")
    handleStop(action_id);
  else if (action_type == "pick_place")
    handlePickPlace(action_id);
  else
    publishFeedback("failed", action_id, "Unknown action_type: " + action_type);
}

void BrainArmNode::handleMoveTo(const std::string& json, const std::string& action_id)
{
  double x = JsonHelper::extractDouble(json, "x");
  double y = JsonHelper::extractDouble(json, "y");
  double z = JsonHelper::extractDouble(json, "z");
  double roll = JsonHelper::extractDouble(json, "roll");
  double pitch = JsonHelper::extractDouble(json, "pitch");
  double yaw = JsonHelper::extractDouble(json, "yaw");
  double speed = JsonHelper::extractDouble(json, "speed");
  if (speed <= 0.0)
    speed = 0.3;

  RCLCPP_INFO(LOGGER, "move_to target: x=%.3f y=%.3f z=%.3f r=%.3f p=%.3f y=%.3f speed=%.2f", x, y, z, roll, pitch,
              yaw, speed);

  geometry_msgs::msg::Pose target_pose;
  target_pose.position.x = x;
  target_pose.position.y = y;
  target_pose.position.z = z;

  tf2::Quaternion q;
  q.setRPY(roll, pitch, yaw);
  target_pose.orientation = tf2::toMsg(q);

  arm_group_->setPoseTarget(target_pose);
  arm_group_->setMaxVelocityScalingFactor(speed);
  arm_group_->setMaxAccelerationScalingFactor(speed);

  moveit::planning_interface::MoveGroupInterface::Plan plan;
  bool success = (arm_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS);

  if (!success)
  {
    publishFeedback("failed", action_id, "Failed to plan move_to trajectory");
    return;
  }

  if (stop_requested_)
  {
    publishFeedback("failed", action_id, "Command stopped before execution");
    return;
  }

  auto exec_result = arm_group_->execute(plan);
  if (exec_result == moveit::core::MoveItErrorCode::SUCCESS)
    publishFeedback("success", action_id, "Reached target pose");
  else
    publishFeedback("failed", action_id, "Failed to execute move_to trajectory");
}

void BrainArmNode::handleMoveJoints(const std::string& json, const std::string& action_id)
{
  std::vector<double> joint_angles = JsonHelper::extractDoubleArray(json, "joint_angles");
  double speed = JsonHelper::extractDouble(json, "speed");
  if (speed <= 0.0)
    speed = 0.2;

  if (joint_angles.size() < 6)
  {
    publishFeedback("failed", action_id, "joint_angles must have at least 6 values for soarm101_arm");
    return;
  }

  RCLCPP_INFO(LOGGER, "move_joints to %zu angles with speed %.2f", joint_angles.size(), speed);

  arm_group_->setJointValueTarget(joint_angles);
  arm_group_->setMaxVelocityScalingFactor(speed);
  arm_group_->setMaxAccelerationScalingFactor(speed);

  moveit::planning_interface::MoveGroupInterface::Plan plan;
  bool success = (arm_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS);

  if (!success)
  {
    publishFeedback("failed", action_id, "Failed to plan move_joints trajectory");
    return;
  }

  if (stop_requested_)
  {
    publishFeedback("failed", action_id, "Command stopped before execution");
    return;
  }

  auto exec_result = arm_group_->execute(plan);
  if (exec_result == moveit::core::MoveItErrorCode::SUCCESS)
    publishFeedback("success", action_id, "Reached target joint configuration");
  else
    publishFeedback("failed", action_id, "Failed to execute move_joints trajectory");
}

void BrainArmNode::handleGripper(const std::string& json, const std::string& action_id)
{
  // SOARM101 has no gripper - this function is kept for compatibility but does nothing
  publishFeedback("failed", action_id, "SOARM101 has no gripper");
}

void BrainArmNode::handleHome(const std::string& action_id)
{
  RCLCPP_INFO(LOGGER, "Moving to home (ready) position");

  arm_group_->setNamedTarget("ready");
  moveit::planning_interface::MoveGroupInterface::Plan plan;
  bool success = (arm_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS);

  if (!success)
  {
    publishFeedback("failed", action_id, "Failed to plan home trajectory");
    return;
  }

  auto exec_result = arm_group_->execute(plan);
  if (exec_result == moveit::core::MoveItErrorCode::SUCCESS)
    publishFeedback("success", action_id, "Reached home position");
  else
    publishFeedback("failed", action_id, "Failed to execute home trajectory");
}

void BrainArmNode::handleStop(const std::string& action_id)
{
  stop_requested_ = true;
  arm_group_->stop();
  hand_group_->stop();
  publishFeedback("success", action_id, "Stop command received, motion halted");
}

void BrainArmNode::handlePickPlace(const std::string& action_id)
{
  RCLCPP_INFO(LOGGER, "Starting MTC pick and place task");

  try {
    // Create the pick and place task
    pick_place_task_ = std::make_shared<mtc::Task>(createPickPlaceTask());

    // Enable introspection so the task shows up in RViz Task Monitor panel
    pick_place_task_->enableIntrospection(true);

    // Plan the task
    RCLCPP_INFO(LOGGER, "Planning MTC task...");
    if (!pick_place_task_->plan(5)) {
      RCLCPP_ERROR(LOGGER, "MTC task planning failed");
      publishFeedback("failed", action_id, "MTC task planning failed");
      return;
    }

    RCLCPP_INFO(LOGGER, "MTC task planning succeeded with %zu solutions",
                pick_place_task_->numSolutions());

    // Execute the first solution
    if (pick_place_task_->numSolutions() == 0) {
      RCLCPP_ERROR(LOGGER, "No solutions found");
      publishFeedback("failed", action_id, "No solutions found");
      return;
    }

    RCLCPP_INFO(LOGGER, "Executing MTC task solution...");

    // Execute via move_group's ExecuteTaskSolution capability
    const auto& solution = *pick_place_task_->solutions().begin();
    if (!pick_place_task_->execute(*solution)) {
      RCLCPP_ERROR(LOGGER, "MTC task execution failed");
      publishFeedback("failed", action_id, "MTC task execution failed");
      return;
    }

    RCLCPP_INFO(LOGGER, "MTC pick and place completed successfully");
    publishFeedback("success", action_id, "Pick and place completed");

  } catch (const std::exception& e) {
    RCLCPP_ERROR(LOGGER, "MTC task exception: %s", e.what());
    publishFeedback("failed", action_id, std::string("Exception: ") + e.what());
  }
}

mtc::Task BrainArmNode::createPickPlaceTask()
{
  mtc::Task task;
  task.stages()->setName("demo task");
  task.loadRobotModel(node_);

  const auto& arm_group_name = "panda_arm";
  const auto& hand_group_name = "hand";
  const auto& hand_frame = "panda_link8";

  task.setProperty("group", arm_group_name);
  task.setProperty("eef", hand_group_name);
  task.setProperty("ik_frame", hand_frame);

  mtc::Stage* current_state_ptr = nullptr;
  auto stage_state_current = std::make_unique<mtc::stages::CurrentState>("current");
  current_state_ptr = stage_state_current.get();
  task.add(std::move(stage_state_current));

  auto sampling_planner = std::make_shared<mtc::solvers::PipelinePlanner>(node_);
  auto interpolation_planner = std::make_shared<mtc::solvers::JointInterpolationPlanner>();
  auto cartesian_planner = std::make_shared<mtc::solvers::CartesianPath>();
  cartesian_planner->setMaxVelocityScalingFactor(1.0);
  cartesian_planner->setMaxAccelerationScalingFactor(1.0);
  cartesian_planner->setStepSize(.01);

  // Stage: open hand
  auto stage_open_hand = std::make_unique<mtc::stages::MoveTo>("open hand", interpolation_planner);
  stage_open_hand->setGroup(hand_group_name);
  stage_open_hand->setGoal("open");
  task.add(std::move(stage_open_hand));

  // Stage: move to pick
  auto stage_move_to_pick = std::make_unique<mtc::stages::Connect>(
      "move to pick",
      mtc::stages::Connect::GroupPlannerVector{ { arm_group_name, sampling_planner } });
  stage_move_to_pick->setTimeout(5.0);
  stage_move_to_pick->properties().configureInitFrom(mtc::Stage::PARENT);
  task.add(std::move(stage_move_to_pick));

  mtc::Stage* attach_object_stage = nullptr;

  // Pick Object
  {
    auto grasp = std::make_unique<mtc::SerialContainer>("pick object");
    task.properties().exposeTo(grasp->properties(), { "eef", "group", "ik_frame" });
    grasp->properties().configureInitFrom(mtc::Stage::PARENT, { "eef", "group", "ik_frame" });

    // approach object
    {
      auto stage = std::make_unique<mtc::stages::MoveRelative>("approach object", cartesian_planner);
      stage->properties().set("marker_ns", "approach_object");
      stage->properties().set("link", hand_frame);
      stage->properties().configureInitFrom(mtc::Stage::PARENT, { "group" });
      stage->setMinMaxDistance(0.1, 0.15);
      geometry_msgs::msg::Vector3Stamped vec;
      vec.header.frame_id = hand_frame;
      vec.vector.z = 1.0;
      stage->setDirection(vec);
      grasp->insert(std::move(stage));
    }

    // generate grasp pose + Compute IK
    {
      auto stage = std::make_unique<mtc::stages::GenerateGraspPose>("generate grasp pose");
      stage->properties().configureInitFrom(mtc::Stage::PARENT);
      stage->properties().set("marker_ns", "grasp_pose");
      stage->setPreGraspPose("open");
      stage->setObject("object");
      stage->setAngleDelta(M_PI / 12);
      stage->setMonitoredStage(current_state_ptr);

      Eigen::Isometry3d grasp_frame_transform;
      Eigen::Quaterniond q = Eigen::AngleAxisd(M_PI / 2, Eigen::Vector3d::UnitX()) *
                             Eigen::AngleAxisd(M_PI / 2, Eigen::Vector3d::UnitY()) *
                             Eigen::AngleAxisd(M_PI / 2, Eigen::Vector3d::UnitZ());
      grasp_frame_transform.linear() = q.matrix();
      grasp_frame_transform.translation().z() = 0.1;

      auto wrapper = std::make_unique<mtc::stages::ComputeIK>("grasp pose IK", std::move(stage));
      wrapper->setMaxIKSolutions(8);
      wrapper->setMinSolutionDistance(1.0);
      wrapper->setIKFrame(grasp_frame_transform, hand_frame);
      wrapper->properties().configureInitFrom(mtc::Stage::PARENT, { "eef", "group" });
      wrapper->properties().configureInitFrom(mtc::Stage::INTERFACE, { "target_pose" });
      grasp->insert(std::move(wrapper));
    }

    // allow collision
    {
      auto stage = std::make_unique<mtc::stages::ModifyPlanningScene>("allow collision (hand,object)");
      stage->allowCollisions("object",
                             task.getRobotModel()->getJointModelGroup(hand_group_name)->getLinkModelNamesWithCollisionGeometry(),
                             true);
      grasp->insert(std::move(stage));
    }

    // close hand
    {
      auto stage = std::make_unique<mtc::stages::MoveTo>("close hand", interpolation_planner);
      stage->setGroup(hand_group_name);
      stage->setGoal("close");
      grasp->insert(std::move(stage));
    }

    // attach object
    {
      auto stage = std::make_unique<mtc::stages::ModifyPlanningScene>("attach object");
      stage->attachObject("object", hand_frame);
      attach_object_stage = stage.get();
      grasp->insert(std::move(stage));
    }

    // lift object
    {
      auto stage = std::make_unique<mtc::stages::MoveRelative>("lift object", cartesian_planner);
      stage->properties().configureInitFrom(mtc::Stage::PARENT, { "group" });
      stage->setMinMaxDistance(0.1, 0.3);
      stage->setIKFrame(hand_frame);
      stage->properties().set("marker_ns", "lift_object");
      geometry_msgs::msg::Vector3Stamped vec;
      vec.header.frame_id = "world";
      vec.vector.z = 1.0;
      stage->setDirection(vec);
      grasp->insert(std::move(stage));
    }
    task.add(std::move(grasp));
  }

  // Move to Place
  {
    auto stage_move_to_place = std::make_unique<mtc::stages::Connect>(
        "move to place",
        mtc::stages::Connect::GroupPlannerVector{ { arm_group_name, sampling_planner },
                                                  { hand_group_name, sampling_planner } });
    stage_move_to_place->setTimeout(5.0);
    stage_move_to_place->properties().configureInitFrom(mtc::Stage::PARENT);
    task.add(std::move(stage_move_to_place));
  }

  // Place Object
  {
    auto place = std::make_unique<mtc::SerialContainer>("place object");
    task.properties().exposeTo(place->properties(), { "eef", "group", "ik_frame" });
    place->properties().configureInitFrom(mtc::Stage::PARENT, { "eef", "group", "ik_frame" });

    {
      auto stage = std::make_unique<mtc::stages::GeneratePlacePose>("generate place pose");
      stage->properties().configureInitFrom(mtc::Stage::PARENT);
      stage->properties().set("marker_ns", "place_pose");
      stage->setObject("object");

      geometry_msgs::msg::PoseStamped target_pose_msg;
      target_pose_msg.header.frame_id = "object";
      target_pose_msg.pose.position.y = 0.5;
      target_pose_msg.pose.orientation.w = 1.0;
      stage->setPose(target_pose_msg);
      stage->setMonitoredStage(attach_object_stage);

      auto wrapper = std::make_unique<mtc::stages::ComputeIK>("place pose IK", std::move(stage));
      wrapper->setMaxIKSolutions(2);
      wrapper->setMinSolutionDistance(1.0);
      wrapper->setIKFrame("object");
      wrapper->properties().configureInitFrom(mtc::Stage::PARENT, { "eef", "group" });
      wrapper->properties().configureInitFrom(mtc::Stage::INTERFACE, { "target_pose" });
      place->insert(std::move(wrapper));
    }

    {
      auto stage = std::make_unique<mtc::stages::MoveTo>("open hand", interpolation_planner);
      stage->setGroup(hand_group_name);
      stage->setGoal("open");
      place->insert(std::move(stage));
    }

    {
      auto stage = std::make_unique<mtc::stages::ModifyPlanningScene>("forbid collision (hand,object)");
      stage->allowCollisions("object",
                             task.getRobotModel()->getJointModelGroup(hand_group_name)->getLinkModelNamesWithCollisionGeometry(),
                             false);
      place->insert(std::move(stage));
    }

    {
      auto stage = std::make_unique<mtc::stages::ModifyPlanningScene>("detach object");
      stage->detachObject("object", hand_frame);
      place->insert(std::move(stage));
    }

    {
      auto stage = std::make_unique<mtc::stages::MoveRelative>("retreat", cartesian_planner);
      stage->properties().configureInitFrom(mtc::Stage::PARENT, { "group" });
      stage->setMinMaxDistance(0.1, 0.3);
      stage->setIKFrame(hand_frame);
      stage->properties().set("marker_ns", "retreat");
      geometry_msgs::msg::Vector3Stamped vec;
      vec.header.frame_id = "world";
      vec.vector.x = -0.5;
      stage->setDirection(vec);
      place->insert(std::move(stage));
    }
    task.add(std::move(place));
  }

  // return home
  {
    auto stage = std::make_unique<mtc::stages::MoveTo>("return home", interpolation_planner);
    stage->properties().configureInitFrom(mtc::Stage::PARENT, { "group" });
    stage->setGoal("ready");
    task.add(std::move(stage));
  }

  return task;
}

void BrainArmNode::stopArmService(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*request*/,
                                  std::shared_ptr<std_srvs::srv::Trigger::Response> response)
{
  stop_requested_ = true;
  arm_group_->stop();
  hand_group_->stop();
  response->success = true;
  response->message = "Arm stopped";
  publishFeedback("success", "stop_service", "Emergency stop triggered via service");
}

void BrainArmNode::goHomeService(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*request*/,
                                 std::shared_ptr<std_srvs::srv::Trigger::Response> response)
{
  handleHome("go_home_service");
  response->success = true;
  response->message = "Going home";
}

void BrainArmNode::setupPlanningScene()
{
  moveit_msgs::msg::CollisionObject object;
  object.id = "object";
  object.header.frame_id = "world";
  object.primitives.resize(1);
  object.primitives[0].type = shape_msgs::msg::SolidPrimitive::CYLINDER;
  object.primitives[0].dimensions = { 0.1, 0.02 };

  geometry_msgs::msg::Pose pose;
  pose.position.x = 0.5;
  pose.position.y = -0.25;
  pose.position.z = 0.2;
  pose.orientation.w = 1.0;
  object.pose = pose;

  moveit::planning_interface::PlanningSceneInterface psi;
  psi.applyCollisionObject(object);
  RCLCPP_INFO(LOGGER, "Added collision object 'object' to planning scene");
}

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);

  rclcpp::NodeOptions options;
  options.automatically_declare_parameters_from_overrides(true);

  auto brain_arm_node = std::make_shared<BrainArmNode>(options);
  rclcpp::executors::MultiThreadedExecutor executor;

  auto spin_thread = std::make_unique<std::thread>([&executor, &brain_arm_node]() {
    executor.add_node(brain_arm_node->getNodeBaseInterface());
    executor.spin();
    executor.remove_node(brain_arm_node->getNodeBaseInterface());
  });

  // Setup planning scene after a short delay to ensure all nodes are ready
  rclcpp::sleep_for(std::chrono::seconds(1));
  brain_arm_node->setupPlanningScene();

  RCLCPP_INFO(LOGGER, "Brain-Arm simulation ready. Use fake_brain.py to send commands.");

  spin_thread->join();
  rclcpp::shutdown();
  return 0;
}
