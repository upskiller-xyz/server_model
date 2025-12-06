#!/bin/bash
set -e

# ONNX Model Server - Docker Deployment Script
# Usage: sudo bash deploy-docker.sh [options]
#
# Options:
#   --with-nginx        Deploy with nginx reverse proxy
#   --port PORT         Set the host port (default: 8083)
#   --model MODEL       Set the model name (default: df_default_2.0.1)
#   --build             Force rebuild the Docker image
#   --debug             Enable debug logging (verbose output)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
WITH_NGINX=false
HOST_PORT=8083
MODEL_NAME="df_default_2.0.1"
FORCE_BUILD=false
DEBUG_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-nginx)
            WITH_NGINX=true
            shift
            ;;
        --port)
            HOST_PORT="$2"
            shift 2
            ;;
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --build)
            FORCE_BUILD=true
            shift
            ;;
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ONNX Model Server - Docker Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo -e "${YELLOW}Installing Docker...${NC}"

    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    # Add current user to docker group
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
        echo -e "${GREEN}Added $SUDO_USER to docker group${NC}"
    fi

    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}✓ Docker installed successfully${NC}"
else
    echo -e "${GREEN}✓ Docker is already installed${NC}"
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Installing Docker Compose...${NC}"

    # Install Docker Compose plugin
    apt-get update
    apt-get install -y docker-compose-plugin

    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose is already installed${NC}"
fi

# Determine Docker Compose command
if command -v docker compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Navigate to deployment directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Update port in docker-compose.yml
echo -e "${YELLOW}Configuring port mapping: $HOST_PORT:8083${NC}"
sed -i.bak "s/\"[0-9]*:8083\"/\"$HOST_PORT:8083\"/g" docker-compose.yml

# Configure environment file based on debug mode
if [ "$DEBUG_MODE" = true ]; then
    echo -e "${YELLOW}Configuring DEBUG mode environment${NC}"
    if [ -f .env.docker.debug ]; then
        cp .env.docker.debug .env.docker
    else
        cat > .env.docker << EOF
# Docker Environment Configuration - DEBUG MODE
PORT=8083
MODEL=$MODEL_NAME
PYTHONUNBUFFERED=1
PYTHONPATH=/app
LOG_LEVEL=DEBUG
EOF
    fi
else
    if [ ! -f .env.docker ]; then
        echo -e "${YELLOW}Configuring PRODUCTION mode environment${NC}"
        cat > .env.docker << EOF
# Docker Environment Configuration
PORT=8083
MODEL=$MODEL_NAME
PYTHONUNBUFFERED=1
PYTHONPATH=/app
EOF
    fi
fi

# Create logs directory
mkdir -p logs

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
$DOCKER_COMPOSE down --remove-orphans 2>/dev/null || true

# Build and start containers
if [ "$FORCE_BUILD" = true ]; then
    echo -e "${YELLOW}Building Docker image (forced rebuild)...${NC}"
    $DOCKER_COMPOSE build --no-cache
else
    echo -e "${YELLOW}Building Docker image...${NC}"
    $DOCKER_COMPOSE build
fi

# Start services
if [ "$WITH_NGINX" = true ]; then
    echo -e "${YELLOW}Starting services with nginx...${NC}"
    $DOCKER_COMPOSE --profile with-nginx up -d
else
    echo -e "${YELLOW}Starting services...${NC}"
    $DOCKER_COMPOSE up -d server-model
fi

# Wait for service to be ready
echo -e "${YELLOW}Waiting for service to start...${NC}"
sleep 5

# Check if service is running
if docker ps | grep -q server-model; then
    echo -e "${GREEN}✓ Service is running${NC}"

    # Test health check
    echo -e "${YELLOW}Testing health check...${NC}"
    sleep 3

    if curl -s http://localhost:$HOST_PORT/ > /dev/null; then
        echo -e "${GREEN}✓ Health check passed${NC}"
    else
        echo -e "${RED}✗ Health check failed${NC}"
        echo -e "${YELLOW}Check logs: docker logs server-model${NC}"
    fi
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo -e "${YELLOW}Check logs: docker logs server-model${NC}"
    exit 1
fi

# Print summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Container: ${GREEN}server-model${NC}"
echo -e "Host Port: ${GREEN}$HOST_PORT${NC}"
echo -e "Container Port: ${GREEN}8083${NC}"
echo -e "Model: ${GREEN}$MODEL_NAME${NC}"
if [ "$WITH_NGINX" = true ]; then
    echo -e "Nginx: ${GREEN}enabled (ports 80, 443)${NC}"
fi
if [ "$DEBUG_MODE" = true ]; then
    echo -e "Debug Mode: ${YELLOW}ENABLED${NC}"
    echo -e "  ${YELLOW}⚠ Debug mode provides verbose logging for troubleshooting${NC}"
    echo -e "  ${YELLOW}⚠ Not recommended for production use${NC}"
else
    echo -e "Debug Mode: ${GREEN}DISABLED${NC} (production mode)"
fi
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  View logs:           ${GREEN}docker logs -f server-model${NC}"
echo -e "  Stop service:        ${GREEN}$DOCKER_COMPOSE down${NC}"
echo -e "  Restart service:     ${GREEN}$DOCKER_COMPOSE restart${NC}"
echo -e "  View containers:     ${GREEN}docker ps${NC}"
echo -e "  Execute in container: ${GREEN}docker exec -it server-model sh${NC}"
echo ""
echo -e "${YELLOW}Test the API:${NC}"
echo -e "  ${GREEN}curl http://localhost:$HOST_PORT/${NC}"
echo ""
echo -e "${GREEN}Deployment successful!${NC}"
