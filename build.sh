#!/bin/bash

update_dockerfile() {
	# [--new|--init|--create] OUTPUT-DOCKERFILE [--image] IMAGE|SOURCE-DOCKER|URL [NAME]
	local new output_dockerfile image src url name bn sed_exp
	new=
	([ "$1" == "--new" ] || [ "$1" == "--init" ] || [ "$1" == "--create" ]) && new=1 && shift
	([ "$1" == "--multi-stage" ] || [ "$1" == "--ms" ] || [ "$1" == "--append" ]) && new=0 && shift
	output_dockerfile="$1"
	shift
	[ -z "$output_dockerfile" ] && >&2 echo "error: output dockerfile not specified" && return 1
	image=0
	if [ "$1" == "--image" ]; then
		image=1
		[ -z "$new" ] && new=1
		shift
	fi
	[ -z "$new" ] && new=0
	src="$1"
	shift
	url=
	([ "${src##http://}" != "$src" ] || [ "${src##https://}" != "$src" ]) && url="$src"
	name="$1"
	shift
	if [ -z "$name" ]; then
		if [ $image -eq 1 ]; then
			name="$src"
		else
			# try to autodetect name if not specified
			bn="$(basename "$src")"
			if [ "$bn" != "Dockerfile" ]; then
				if [ "${bn##Dockerfile}" != "$bn" ]; then
					name="${bn#Dockerfile?}"
				else
					name="$bn"
				fi
			else
				name="`basename "$(dirname "$src")"`"	# parent directory name
			fi
		fi
	fi
	if [ $image -eq 0 ]; then
		echo "## --- $name: $src" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
	fi

	if [ $image -eq 1 ]; then
		[ $new -eq 1 ] && echo "FROM $src" > "$output_dockerfile"
		[ $new -eq 0 ] && echo "FROM $src" >> "$output_dockerfile"
		# echo >> "$output_dockerfile"
		# echo "# vim: set filetype=dockerfile:" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
	elif [ $new -eq 0 ]; then
		# sed_exp='/^FROM\s/d'		# delete FROM statement
		sed_exp='/^FROM\s/s/^/#/'	# comment out FROM statement
		# download file from URL, remove FROM statements and append to specified output_dockerfile
		if [ "$url" ]; then
			curl -sL "$src" | sed -e "$sed_exp" >> "$output_dockerfile"
		else
			cat "$src" | sed -e "$sed_exp" >> "$output_dockerfile"
		fi
	else
		if [ "$url" ]; then
			curl -sL "$src" > "$output_dockerfile"
		else
			cat "$src" > "$output_dockerfile"
		fi
	fi
	if [ $image -eq 0 ]; then
		echo >> "$output_dockerfile"
		echo "## --- END of $name ---" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
	fi
}

add_vim_modeline() {
	echo "# vim: set filetype=dockerfile:" >> "$1"
}

build_image() {
	local script_path="$(cd "`dirname "$0"`"; pwd)"
	if [ ! -d "$script_path" ]; then
		>&2 echo "warning: unable to determine script path, will use working directory path; please set base_path variable to script path"
		script_path=.
	fi
	local base_path="${base_path:-$script_path}"
	local cuda_path="${cuda_path:-/usr/local/cuda}"
	[ ! -f "$cuda_path/lib64/libcudart.so" ] && >&2 echo "error: cuda_path=$cuda_path is not valid" && return 1
	local nvidia_cuda_default="$(x=`ls -l "$cuda_path" 2> /dev/null`; echo ${x##*-})"
	local nvidia_cudnn_default="$(x=`ls -l "$cuda_path/lib64/libcudnn.so" 2> /dev/null`; echo ${x##*.})"
	nvidia_cuda_default="${nvidia_cuda_default:-9.1}"
	local nvidia_cuda=
	local nvidia_cudnn=
	local nvidia_opengl=0
	local nvidia_devel=0
	local vnc_desktop=0
	local image_name=
	# local cache_directory="$base_path/.cache"
	# local output_directory="$base_path/tmp"
	local cache_directory=".cache"
	local output_directory="tmp"
	local tmp_directory=
	local no_cache=0
	local purge_cache=0
	local clean=0
	local cleanup=0
	local skip_build=0
	local suffix=
	while [ $# -gt 0 ]; do
		case "$1" in
			-h|--help)
				echo "$0 [options] [IMAGE]"
				echo
				echo "build apple picker docker images using specified configuration"
				echo
				echo "IMAGE                        output docker image name"
				echo
				echo "options:"
				echo
				echo "--nvidia-cuda[=VER]          enable NVIDIA CUDA support (default version: $nvidia_cuda_default)"
				echo "--nvidia-cudnn[=VER]         use NVIDIA CUDA with cuDNN support (default version: $nvidia_cudnn_default)"
				echo "--nvidia-opengl              enable NVIDIA OpenGL support (use nvrun.sh to run the container)"
				echo "--nvidia-all                 enable NVIDIA CUDA, cuDNN and OpenGL support"
				echo "--nvidia-devel               use NVIDIA development images"
				echo "                             same as specifying --nvidia-cuda, --nvidia-cudnn and --nvidia-opengl"
				echo "--desktop                    enable desktop with VNC"
				echo "--suffix[=]SUFFIX            suffix for Dockerfile, e.g., --suffix=-cuda will generate Dockerfile-cuda"
				echo "--output[=]DIR               output directory (default: $output_directory);"
				echo "                             empty for fresh tmp dir with mktemp,"
				echo "                             implies --cleanup, --clean will be already satisfied"
				echo "--cache[=]DIR                cache directory (default: $cache_directory)"
				echo "--tmp[=]DIR                  temporary directory in case cache is disabled, by default will use mktemp"
				echo "--purge-cache                purge cache"
				echo "--no-cache                   do not use cache"
				echo "--clean                      remove temporary files from previous build"
				echo "--cleanup                    remove temporary files after image is built"
				echo "--skip-build                 create Dockerfile, but do not build, disables --cleanup"
				echo
				return 0
				;;
			--nvidia-cuda)
				[ -z "$nvidia_cuda" ] && nvidia_cuda="$nvidia_cuda_default"
				shift
				;;
			--nvidia-cuda=*)
				nvidia_cuda="${1#*=}"
				shift
				;;
			--nvidia-cudnn)
				[ -z "$nvidia_cudnn" ] && nvidia_cudnn="$nvidia_cudnn_default"
				shift
				;;
			--nvidia-cudnn=*)
				nvidia_cudnn="${1#*=}"
				shift
				;;
			--nvidia-opengl)
				nvidia_opengl=1
				shift
				;;
			--nvidia-devel)
				nvidia_devel=1
				shift
				;;
			--nvidia-all)
				[ -z "$nvidia_cuda" ] && nvidia_cuda="$nvidia_cuda_default"
				[ -z "$nvidia_cudnn" ] && nvidia_cudnn="$nvidia_cudnn_default"
				nvidia_opengl=1
				shift
				;;
			--desktop)
				vnc_desktop=1
				shift
				;;
			--suffix)
				shift
				suffix="$1"
				shift
				;;
			--suffix=*)
				suffix="${1#*=}"
				shift
				;;
			--output)
				shift
				output_directory="$1"
				shift
				;;
			--output=*)
				output_directory="${1#*=}"
				shift
				;;
			--cache)
				shift
				cache_directory="$1"
				shift
				;;
			--cache=*)
				cache_directory="${1#*=}"
				shift
				;;
			--tmp)
				shift
				tmp_directory="$1"
				shift
				;;
			--tmp=*)
				tmp_directory="${1#*=}"
				shift
				;;
			--no-cache)
				no_cache=1
				shift
				;;
			--purge-cache)
				purge_cache=1
				shift
				;;
			--clean)
				clean=1
				shift
				;;
			--cleanup)
				cleanup=1
				shift
				;;
			--skip-build)
				skip_build=1
				shift
				;;
			--)
				break
				;;
			*)
				[ -n "$image_name" ] && >&2 echo "error: invalid argument: $1" && return 1
				image_name="$1"
				shift
				;;
		esac
	done
	
	if [ -z "$image_name" ] && [ -n "$1" ]; then
		image_name="$1"
		shift
	fi

	# [ -z "$image_name" ] && >&2 echo "error: image name not specified" && return 1
	[ -z "$image_name" ] && >&2 echo "warning: image name not specified, will skip build phase" && skip_build=1

	[ $skip_build -eq 1 ] && cleanup=0

	[ $purge_cache -eq 1 ] && [ -d "$cache_directory" ] && rm -rf "$cache_directory/*"
	[ $no_cache -eq 0 ] && [ ! -d "$cache_directory" ] && mkdir -p "$cache_directory"

	local output_directory_exists=0

	if [ -z "$output_directory" ]; then
		cleanup=1
		output_directory="$(mktemp -d)"
	else
		[ -d "$output_directory" ] && output_directory_exists=1 || mkdir -p "$output_directory"
	fi

	[ $output_directory_exists -eq 1 ] && [ $clean -eq 1 ] && >&2 echo "cleaning $output_directory" && rm -rf "$output_directory"/*

	local NVIDIA_TYPE=runtime
	[ $nvidia_devel -eq 1 ] && NVIDIA_TYPE=devel

	# base on either plain ubuntu or one of the NVIDIA CUDA images
	if [ -n "$nvidia_cuda" ]; then
		# base_image="nvidia/cudagl:$nvidia_cuda-runtime"	# NVIDIA CUDA with OpenGL libraries (glvnd)
		if [ -n "$nvidia_cudnn" ]; then
			base_image="nvidia/cuda:$nvidia_cuda-cudnn$nvidia_cudnn-$NVIDIA_TYPE-ubuntu16.04"
		else
			base_image="nvidia/cuda:$nvidia_cuda-$NVIDIA_TYPE-ubuntu16.04"
		fi
	else
		# use plain ubuntu
		base_image="ubuntu:16.04"
	fi

	local tmp_directory_exists=0

	if [ $no_cache -eq 1 ]; then
		# no-cache: use tmp directory as cache directory
		[ -n "$tmp_directory" ] && [ -d "$tmp_directory" ] && tmp_directory_exists=1
		[ -z "$tmp_directory" ] && tmp_directory="$(mktemp -d)"
		[ -n "$tmp_directory" ] && [ ! -d "$tmp_directory" ] && mkdir -p "$tmp_directory"
		cache_directory="$tmp_directory"
	fi

	local output_dockerfile="$output_directory/Dockerfile$suffix"

	# define some url variables for convenience
	# prepare dockerfiles
	local ros_dockerfile_base_url="https://raw.githubusercontent.com/osrf/docker_images/master/ros/kinetic/ubuntu/xenial"
	local ros_core_url="$ros_dockerfile_base_url/ros-core"
	local ros_base_url="$ros_dockerfile_base_url/ros-base"
	local ros_core_dockerfile="$cache_directory/Dockerfile-ros-core"
	local ros_base_dockerfile="$cache_directory/Dockerfile-ros-base"

	[ ! -f "$ros_core_dockerfile" ] && curl -sL "$ros_core_url/Dockerfile" -o "$ros_core_dockerfile" && add_vim_modeline "$ros_core_dockerfile"
	# [ ! -f "$ros_base_dockerfile" ] && curl -sL "$ros_base_url/Dockerfile" -o "$ros_base_dockerfile" && add_vim_modeline "$ros_base_dockerfile"

	# == prepare resource files

	local f

	# ros_entrypoint.sh for ros-core image
	f="$cache_directory/ros_entrypoint.sh"
	[ ! -f "$f" ] && curl -sL "$ros_core_url/ros_entrypoint.sh" -o "$f" && chmod +x "$f"
	cp "$f" "$output_directory/"

	# copy nn agent project files
	local agent_project_directory="$base_path"
	for src in nn_agent; do
		cp -r "$agent_project_directory"/$src "$output_directory/"
	done

	# copy other files at base_path
	for src in project.launch apple_dbaby.world turtlebot3_burger.gazebo.xacro entrypoint.sh xorg.conf.nvidia-headless lightop__init__.py; do
		cp "$base_path/files/$src" "$output_directory/"
	done

	if [ $vnc_desktop -eq 1 ]; then
		if [ ! -d "$cache_directory/docker-ubuntu-vnc-desktop" ]; then
			$(cd "$cache_directory" ; git clone https://github.com/ct2034/docker-ubuntu-vnc-desktop.git --depth=1)
		# else
		# 	$(cd "$cache_directory/docker-ubuntu-vnc-desktop"; git pull)
		fi

		for src in "$cache_directory"/docker-ubuntu-vnc-desktop/*; do
			[ ! -d "$src" ] && continue
			cp -r "$src" "$output_directory/"
		done
	fi

	# == create Dockerfile

	echo "# This file is autogenerated at $(date +'%Y-%m-%d %H:%M')" > "$output_dockerfile"
	echo >> "$output_dockerfile"
	add_vim_modeline "$output_dockerfile"
	echo >> "$output_dockerfile"

	# using multi-stage builds
	# https://hub.docker.com/r/nvidia/opengl/
	# https://gitlab.com/nvidia/opengl/blob/ubuntu16.04/1.0-glvnd/runtime/Dockerfile
	# if cudagl used this is not needed
	if [ $nvidia_opengl -eq 1 ]; then
		echo "FROM nvidia/opengl:$NVIDIA_TYPE as glvnd" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
	fi

	update_dockerfile --multi-stage "$output_dockerfile" --image "$base_image"
	update_dockerfile "$output_dockerfile" "$ros_core_dockerfile"
	# update_dockerfile "$output_dockerfile" "$ros_base_dockerfile"
	if [ $vnc_desktop -eq 1 ]; then
		echo "RUN rm -r /etc/ros/rosdep/sources.list.d/20-default.list" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
		update_dockerfile "$output_dockerfile" "$cache_directory/docker-ubuntu-vnc-desktop/Dockerfile"
		echo "COPY lightop__init__.py /usr/lib/web/lightop/__init__.py" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
		echo "RUN rm /etc/apt/sources.list.d/arc-theme.list*" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
		echo "ENV VNC_DESKTOP 1" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
		echo "RUN apt-get update && apt-get install -y xserver-xorg-core" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
		if [ $nvidia_opengl -eq 1 ]; then
			# disable Xvfb
			sed -i 's#^command=/usr/bin/Xvfb.*$#command=/bin/true#' \
				"$output_directory/image/etc/supervisor/conf.d/supervisord.conf"
		else
			# allow up to UHD resolution for Xvfb
			sed -i 's#^command=/usr/bin/Xvfb.*$#command=/usr/bin/Xvfb :1 -screen 0 3840x2160x16#' \
				"$output_directory/image/etc/supervisor/conf.d/supervisord.conf"
		fi
	fi
	update_dockerfile "$output_dockerfile" "$base_path/dockerfiles/Dockerfile-gazebo"
	update_dockerfile "$output_dockerfile" "$base_path/dockerfiles/Dockerfile-pytorch"
	
	if [ $nvidia_opengl -eq 1 ]; then
		update_dockerfile "$output_dockerfile" "$base_path/dockerfiles/Dockerfile-nvidia-headless"

		echo "COPY --from=glvnd /usr/local/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu" >> "$output_dockerfile"
		echo "COPY --from=glvnd /usr/local/lib/i386-linux-gnu /usr/lib/i386-linux-gnu" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
		echo "ENV NVIDIA_OPENGL true" >> "$output_dockerfile"
		echo >> "$output_dockerfile"
	fi

	update_dockerfile "$output_dockerfile" "$base_path/dockerfiles/Dockerfile-apple"
	update_dockerfile "$output_dockerfile" "$base_path/dockerfiles/Dockerfile-agent"

	# restore vnc-desktop entrypoint overwritten by gazebo dockerfile
	# [ $vnc_desktop -eq 1 ] && echo 'ENTRYPOINT ["/startup.sh"]' >> "$output_dockerfile" && echo >> "$output_dockerfile"
	[ $vnc_desktop -eq 1 ] && echo 'CMD []' >> "$output_dockerfile" && echo >> "$output_dockerfile"

	if [ $vnc_desktop -eq 1 ]; then
		echo >> "$output_dockerfile"
		echo "# copy turtlebot3 models" >> "$output_dockerfile"
		echo "RUN mkdir -p /root/.gazebo/models" >> "$output_dockerfile"
		echo "RUN cp -rv /root/apple_picking_robot/ros/src/turtlebot3_gazebo/models/* /root/.gazebo/models" >> "$output_dockerfile"
	fi

	# cleanup
	if [ -n "$tmp_directory" ] && [ -d "$tmp_directory" ] && [ $tmp_directory_exists -eq 0 ]; then
		rm -rf "$tmp_directory"
	fi

	if [ $skip_build -eq 0 ]; then
		docker build -t "$image_name" "$output_directory"
		r=$?
		if [ $r -eq 0 ] && [ $cleanup -eq 1 ]; then
			[ $output_directory_exists -eq 1 ] && rm -rf "$output_directory/*" || rm -rf "$output_directory"
		fi
		return $r
	else
		echo "docker image build directory: $output_directory"
		echo
		echo "to build execute:"
		[ -z "$image_name" ] && image_name="apple_picker"
		echo "$ docker build -t $image_name $output_directory"
		echo
		return 0
	fi
}

if [ "$BASH_SOURCE" = "$0" ]; then
	build_image "$@"
fi
