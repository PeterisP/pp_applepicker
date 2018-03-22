FROM naurislv/apple_picking_robot

RUN pip install http://download.pytorch.org/whl/cpu/torch-0.3.1-cp27-cp27mu-linux_x86_64.whl 
RUN pip install torchvision 

RUN echo "cd /home/apple_picking_robot/ros" >> /root/.bashrc
WORKDIR /home/apple_picking_robot/ros

COPY go.sh ./
COPY nn_agent ./src/nn_agent
COPY project.launch ./launch/
