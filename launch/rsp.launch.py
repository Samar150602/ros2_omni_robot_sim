import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, Command
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node

PACKAGE_NAME = "ros2_omni_robot_sim"

def generate_launch_description():
    # Process the URDF file
    print("here 1")
    pkg_path = get_package_share_directory(PACKAGE_NAME)
    xacro_file = os.path.join(pkg_path,'urdf','3w_omni_robot.urdf.xacro')
    robot_description_config = Command(['xacro ', xacro_file])
    print("here 2")
    
    # Create a robot_state_publisher node
    params = {'robot_description': robot_description_config}
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[params]
    )

    # Launch!
    return LaunchDescription([
        node_robot_state_publisher
    ])
