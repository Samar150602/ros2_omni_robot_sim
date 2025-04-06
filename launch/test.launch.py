import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from pathlib import Path

PACKAGE_NAME = "ros2_omni_robot_sim"
ARGUMENTS = [
    DeclareLaunchArgument('world', 
                          default_value="maze2",
                          description='Gazebo World'),
    DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use sim time if true'),
]

def generate_launch_description():
    # Get the package directory
    pkg_share = get_package_share_directory(PACKAGE_NAME)

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Source Environment (Need it to be able find mesh files)
    pkg_path = get_package_share_directory(PACKAGE_NAME)
    ign_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=[
            str(Path(pkg_path).parent.resolve()), ":",
             os.path.join(pkg_path, 'worlds'),
            ]
    )

    # Path to the URDF file
    xacro_file = os.path.join(pkg_share, 'urdf', '3w_v2', 'main.urdf.xacro')

    robot_description = Command(['xacro ', xacro_file])

    # Nodes to launch
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': use_sim_time}]
    )

    # launch gazebo
    ignition_launch_path = PathJoinSubstitution([
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
            ])
    
    ignition = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([ignition_launch_path]),
        launch_arguments=[
            ('gz_args', [LaunchConfiguration('world'),
                         '.sdf',
                          ' -r',
                          ' -v 4'])
        ]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', os.path.join(pkg_share, 'rviz', 'test.rviz')]  # Optional RViz config file
    )

    # Spawn the robot in Gazebo
    spawn_robot = Node(package='ros_gz_sim', executable='create',
                        arguments=['-topic', 'robot_description',
                                   '-name', '3w_omni_robot',
                                   '-z', '0.1'],
                        output='screen')
    
    # gz bridge 
    bridge_params = os.path.join(get_package_share_directory(PACKAGE_NAME),'config', 'gz_bridge', 'gz_bridge_3w_v2.yaml')
    ros_gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            '--ros-args',
            '-p',
            f'config_file:={bridge_params}',
        ]
    )

    
    # spawn controller 
    spawn_wheel_controller = Node(package='controller_manager', executable='spawner',
                        arguments=['joint_state_broadcaster', 
                                    'wheel1_controller', 
                                    'wheel2_controller', 
                                    'wheel3_controller'],
                        output='screen')

    kinematics = Node(
        package=PACKAGE_NAME,
        executable="kinematics_v2",
        parameters=[{"use_sim_time": use_sim_time}]
    )
    
    # Create the launch description
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(ign_resource_path)
    ld.add_action(robot_state_publisher_node)
    ld.add_action(ignition)
    ld.add_action(spawn_robot)
    ld.add_action(ros_gz_bridge)
    ld.add_action(spawn_wheel_controller)
    ld.add_action(kinematics)
    ld.add_action(rviz_node)
    return ld