<h1 style="font-size: 3em;">ROS 2 Integration for Franka Robotics Research Robots</h1>

[![CI](https://github.com/frankarobotics/franka_ros2/actions/workflows/ci.yml/badge.svg)](https://github.com/frankarobotics/franka_ros2/actions/workflows/ci.yml)


## Prerequisites

## Local Machine Installation
1. **Install ROS 2 Development environment**

    _**franka_ros2**_ is built upon _**ROS 2 Jazzy**_.

    To set up your ROS 2 environment, follow the official _**jazzy**_ installation instructions provided [**here**](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).
    The guide discusses two main installation options: **Desktop** and **Bare Bones**.

    #### Choose **one** of the following:
    - **ROS 2 "Desktop Install"** (`ros-humble-desktop`)
      Includes a full ROS 2 installation with GUI tools and visualization packages (e.g., Rviz and Gazebo).
      **Recommended** for users who need simulation or visualization capabilities.

    - **"ROS-Base Install (Bare Bones)"** (`ros-humble-ros-base`)
      A minimal installation that includes only the core ROS 2 libraries.
      Suitable for resource-constrained environments or headless systems.

    ```bash
    # replace <YOUR CHOICE> with either ros-humble-desktop or ros-humble-ros-base
    sudo apt install <YOUR CHOICE>
    ```
    ---
    Also install the **Development Tools** package:
    ```bash
    sudo apt install ros-dev-tools
    ```
    Installing the **Desktop** or **Bare Bones** should automatically source the **ROS 2** environment but, under some circumstances you may need to do this again:
    ```bash
    source /opt/ros/jazzy/setup.sh
    ```

2. **Create a ROS 2 Workspace:**
   ```bash
   mkdir -p ~/franka_ros2_ws/src
   cd ~/franka_ros2_ws  # not into src
   ```
3. **Clone the Repositories:**
   ```bash
    git clone https://github.com/frankarobotics/franka_ros2.git src
    ```
4. **Install the dependencies**
    ```bash
    vcs import src < src/franka.repos --recursive --skip-existing
    ```
5. **Detect and install project dependencies**
   ```bash
   rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
   ```
6. **Build**
   ```bash
   # use the --symlinks option to reduce disk usage, and facilitate development.
   colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
   ```
7. **Adjust Enviroment**
   ```bash
   # Adjust environment to recognize packages and dependencies in your newly built ROS 2 workspace.
   source install/setup.sh
   ```

## Docker Container Installation
The **franka_ros2** package includes a `Dockerfile` and a `docker-compose.yml`, which allows you to use `franka_ros2` packages without manually installing **ROS 2**. Also, the support for Dev Containers in Visual Studio Code is provided.

For detailed instructions, on preparing VSCode to use the `.devcontainer` follow the setup guide from [VSCode devcontainer_setup](https://code.visualstudio.com/docs/devcontainers/tutorial).

1. **Clone the Repositories:**
    ```bash
    git clone https://github.com/frankarobotics/franka_ros2.git
    cd franka_ros2
    ```
    We provide separate instructions for using Docker with Visual Studio Code or the command line. Choose one of the following options:

    Option A: (Deleted)

    Option B: Set up and use Docker with Visual Studio Code's Docker support.
   

#### Option B: using Dev Containers in Visual Studio Code

  2. **Open Visual Studio Code ...**

        Then, open folder  `franka_ros2`

  3. **Choose `Reopen in container` when prompted.**

      The container will be built automatically, as required.

  4. **Clone the latests dependencies:**
      ```bash
      vcs import src < src/franka.repos --recursive --skip-existing
      ```

  5. **Open a terminal and build the workspace:**
      ```bash
      colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
      ```
  6. **Source the built workspace environment:**
      ```bash
      source install/setup.bash
      ```


# Test the build
   ```bash
   colcon test
   ```
> Remember, franka_ros2 is under development.
> Warnings can be expected.

# Run a sample ROS 2 application

To verify that your setup works correctly without a robot, you can run the following command to use dummy hardware:

```bash
ros2 launch franka_fr3_moveit_config moveit.launch.py robot_ip:=dont-care use_fake_hardware:=true
```

If you want to run this example with namespaces, you would need to use the argument `namespace` and manually write your namespace in `moveit.rviz` under `Move Group Namespace`.

# Run a ROS 2 example controller

To run any example controller, make sure to add your desired configuration in `franka.config.yaml` and run:

```bash
ros2 launch franka_bringup example.launch.py controller_name:=your_desired_controller
```
You can select one of the controllers from `controllers.yaml`.

# Run Gazebo examples with ROS 2

If you want to use Gazebo to run your code, you can find some examples here: [franka_gazebo](./franka_gazebo/README.md)


