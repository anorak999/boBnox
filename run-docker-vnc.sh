#!/bin/bash
# Build and run boBnox in Docker with web-based GUI access

IMAGE_NAME="bobnox-vnc:latest"
CONTAINER_NAME="bobnox-vnc"

# Stop existing container if running
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Build the image
echo "Building Docker image with VNC support..."
docker build -f Dockerfile.vnc -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

# Run the container
echo "Starting boBnox in Docker..."
echo ""
echo "Access the GUI in your browser:"
echo "  👉 http://localhost:6080/vnc.html"
echo ""
echo "Press Ctrl+C to stop the container"
echo ""

docker run --rm \
    -p 6080:6080 \
    -v $HOME:$HOME \
    --name $CONTAINER_NAME \
    $IMAGE_NAME
