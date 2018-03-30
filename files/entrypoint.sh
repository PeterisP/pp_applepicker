#!/bin/bash

if [ -n "$NVIDIA_OPENGL" ] && [ "$NVIDIA_OPENGL" != "0" ] && [ "$NVIDIA_OPENGL" != "false" ] && [ "$NVIDIA_OPENGL" != "f" ]; then
	[ -n "$VNC_DESKTOP" ] && HEADLESS_DISPLAY=1
	# NVIDIA OpenGL present, start Xorg server in background
	echo "Starting X server ..."
	VT=${VT#vt}
	# support multiple Xorg instances on single GPU:
	# https://devtalk.nvidia.com/default/topic/675094/linux/second-x-server-turns-video-singnal-off-on-other-card/
	Xorg -sharevts -novtswitch -noreset +extension GLX +extension RANDR +extension RENDER vt${VT:-10} :${HEADLESS_DISPLAY:-0} \
		> /dev/null 2> /dev/null &
	echo "X server log: /var/log/Xorg.${HEADLESS_DISPLAY:-0}.log"
	echo
else
	# No NVIDIA OpenGL, use Xfvb
	/usr/bin/Xvfb :${HEADLESS_DISPLAY:-0} -screen 0 1024x768x16 &
fi

# if [ -n "$VNC_DESKTOP" ]; then
# 	export VNC_DISPLAY_SIZE=${VNC_DISPLAY_SIZE:-1024x768}
#
# 	cat > /etc/supervisor/conf.d/xrandr.conf << EOF
# [program:xrandr]
# priority=15
# directory=/root
# command=/usr/bin/xrandr --fb %(ENV_VNC_DISPLAY_SIZE)s
# user=root
# autostart=true
# autorestart=false
# stopsignal=QUIT
# environment=DISPLAY=":1",HOME="/root",USER="root"
# stdout_logfile=/var/log/xrandr.log
# redirect_stderr=true
# EOF
# fi

export DISPLAY=:${HEADLESS_DISPLAY:-0}.0

[ -n "$VNC_DESKTOP" ] && [ -z "$@" ] && /ros_entrypoint.sh /startup.sh || /ros_entrypoint.sh "$@"
