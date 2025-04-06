#include <chrono>
#include <memory>
#include <iostream>
#include <cmath>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include <tf2_ros/transform_broadcaster.h>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2/LinearMath/Matrix3x3.h>

using namespace std::chrono_literals;
using std::placeholders::_1;
using namespace std;

#define WHEEL_RADIUS  0.03
#define ROBOT_RADIUS  0.088

class OmniKinematics : public rclcpp::Node
{
public:
  OmniKinematics(int num_wheels_, double robot_radius_, double wheel_radius_, double heading_offset_ = 0)
  : Node("omni_kinematics"), count_(0)
  {
    N = num_wheels_; // num of wheel
    R = robot_radius_;
    r = wheel_radius_;
    heading_offset = heading_offset_;

    pub_wheel_1 = this->create_publisher<std_msgs::msg::Float64MultiArray>("wheel1_controller/commands", 10);
    pub_wheel_2 = this->create_publisher<std_msgs::msg::Float64MultiArray>("wheel2_controller/commands", 10);
    pub_wheel_3 = this->create_publisher<std_msgs::msg::Float64MultiArray>("wheel3_controller/commands", 10);
    pub_odometry = this->create_publisher<nav_msgs::msg::Odometry>("odom", 10);

    sub_cmd_vel = this->create_subscription<geometry_msgs::msg::Twist>("cmd_vel", 10, std::bind(&OmniKinematics::cmd_vel_callback, this, _1));
    sub_join_states = this->create_subscription<sensor_msgs::msg::JointState>("joint_states", 10, std::bind(&OmniKinematics::join_states_callback, this, _1));
    sub_imu = this->create_subscription<sensor_msgs::msg::Imu>("imu", 10, std::bind(&OmniKinematics::imu_callback, this, _1));

    tf_broadcaster = std::make_shared<tf2_ros::TransformBroadcaster>(*this);

    last_time = this->get_clock()->now();

    // this->declare_parameter("use_sim_time", rclcpp::ParameterValue(true));

    // timer_ = this->create_wall_timer(500ms, std::bind(&OmniKinematics::timer_callback, this));

    double C = 2 * r / sqrt(3);
    double h = 0 * M_PI / 180;
    mOd[0][0] = C * (cos(2 * M_PI / 3 + h) - (cos(2 * M_PI / 3 + h) - cos(h)) / 3);
    mOd[0][1] = C * (-cos(h) - (cos(2 * M_PI / 3 + h) - cos(h)) / 3);
    mOd[0][2] = C * (-(cos(2 * M_PI / 3 + h) - cos(h)) / 3);
    mOd[1][0] = C * (sin(2 * M_PI / 3 + h) - (sin(2 * M_PI / 3 + h) - sin(h)) / 3);
    mOd[1][1] = C * (-sin(h) - (sin(2 * M_PI / 3 + h) - sin(h)) / 3);
    mOd[1][2] = C * (-(sin(2 * M_PI / 3 + h) - sin(h)) / 3);
  }

private:

  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr pub_wheel_1;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr pub_wheel_2;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr pub_wheel_3;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr pub_odometry;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_cmd_vel;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr sub_join_states;
  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr sub_imu;

  std::shared_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster;

  size_t count_;
  int N; // num of wheel
  double r; // wheel radius
  double R; // Robot Radius
  double heading_offset;
  double mOd[2][3] = {{0, 0, 0}, {0, 0, 0}};
  double pos_x = 0;
  double pos_y = 0;
  double vx = 0;
  double vy = 0;
  double pitch = 0, roll = 0, yaw = 0;
  double w = 0;

  rclcpp::Time last_time;

  template <typename T>
  void print_vector(vector<T>& vec) {
    std::cout << "[ ";
    for (const auto& elem : vec) {
        std::cout << elem << " ";
    }
    std::cout << "]" << std::endl;
  }

  void cmd_vel_callback(const geometry_msgs::msg::Twist::SharedPtr msg) {
    vector<double> motor = calculate_motor_speed(msg->linear.x, msg->linear.y, msg->angular.z, 0);

    // for(int i = 0; i < N; i++) {
    //   cout << i << ": " << motor[i];
    //   if(i != N-1) cout << ", ";
    // }
    // cout << endl;

    set_motor_speed(motor[0], motor[1], motor[2]);
  }

  void join_states_callback(const sensor_msgs::msg::JointState::SharedPtr msg) {
    print_vector(msg->position);
     // Extract wheel angular velocities
        double w1 = 0;
        double w2 = 0;
        double w3 = 0;

        // Loop through all joint names and extract the velocities for the specified joints
        for (size_t i = 0; i < msg->name.size(); ++i)
        {
            if (msg->name[i] == "omni_wheel_joint_1")
            {
                w1 = msg->velocity[i];
            }
            else if (msg->name[i] == "omni_wheel_joint_2")
            {
                w2 = msg->velocity[i];
            }
            else if (msg->name[i] == "omni_wheel_joint_3")
            {
                w3 = msg->velocity[i];
            }
        }

        // Convert to linear velocity
        // double V1 = r * w1;
        // double V2 = r * w2;
        // double V3 = r * w3;

        double vx = (mOd[0][0] * w1 + mOd[0][1] * w2 + mOd[0][2] * w3);
        double vy = (mOd[1][0] * w1 + mOd[1][1] * w2 + mOd[1][2] * w3);

        rclcpp::Time current_time = this->get_clock()->now();
        double dt = (current_time - last_time).seconds();
        last_time = current_time;

        // RCLCPP_INFO(this->get_logger(), "Current Time (seconds): %f, dt: %f", current_time.seconds(), dt);

        pos_x += vx * cos(yaw) * dt - vy * sin(yaw) * dt;
        pos_y += vx * sin(yaw) * dt + vy * cos(yaw) * dt;
        // pos_x = 12;
        // pos_y = 13;
        // RCLCPP_INFO(this->get_logger(), "%f %f %f %f %f", w1, w2, w3, vx, vy);
        publish_odom(current_time);
  }

  void imu_callback(const sensor_msgs::msg::Imu::SharedPtr msg) {
    w = msg->angular_velocity.z;
    // Convert quaternion to yaw (heading)
    tf2::Quaternion q(
        msg->orientation.x,
        msg->orientation.y,
        msg->orientation.z,
        msg->orientation.w
    );

    tf2::Matrix3x3 m(q);
    m.getRPY(roll, pitch, yaw); // Extract roll, pitch, and yaw

    // RCLCPP_INFO(this->get_logger(), "Yaw: %f", yaw);
}

  void publish_odom(rclcpp::Time current_time) {
    // Create the odometry message
    nav_msgs::msg::Odometry odom_msg;
    odom_msg.header.stamp = current_time;
    odom_msg.header.frame_id = "odom";
    odom_msg.child_frame_id = "base_footprint";

    // Position
    odom_msg.pose.pose.position.x = pos_x;
    odom_msg.pose.pose.position.y = pos_y;
    odom_msg.pose.pose.position.z = 0.0;

    // Orientation (Quaternion)
    tf2::Quaternion q;
    q.setRPY(0, 0, yaw);
    odom_msg.pose.pose.orientation.x = q.x();
    odom_msg.pose.pose.orientation.y = q.y();
    odom_msg.pose.pose.orientation.z = q.z();
    odom_msg.pose.pose.orientation.w = q.w();

    // Linear velocity
    odom_msg.twist.twist.linear.x = vx;
    odom_msg.twist.twist.linear.y = vy;
    odom_msg.twist.twist.angular.z = w;

    
    // Publish odometry
    pub_odometry->publish(odom_msg);

    // Publish TF transform
    geometry_msgs::msg::TransformStamped odom_tf;
    odom_tf.header.stamp = current_time;
    odom_tf.header.frame_id = "odom";
    odom_tf.child_frame_id = "base_footprint";
    odom_tf.transform.translation.x = pos_x;
    odom_tf.transform.translation.y = pos_y;
    odom_tf.transform.translation.z = 0.0;
    odom_tf.transform.rotation = odom_msg.pose.pose.orientation;
    
    // RCLCPP_INFO(this->get_logger(), "%f %f", pos_x, pos_y);
    tf_broadcaster->sendTransform(odom_tf);
  }

  vector<double> calculate_motor_speed(float x_, float y_, float w_, float heading_offset_) {
    float del_angle_ = 360 / N;
    vector<double> motor(3, 0);

    for(int i = 0; i < N; i++){
      motor[i] = (-x_ * sin((del_angle_ * i + heading_offset_) * M_PI / 180))/r;
      motor[i] += (y_ * cos((del_angle_ * i + heading_offset_) * M_PI / 180))/r;
      motor[i] += (w_ * R)/r;
    }

    return motor;
  }

  void set_motor_speed(double s1, double s2, double s3) {
    auto s1_message = std_msgs::msg::Float64MultiArray();
    auto s2_message = std_msgs::msg::Float64MultiArray();
    auto s3_message = std_msgs::msg::Float64MultiArray();

    s1_message.data = {s1};
    s2_message.data = {s2};
    s3_message.data = {s3};

    pub_wheel_1->publish(s1_message);
    pub_wheel_2->publish(s2_message);
    pub_wheel_3->publish(s3_message);
  }
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<OmniKinematics>(3, ROBOT_RADIUS, WHEEL_RADIUS));
  rclcpp::shutdown();
  return 0;
}
