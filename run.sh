#!/bin/bash

docker run -p 6080:80 -v $PWD/nn_agent:/home/apple_picking_robot/ros/src/nn_agent -it pp_applepicker "$@"
