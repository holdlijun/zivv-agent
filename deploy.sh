#!/bin/bash

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="ghcr.io/holdlijun/zivv-agent:latest"

echo "🚀 Starting deployment for zivv-agent..."

cd "$PROJECT_DIR"

# Ensure .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Please create it before starting."
    exit 1
fi

# Pull latest image
echo "📡 Pulling latest image: $IMAGE_NAME"
docker compose pull

# Restart container
echo "🔄 Restarting containers..."
docker compose up -d

# Cleanup old images
echo "🧹 Cleaning up old images..."
docker image prune -f

echo "✅ Deployment completed successfully!"
