# Docker Image Test Guide

## Step 1: Build the Image

```bash
cd /home/anorak/Works/bobnox
docker build -t bobnox:test .
```

Expected output: Multiple steps completing successfully, ending with "Successfully tagged bobnox:test"

## Step 2: Create Test Data

```bash
# Create a test folder
mkdir -p /tmp/test-organize

# Add some test files
touch /tmp/test-organize/document.pdf
touch /tmp/test-organize/photo.jpg
touch /tmp/test-organize/song.mp3
touch /tmp/test-organize/video.mp4
touch /tmp/test-organize/script.py
touch /tmp/test-organize/notes.txt

# List files before organizing
ls -la /tmp/test-organize/
```

## Step 3: Run the Container

```bash
docker run --rm -v /tmp/test-organize:/data bobnox:test --path /data
```

**Explanation:**
- `--rm`: Remove container after it exits
- `-v /tmp/test-organize:/data`: Mount host folder into container at /data
- `bobnox:test`: The image name and tag
- `--path /data`: Tell the CLI to organize files in /data

Expected output:
```
Moving (1/6): document.pdf -> Documents
Moving (2/6): photo.jpg -> Images
Moving (3/6): song.mp3 -> Audio
...
Log saved to: /data/bobnox-log-20251104-HHMMSS.txt
```

## Step 4: Verify Results

```bash
# Check organized structure
tree /tmp/test-organize/

# Should show:
# /tmp/test-organize/
# ├── Audio/
# │   └── song.mp3
# ├── Documents/
# │   └── document.pdf
# ├── Images/
# │   └── photo.jpg
# ├── Scripts/
# │   └── script.py
# ├── Text Documents/
# │   └── notes.txt
# ├── Videos/
# │   └── video.mp4
# └── bobnox-log-20251104-HHMMSS.txt

# Check the log file
cat /tmp/test-organize/bobnox-log-*.txt
```

## Step 5: Test with Your Own Folder

```bash
# Test with your actual Downloads folder (be careful!)
docker run --rm -v ~/Downloads:/data bobnox:test --path /data
```

## Troubleshooting

**Image not found?**
```bash
docker images | grep bobnox
```

**Build failed?**
```bash
# Check build logs
docker build -t bobnox:test . 2>&1 | tee build.log
```

**Permission issues?**
```bash
# Run with user privileges
docker run --rm --user $(id -u):$(id -g) -v /tmp/test-organize:/data bobnox:test --path /data
```

**Container exits immediately?**
```bash
# Check what's wrong
docker run --rm -v /tmp/test-organize:/data bobnox:test --path /data; echo "Exit code: $?"
```

## Clean Up Test Data

```bash
rm -rf /tmp/test-organize
```

## Tag and Push to GHCR (when ready)

```bash
# Tag for GitHub Container Registry
docker tag bobnox:test ghcr.io/anorak999/bobnox:latest

# Login to GHCR
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u anorak999 --password-stdin

# Push
docker push ghcr.io/anorak999/bobnox:latest
```
