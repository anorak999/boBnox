#!/bin/bash
# Run boBnox GUI in Docker with X11 forwarding

IMAGE_NAME="bobnox-gui:latest"

# Build the image if it doesn't exist
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
    echo "Building Docker image..."
    docker build -f Dockerfile.gui -t $IMAGE_NAME .
fi

echo "Starting boBnox GUI..."
echo "Close the application window to stop the container."

# Allow X server connections from Docker
xhost +local:docker

# Run the container with X11 forwarding
docker run --rm \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v $HOME:$HOME \
    --name bobnox-gui \
    $IMAGE_NAME

# Revoke X server access after container stops
xhost -local:docker

echo "boBnox GUI stopped."
