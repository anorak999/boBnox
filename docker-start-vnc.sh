#!/bin/bash
# Start VNC server and boBnox GUI

# Start Xvfb (virtual framebuffer)
Xvfb :99 -screen 0 ${RESOLUTION}x24 &
sleep 2

# Start window manager
fluxbox &
sleep 1

# Start VNC server
x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -forever -shared &
sleep 2

# Start noVNC (web-based VNC client)
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &
sleep 2

# Start boBnox GUI
cd /app
python bobnox.py

# Keep container running if app closes
tail -f /dev/null
