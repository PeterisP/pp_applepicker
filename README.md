# Learning agent for apple picking robot

This repository builds on top of [Apple picking robot repository](https://github.com/Naurislv/apple_picking_robot) and adds:

1. neural network based learning agent
2. build system to produce docker images

## Learning agent

Learning agent `nn_agent` integrates into [ROS](http://www.ros.org/)
source directory [`ros/src`](https://github.com/Naurislv/apple_picking_robot/tree/master/ros/src) of
Apple picking robot [repository](https://github.com/Naurislv/apple_picking_robot).
Uses [PyTorch](http://pytorch.org/) with [NVIDIA CUDA](https://developer.nvidia.com/cuda-toolkit) support if run on NVIDIA GPU.

## Docker image build system

Because there are various possible configuration option combinations,
a build script `build.sh` is used to generate `Dockerfile` along with dependencies for each configuration.

Possible configuration options:

* web based VNC desktop support to run with GUI based on [this repository](https://github.com/ct2034/docker-ubuntu-vnc-desktop)
* NVIDIA CUDA support for faster training of neural networks
* NVIDIA OpenGL rendering support for faster camera frame generation

**NOTE:** for NVIDIA GPU support [nvidia-docker](https://github.com/NVIDIA/nvidia-docker) is required.

Use `build.sh` to generate Dockerfile with specified configuration and build the docker image.

    ./build.sh [options] IMAGE

Options:

* `--desktop` - build image with VNC desktop
* `--nvidia-all` - build NVIDIA GPU enabled image (CUDA, cuDNN and OpenGL), autodetect CUDA and cuDNN versions of host system
* `--nvidia-cuda[=VER]` - build NVIDIA CUDA enabled image optionally with specific cuda version or autodetect from host system
* `--nvidia-cudnn[=VER]` - support NVIDIA cuDNN optionally with specific cuDNN version or autodetect from host system
* `--nvidia-opengl` - build image with NVIDIA OpenGL drivers, see [NVIDIA OpenGL support](#nvidia-opengl-support)
* `--nvidia-devel` - include development libraries for NVIDIA CUDA and cuDNN

If no `IMAGE` name is specified, the build script will generate `Dockerfile`
along with other depending files in the output directory (by default `tmp`).
There are different options to alter cache usage and directory locations.
Use `--help` to see all options.


Optional environment variables to set at runtime:

* `MASTER` - specify hostname/IP address of node running `roscore`, use this to connect a GUI to an already running simulation
* `VNC_PASSWORD` - password protect VNC desktop

## NVIDIA OpenGL support

At the moment `nvidia-docker` does not support OpenGL, hence in this project a workaround is used
that requires for NVIDIA OpenGL enabled docker images to be run using `nvrun.sh` script,
which executes `docker run` with NVIDIA runtime and mounts few other files and devices from the host system.
So, instead of running plain `docker run ...` you have to use `./nvrun.sh` script with your `docker run` arguments, e.g.,

    ./nvrun.sh --rm -it apple_picker:cuda-opengl

That does not apply to images built with NVIDIA CUDA support and without NVIDIA OpenGL support.
For these images use plain `nvidia-docker`, e.g.

    docker run --runtime=nvidia --rm -it apple_picker:cuda

Note the `--runtime=nvidia` argument.

## VNC desktop

The VNC desktop is a graphical desktop environment accessible via a VNC client in a web browser.
Inside the desktop environment the simulation can be launched with a graphical user interface
or the state of an already running simulation in a different container can be observed graphically.

Optionally the VNC desktop can be password protected for increased security.
For usage and technical details see the use case 8 in the next section.

## Docker image examples and use cases

1. Build a docker image without NVIDIA GPU or VNC desktop support

        ./build.sh apple_picker:plain

2. Build a docker image with VNC desktop, but without NVIDIA GPU support

        ./build.sh --desktop apple_picker:desktop

3. Build a docker image with NVIDIA CUDA support, but without NVIDIA OpenGL drivers and without VNC desktop

        ./build.sh --nvidia-cuda apple_picker:cuda

   Optionally you may also add `--nvidia-cudnn` to include NVIDIA cuDNN libraries and `--nvidia-devel` to include NVIDIA CUDA development libraries.

4. Build a docker image with NVIDIA CUDA and NVIDIA OpenGL support, but without VNC desktop

        ./build.sh --nvidia-cuda --nvidia-opengl apple_picker:cuda-opengl

   or including NVIDIA cuDNN support

        ./build.sh --nvidia-all apple_picker:cuda-cudnn-opengl

5. Build a docker image with NVIDIA CUDA and NVIDIA OpenGL support and also with VNC desktop

        ./build.sh --nvidia-cuda --nvidia-opengl --desktop apple_picker:desktop-cuda-opengl

6. Run image with NVIDIA CUDA support only (without NVIDIA OpenGL drivers)

        docker run --runtime=nvidia --rm -it apple_picker:cuda

7. Run image with NVIDIA CUDA and NVIDIA OpenGL support

        ./nvrun.sh --runtime=nvidia --rm -it apple_picker:cuda-opengl

8. Run image with VNC desktop and without any NVIDIA GPU support

        docker run --rm -it -p 8080:80 apple_picker:desktop

   To be able to connect to the VNC desktop from outside the container network,
   you have to map the port `80` of the container to some port on host system.
   In the above example the port `8080` on host system is mapped to the port `80` of the container.

   Optionally the VNC access can be restricted with a password

        docker run --rm -it -p 8080:80 -e VNC_PASSWORD=yourpassword apple_picker:desktop

   Open browser and navigate to [localhost:8080](http://localhost:8080) if the docker container
   is run locally or replace `localhost` with the hostname or IP address of the machine running the container.

   Inside the VNC desktop open terminal application, the working directory will be the root of
   [apple\_picking\_robot](https://github.com/Naurislv/apple_picking_robot) project.
   The simulation can now be started using the `./run_apple_picker.sh` script.

        ./run_apple_picker.sh -w dbaby -gg true

   Although it is possible to add `-r true` or even `-rv true` parameters to eventually get the camera view,
   a better option is to open another terminal instance and enter

        rqt_image_view -t /camera1/image_raw

   This will open the camera topic right away and set the window to stay always on top of the simulation window.

9. Run image with VNC desktop and with NVIDIA CUDA support, but without NVIDIA OpenGL drivers

        docker run --runtime=nvidia --rm -it -p 8080:80 apple_picker:desktop-cuda

10. Run image with VNC desktop and with NVIDIA CUDA and NVIDIA OpenGL support

        ./nvrun.sh --rm -it -p 8080:80 apple_picker:desktop-cuda

11. Create a setup with a headless training container and an optional VNC desktop with GUI for observing training progress

    11.1. Because [ROS](http://www.ros.org/) requires for all nodes to be fully accessible to each other (on all ports),
    a docker network has to be created (or legacy container linking with `--link` argument to `docker run` must be used)

        docker create network apnet

    where `apnet` is a chosen network name. This step has to be done only once.

    11.2. Run the headless simulation container specifying the network name and chosen alias name (`simnode` in this example)

        docker run --rm -it --net=apnet --net-alias simnode apple_picker:plain

    `bash` will be launched with the root of [apple\_picking\_robot](https://github.com/Naurislv/apple_picking_robot) project
    as the current working directory.

    Start the simulation using the `./run_apple_picker.sh` script

        ./run_apple_picker.sh -w dbaby

    11.3. Run the desktop VNC container specifying the same network and the network alias of simulation container

        docker run --rm -it --net=apnet -p 8080:80 -e MASTER=simnode apple_picker:desktop

    The environment variable `MASTER` is used to let ROS and [Gazebo](http://gazebosim.org/) know where the `roscore` is run.

    11.4. Open browser and navigate to [localhost:8080](http://localhost:8080) if containers are run locally
    or use the hostname or IP address of the remote machine where the containers are running.

    11.5. Inside container open terminal and enter `rqt_image_view -t /camera1/image_raw` to see the camera feed.

    11.6. Open another terminal instance and enter `gzclient --verbose` to open Gazebo client and follow the simulation.

    11.7. After the GUI is not needed anymore, it is safe to close the browser and stop the container running VNC desktop,
    the simulation on other container will continue without interruption.

## Prebuilt docker images

Some prebuilt docker images are available from dockerhub:

* `didzis/apple_picker:plain`
* `didzis/apple_picker:cuda`
* `didzis/apple_picker:cuda9.1`
* `didzis/apple_picker:opengl`
* `didzis/apple_picker:cuda-opengl`
* `didzis/apple_picker:cuda9.1-opengl`
* `didzis/apple_picker:desktop`
* `didzis/apple_picker:desktop-cuda`
* `didzis/apple_picker:desktop-cuda9.1`
* `didzis/apple_picker:desktop-cuda-opengl`
* `didzis/apple_picker:desktop-cuda9.1-opengl`
* `didzis/apple_picker:desktop-opengl`

If you use the prebuilt docker images listed above,
you may first pull the latest changes from github by running `git pull` from the shell. 

Note, that for the `opengl` version images above, you will need not only `nvidia-docker`,
but also the [`nvrun.sh`](nvrun.sh) script found in this repository.
You can download the script at the terminal using curl

    curl -sO https://raw.githubusercontent.com/PeterisP/pp_applepicker/nvidia-docker/nvrun.sh 

Or you can replace `./nvrun.sh ...` with

    curl -s https://raw.githubusercontent.com/PeterisP/pp_applepicker/nvidia-docker/nvrun.sh | bash -s ...

