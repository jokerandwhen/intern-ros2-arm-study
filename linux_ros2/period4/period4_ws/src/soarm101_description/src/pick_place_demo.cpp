/**
 * SO-ARM101 抓取放置演示节点
 * 控制机械臂完成简单的方块抓取放置任务
 */
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <vector>
#include <cmath>

class PickPlaceDemo : public rclcpp::Node
{
public:
    PickPlaceDemo() : Node("pick_place_demo"), state_(INIT), elapsed_time_(0.0)
    {
        // 发布关节状态
        joint_pub_ = this->create_publisher<sensor_msgs::msg::JointState>("/joint_states", 10);

        // 定时器：50Hz
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(20),
            std::bind(&PickPlaceDemo::timer_callback, this));

        // 初始化关节名称
        joint_names_ = {"joint1", "joint2", "joint3", "joint4", "joint5", "joint6",
                        "gripper_right_joint"};

        RCLCPP_INFO(this->get_logger(), "抓取放置演示节点已启动");
        RCLCPP_INFO(this->get_logger(), "轨迹序列: 预备 -> 抓取 -> 提升 -> 移动 -> 放置 -> 返回");
    }

private:
    // 状态机
    enum State
    {
        INIT,
        READY,
        APPROACH,
        GRASP,
        LIFT,
        MOVE,
        RELEASE,
        RETURN,
        DONE
    };

    // 关节位置结构体
    struct JointPosition
    {
        std::vector<double> positions;
        double duration;
    };

    // 插值计算
    std::vector<double> interpolate(const std::vector<double> &start,
                                     const std::vector<double> &end,
                                     double t)
    {
        std::vector<double> result(start.size());
        for (size_t i = 0; i < start.size(); ++i)
        {
            result[i] = start[i] + (end[i] - start[i]) * t;
        }
        return result;
    }

    // 获取目标位置
    JointPosition get_target_position(State state)
    {
        // 所有角度单位：弧度
        // joint1-5: 旋转关节
        // joint6: gripper (0=闭合, 0.014=张开)

        switch (state)
        {
        case READY:
            // 预备位置（中立姿态）
            return {{
                        0.0,    // joint1: 0°
                        0.0,    // joint2: 0°
                        0.0,    // joint3: 0°
                        0.0,    // joint4: 0°
                        0.0,    // joint5: 0°
                        0.014,  // joint6: gripper张开
                        0.014   // gripper_right_joint
                    },
                    2.0};

        case APPROACH:
            // 接近目标位置（前倾）
            return {{
                        0.0,    // joint1: 0°
                        0.3,    // joint2: ~17° (前倾)
                        -0.5,   // joint3: ~-28° (肘部弯曲)
                        0.2,    // joint4: ~11° (腕部调整)
                        0.0,    // joint5: 0°
                        0.014,  // joint6: gripper张开
                        0.014   // gripper_right_joint
                    },
                    2.0};

        case GRASP:
            // 抓取位置（gripper闭合）
            return {{
                        0.0,   // joint1: 0°
                        0.3,   // joint2: ~17°
                        -0.5,  // joint3: ~-28°
                        0.2,   // joint4: ~11°
                        0.0,   // joint5: 0°
                        0.0,   // joint6: gripper闭合
                        0.0    // gripper_right_joint
                    },
                    1.5};

        case LIFT:
            // 提升位置（向上）
            return {{
                        0.0,    // joint1: 0°
                        -0.2,   // joint2: ~-11° (向上抬)
                        -0.3,   // joint3: ~-17°
                        0.1,    // joint4: ~6°
                        0.0,    // joint5: 0°
                        0.0,    // joint6: gripper保持闭合
                        0.0     // gripper_right_joint
                    },
                    2.0};

        case MOVE:
            // 移动到放置位置（旋转90°）
            return {{
                        1.57,   // joint1: 90° (旋转)
                        -0.2,   // joint2: ~-11°
                        -0.3,   // joint3: ~-17°
                        0.1,    // joint4: ~6°
                        0.0,    // joint5: 0°
                        0.0,    // joint6: gripper保持闭合
                        0.0     // gripper_right_joint
                    },
                    2.0};

        case RELEASE:
            // 放置位置（gripper张开）
            return {{
                        1.57,   // joint1: 90°
                        -0.2,   // joint2: ~-11°
                        -0.3,   // joint3: ~-17°
                        0.1,    // joint4: ~6°
                        0.0,    // joint5: 0°
                        0.014,  // joint6: gripper张开
                        0.014   // gripper_right_joint
                    },
                    1.5};

        case RETURN:
            // 返回预备位置
            return {{
                        0.0,    // joint1: 0°
                        0.0,    // joint2: 0°
                        0.0,    // joint3: 0°
                        0.0,    // joint4: 0°
                        0.0,    // joint5: 0°
                        0.014,  // joint6: gripper张开
                        0.014   // gripper_right_joint
                    },
                    2.0};

        default:
            return {{
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.014,
                        0.014},
                    1.0};
        }
    }

    // 定时器回调
    void timer_callback()
    {
        auto msg = sensor_msgs::msg::JointState();
        msg.header.stamp = this->now();
        msg.name = joint_names_;

        State next_state = state_;
        JointPosition target = get_target_position(state_);

        if (state_ == INIT)
        {
            // 初始化：直接跳转到READY
            current_positions_ = target.positions;
            start_positions_ = current_positions_;  // 初始化start_positions_
            msg.position = current_positions_;  // 关键修复：设置msg.position
            next_state = READY;
            elapsed_time_ = 0.0;
            RCLCPP_INFO(this->get_logger(), "状态: READY (预备位置)");
        }
        else if (state_ != DONE)
        {
            // 插值运动
            elapsed_time_ += 0.02;
            double t = std::min(elapsed_time_ / target.duration, 1.0);

            // 平滑插值（使用三次多项式）
            double smooth_t = 3 * t * t - 2 * t * t * t;

            current_positions_ = interpolate(start_positions_, target.positions, smooth_t);
            msg.position = current_positions_;

            // 状态转换
            if (elapsed_time_ >= target.duration)
            {
                elapsed_time_ = 0.0;
                start_positions_ = current_positions_;

                switch (state_)
                {
                case READY:
                    next_state = APPROACH;
                    RCLCPP_INFO(this->get_logger(), "状态: APPROACH (接近目标)");
                    break;
                case APPROACH:
                    next_state = GRASP;
                    RCLCPP_INFO(this->get_logger(), "状态: GRASP (抓取)");
                    break;
                case GRASP:
                    next_state = LIFT;
                    RCLCPP_INFO(this->get_logger(), "状态: LIFT (提升)");
                    break;
                case LIFT:
                    next_state = MOVE;
                    RCLCPP_INFO(this->get_logger(), "状态: MOVE (移动到放置位置)");
                    break;
                case MOVE:
                    next_state = RELEASE;
                    RCLCPP_INFO(this->get_logger(), "状态: RELEASE (放置)");
                    break;
                case RELEASE:
                    next_state = RETURN;
                    RCLCPP_INFO(this->get_logger(), "状态: RETURN (返回预备位置)");
                    break;
                case RETURN:
                    next_state = READY;  // 循环回到READY状态
                    elapsed_time_ = 0.0;
                    start_positions_ = current_positions_;
                    RCLCPP_INFO(this->get_logger(), "状态: READY (重复任务)");
                    break;
                default:
                    break;
                }
            }
        }
        else
        {
            // 完成：保持最终位置
            msg.position = current_positions_;
        }

        state_ = next_state;
        joint_pub_->publish(msg);
    }

    // 成员变量
    rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_pub_;
    rclcpp::TimerBase::SharedPtr timer_;

    std::vector<std::string> joint_names_;
    std::vector<double> current_positions_;
    std::vector<double> start_positions_;

    State state_;
    double elapsed_time_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<PickPlaceDemo>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}