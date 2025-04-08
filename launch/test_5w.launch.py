import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node

def generate_launch_description():
    # Get the package directory
    pkg_name = 'ros2_omni_robot_sim'
    pkg_share = get_package_share_directory(pkg_name)

    # Path to the URDF file
    xacro_file = os.path.join(pkg_share, 'urdf', '5w', 'main.urdf.xacro')

    robot_description = Command(['xacro ', xacro_file])

    # Declare launch arguments (optional, for flexibility)
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    # Nodes to launch
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': use_sim_time}]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', os.path.join(pkg_share, 'rviz', 'test.rviz')]  # Optional RViz config file
    )

    # Create the launch description
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'
        ),
        robot_state_publisher_node,
        rviz_node
    ])