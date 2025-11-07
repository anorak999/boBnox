#!/bin/bash
# Run boBnox GUI in Docker with Wayland/X11 support

IMAGE_NAME="bobnox-gui:latest"

# Build the image if it doesn't exist
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
    echo "Building Docker image..."
    docker build -f Dockerfile.gui -t $IMAGE_NAME .
fi

echo "Starting boBnox GUI..."
echo "Close the application window to stop the container."

# Use host network and share the entire runtime directory for Wayland
docker run --rm \
    --net=host \
    -e DISPLAY=$DISPLAY \
    -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
    -e XDG_RUNTIME_DIR=/run/user/1000 \
    -e QT_X11_NO_MITSHM=1 \
    -v /run/user/1000:/run/user/1000 \
    -v $HOME:$HOME \
    --ipc=host \
    --name bobnox-gui \
    $IMAGE_NAME

echo "boBnox GUI stopped."
