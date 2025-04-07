import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, EmitEvent
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from launch.events import Shutdown
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

robot_model_list = [
    '3w', 
    '3w_v2'
]

def generate_launch_description():
    robot_model = os.environ.get("OMNI_ROBOT_MODEL", "3w")

    if robot_model not in robot_model_list:
        error_msg = f"The robot model specified in environment variable OMNI_ROBOT_MODEL is '{robot_model}', which is unknown.\nPlease choose from the following options:\n"

        for model in robot_model_list:
            error_msg += f"- {model}\n"
        
        print(error_msg)

        return LaunchDescription([
            EmitEvent(event=Shutdown(reason='Invalid robot model specified'))
        ])

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

    # Create a robot_state_publisher node
    pkg_path = get_package_share_directory(PACKAGE_NAME)
    xacro_file = os.path.join(pkg_path,'urdf', robot_model, 'main.urdf.xacro')
    robot_description_config = Command(['xacro ', xacro_file])
    
    params = {'robot_description': robot_description_config, 'use_sim_time': use_sim_time}
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
                         '.sdf',
                          ' -r',
                          ' -v 4'])
        ]
    )

    # Spawn the robot in Gazebo
    spawn_robot = Node(package='ros_gz_sim', executable='create',
                        arguments=['-topic', 'robot_description',
                                   '-name', robot_model,
                                   '-z', '0.1'],
                        output='screen')
    
    # gz bridge 
    bridge_params = os.path.join(get_package_share_directory(PACKAGE_NAME),'config', 'gz_bridge', f'gz_bridge_{robot_model}.yaml')
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
    if(robot_model == '3w'):
        spawn_wheel_controller = Node(package='controller_manager', executable='spawner',
                            arguments=['joint_state_broadcaster', 
                                        'wheel1_controller', 
                                        'wheel2_controller', 
                                        'wheel3_controller',
                                        'camera_servo_controller'],
                            output='screen')
        kinematics = Node(
            package=PACKAGE_NAME,
            executable="kinematics",
            parameters=[{"use_sim_time": use_sim_time}]
        )
    else:
        spawn_wheel_controller = Node(package='controller_manager', executable='spawner',
                            arguments=['joint_state_broadcaster', 
                                        'wheel1_controller', 
                                        'wheel2_controller', 
                                        'wheel3_controller',
                                        ],
                            output='screen')
        kinematics = Node(
            package=PACKAGE_NAME,
            executable="kinematics_v2",
            parameters=[{"use_sim_time": use_sim_time}]
        )


    
    # Create launch description and add actions
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(ign_resource_path)
    ld.add_action(node_robot_state_publisher)
    ld.add_action(ignition)
    ld.add_action(spawn_robot)
    ld.add_action(ros_gz_bridge)
    ld.add_action(spawn_wheel_controller)
    ld.add_action(kinematics)
    return ld