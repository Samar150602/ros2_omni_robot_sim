#include <chrono>
#include <memory>
#include <iostream>
#include <cmath>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"

using namespace std::chrono_literals;
using std::placeholders::_1;
using namespace std;

#define WHEEL_RADIUS  6.0

class OmniKinematics : public rclcpp::Node
{
public:
  OmniKinematics(int num_wheels_, double robot_radius_, double wheel_radius_, double heading_offset_ = 0)
  : Node("omni_kinematics"), count_(0)
  {
    N = num_wheels_; // num of wheel
    robot_radius = robot_radius_;
    wheel_radius = wheel_radius_;
    heading_offset = heading_offset_;

    pub_wheel_1 = this->create_publisher<std_msgs::msg::Float64MultiArray>("wheel1_controller/commands", 10);
    pub_wheel_2 = this->create_publisher<std_msgs::msg::Float64MultiArray>("wheel2_controller/commands", 10);
    pub_wheel_3 = this->create_publisher<std_msgs::msg::Float64MultiArray>("wheel3_controller/commands", 10);

    sub_cmd_vel = this->create_subscription<geometry_msgs::msg::Twist>("cmd_vel", 10, std::bind(&OmniKinematics::cmd_vel_callback, this, _1));
    // timer_ = this->create_wall_timer(500ms, std::bind(&OmniKinematics::timer_callback, this));
  }

private:

  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr pub_wheel_1;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr pub_wheel_2;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr pub_wheel_3;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr pub_odometry;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_cmd_vel;
  size_t count_;
  int N; // num of wheel
  double wheel_radius;
  double robot_radius;
  double heading_offset;

  void cmd_vel_callback(const geometry_msgs::msg::Twist::SharedPtr msg) {
    vector<double> motor = calculate_motor_speed(msg->linear.x, msg->linear.y, msg->angular.z, 0);

    // for(int i = 0; i < N; i++) {
    //   cout << i << ": " << motor[i];
    //   if(i != N-1) cout << ", ";
    // }
    // cout << endl;

    set_motor_speed(motor[0], motor[1], motor[2]);
  }

  vector<double> calculate_motor_speed(float x_, float y_, float w_, float heading_offset_) {
    float del_angle_ = 360 / N;
    vector<double> motor(3, 0);

    for(int i = 0; i < N; i++){
      motor[i] = (-x_ * sin((del_angle_ * i + heading_offset_) * M_PI / 180))/wheel_radius;
      motor[i] += (y_ * cos((del_angle_ * i + heading_offset_) * M_PI / 180))/wheel_radius;
      motor[i] += (w_ * robot_radius)/wheel_radius;
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
  rclcpp::spin(std::make_shared<OmniKinematics>(3, 0.1, 0.01));
  rclcpp::shutdown();
  return 0;
}
