import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from pathlib import Path

PACKAGE_NAME = "ros2_omni_robot_sim"

ARGUMENTS = [
    DeclareLaunchArgument('world', 
                          default_value=os.path.join(get_package_share_directory(PACKAGE_NAME),"worlds","maze.sdf"),
                          description='Gazebo World'),
]

def generate_launch_description():
    # Source Environment (Need it to be able find mesh files)
    pkg_path = get_package_share_directory(PACKAGE_NAME)
    ign_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=[str(Path(pkg_path).parent.resolve())]
    )
    # launch robot state publisher
    # rsp_path = os.path.join(pkg_path, "launch", "rsp.launch.py")
    # robot_state_publisher = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource([rsp_path])
    # )

    # Create a robot_state_publisher node
    pkg_path = get_package_share_directory(PACKAGE_NAME)
    xacro_file = os.path.join(pkg_path,'urdf','3w_omni_robot.urdf.xacro')
    robot_description_config = Command(['xacro ', xacro_file])
    
    params = {'robot_description': robot_description_config}
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[params]
    )

    # launch gazebo
    ignition_launch_path = PathJoinSubstitution([
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
            ])
    ignition = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([ignition_launch_path]),
        launch_arguments=[
            ('gz_args', [LaunchConfiguration('world'),
                          ' -r',
                          ' -v 4'])
        ]
    )

    # Spawn the robot in Gazebo
    spawn_robot = Node(package='ros_gz_sim', executable='create',
                        arguments=['-topic', 'robot_description',
                                   '-name', '3w_omni_robot',
                                   '-z', '0.1'],
                        output='screen')
    
    # gz bridge 
    bridge_params = os.path.join(get_package_share_directory(PACKAGE_NAME),'config','gz_bridge.yaml')
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
                        arguments=['joint_state_broadcaster', 'wheel1_controller', 'wheel2_controller', 'wheel3_controller'],
                        output='screen')
    
    # Create launch description and add actions
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(ign_resource_path)
    ld.add_action(node_robot_state_publisher)
    # ld.add_action(robot_state_publisher)
    ld.add_action(ignition)
    ld.add_action(spawn_robot)
    ld.add_action(ros_gz_bridge)
    # ld.add_action(spawn_wheel_controller)
    return ld