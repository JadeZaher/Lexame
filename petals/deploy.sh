#!/bin/bash

# Default values
CONFIG_DIR="./config"
CACHE_DIR="./cache"
PORT=8000

# Help message
show_help() {
    echo "Usage: ./deploy.sh [OPTIONS]"
    echo "Deploy the Petals IPFS Microservice using Podman"
    echo ""
    echo "Options:"
    echo "  -p, --port PORT       Port to expose (default: 8000)"
    echo "  -c, --config DIR      Config directory (default: ./config)"
    echo "  --cache DIR           Cache directory (default: ./cache)"
    echo "  -h, --help           Show this help message"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_DIR="$2"
            shift 2
            ;;
        --cache)
            CACHE_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Ensure directories exist
mkdir -p "$CONFIG_DIR"
mkdir -p "$CACHE_DIR"

# Build the container
echo "Building container..."
podman build -t petals-ipfs-service -f Containerfile .

# Run the container
echo "Starting service on port $PORT..."
podman run -d \
    --name petals-ipfs-service \
    -p "$PORT:8000" \
    -v "$CONFIG_DIR:/app/config:Z" \
    -v "$CACHE_DIR:/app/cache:Z" \
    --security-opt label=disable \
    petals-ipfs-service

echo "Service deployed! API available at http://localhost:$PORT"
echo "Configuration directory: $CONFIG_DIR"
echo "Cache directory: $CACHE_DIR"
