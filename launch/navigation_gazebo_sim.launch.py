import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from pathlib import Path

PACKAGE_NAME = "ros2_omni_robot_sim"

ARGUMENTS = []

def generate_launch_description():
    # launch gazebo with spawned robot
    gazebo_sim_path = PathJoinSubstitution([
                get_package_share_directory(PACKAGE_NAME), 'launch', 'gazebo_sim.launch.py'
            ])
    gazebo_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gazebo_sim_path])
    )

    nav2_launch_path = PathJoinSubstitution([
                get_package_share_directory("nav2_bringup"), 'launch', 'localization_launch.py'
            ])
    map_path = PathJoinSubstitution([
                get_package_share_directory(PACKAGE_NAME), 'launch', 'gazebo_sim.launch.py'
            ])
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([nav2_launch_path]),
        launch_arguments={"map": map_path, "use_sim_time": 'true'}.items()
    )

    rviz_config_path = PathJoinSubstitution([
                get_package_share_directory(PACKAGE_NAME), 'rviz', 'gz_sim.rviz'
            ])
    rviz2 = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_path],
            parameters=[{'use_sim_time': True}]
        )
    
    # Create launch description and add actions
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(gazebo_sim)
    ld.add_action(nav2_launch)
    ld.add_action(rviz2)
    return ld