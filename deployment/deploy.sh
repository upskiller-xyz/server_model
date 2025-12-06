#!/bin/bash
set -e

# Obstruction Server - VM Deployment Script
# This script automates the deployment of the Obstruction Server on a Linux VM
# Usage: sudo bash deploy.sh [options]
#
# Options:
#   --skip-nginx        Skip nginx installation and configuration
#   --skip-ssl          Skip SSL certificate setup
#   --domain DOMAIN     Set the domain name for nginx configuration
#   --port PORT         Set the application port (default: 8081)
#   --debug             Enable debug logging (verbose output)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
SKIP_NGINX=false
SKIP_SSL=true
DOMAIN=""
APP_PORT=8081
DEBUG_MODE=false
INSTALL_DIR="/opt/obstruction-server"
SERVICE_USER="obstruction"
SERVICE_NAME="obstruction-server"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-nginx)
            SKIP_NGINX=true
            shift
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --port)
            APP_PORT="$2"
            shift 2
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
echo -e "${GREEN}Obstruction Server Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

echo -e "${YELLOW}[1/10] Checking system requirements...${NC}"
# Check if Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    echo -e "${RED}Error: This script is designed for Ubuntu/Debian systems${NC}"
    exit 1
fi

# Update system packages
echo -e "${YELLOW}[2/10] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

# Install base system packages
echo -e "${YELLOW}[3/10] Installing base system packages...${NC}"
apt-get install -y \
    software-properties-common \
    python3-pip \
    git \
    build-essential \
    curl \
    wget

# Detect and install appropriate Python version
echo -e "${YELLOW}[4/10] Detecting and installing Python...${NC}"
PYTHON_CMD=""

# Check for Python 3.13, 3.12, or 3.11
if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
    echo -e "${GREEN}Found Python 3.13${NC}"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    echo -e "${GREEN}Found Python 3.12${NC}"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo -e "${GREEN}Found Python 3.11${NC}"
else
    # Try to install from deadsnakes PPA
    echo -e "${YELLOW}No suitable Python version found. Adding deadsnakes PPA...${NC}"
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update

    # Try to install Python 3.13
    if apt-cache show python3.13 &> /dev/null; then
        apt-get install -y python3.13 python3.13-venv python3.13-dev
        PYTHON_CMD="python3.13"
        echo -e "${GREEN}Installed Python 3.13${NC}"
    elif apt-cache show python3.12 &> /dev/null; then
        apt-get install -y python3.12 python3.12-venv python3.12-dev
        PYTHON_CMD="python3.12"
        echo -e "${GREEN}Installed Python 3.12${NC}"
    elif apt-cache show python3.11 &> /dev/null; then
        apt-get install -y python3.11 python3.11-venv python3.11-dev
        PYTHON_CMD="python3.11"
        echo -e "${GREEN}Installed Python 3.11${NC}"
    else
        echo -e "${RED}Error: Unable to install Python 3.11 or higher${NC}"
        exit 1
    fi
fi

# Ensure venv module is installed
PYTHON_VERSION_SHORT=$(echo $PYTHON_CMD | grep -oP '\d+\.\d+')
if ! apt-cache show ${PYTHON_CMD}-venv &> /dev/null; then
    echo -e "${YELLOW}Installing ${PYTHON_CMD}-venv...${NC}"
    apt-get install -y ${PYTHON_CMD}-venv ${PYTHON_CMD}-dev || true
fi

echo -e "${GREEN}Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))${NC}"

# Create service user
echo -e "${YELLOW}[5/10] Creating service user...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -m -d "$INSTALL_DIR" "$SERVICE_USER"
    echo -e "${GREEN}Created user: $SERVICE_USER${NC}"
else
    echo -e "${GREEN}User $SERVICE_USER already exists${NC}"
fi

# Clone or update repository
echo -e "${YELLOW}[6/10] Setting up application directory...${NC}"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}Repository exists, pulling latest changes...${NC}"
    cd "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" git pull
else
    echo -e "${YELLOW}Cloning repository...${NC}"
    rm -rf "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" git clone https://github.com/upskiller-xyz/server_obstruction.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment
echo -e "${YELLOW}[7/10] Creating Python virtual environment...${NC}"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    sudo -u "$SERVICE_USER" $PYTHON_CMD -m venv "$INSTALL_DIR/venv"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# Install Python dependencies
echo -e "${YELLOW}[8/10] Installing Python dependencies...${NC}"
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Create environment file
echo -e "${YELLOW}[9/10] Configuring environment...${NC}"
if [ ! -f "$INSTALL_DIR/.env" ]; then
    if [ "$DEBUG_MODE" = true ]; then
        echo -e "${YELLOW}Configuring DEBUG mode environment${NC}"
        cp "$INSTALL_DIR/deployment/.env.production.debug" "$INSTALL_DIR/.env"
    else
        echo -e "${YELLOW}Configuring PRODUCTION mode environment${NC}"
        cp "$INSTALL_DIR/deployment/.env.production" "$INSTALL_DIR/.env"
    fi

    # Update port in .env file
    sed -i "s/PORT=8081/PORT=$APP_PORT/g" "$INSTALL_DIR/.env"

    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
    echo -e "${GREEN}Created environment file${NC}"
else
    echo -e "${GREEN}Environment file already exists${NC}"
    if [ "$DEBUG_MODE" = true ]; then
        echo -e "${YELLOW}Warning: Debug mode requested but .env already exists${NC}"
        echo -e "${YELLOW}To enable debug mode, remove .env and re-run with --debug${NC}"
    fi
fi

# Create log directory
mkdir -p /var/log/obstruction-server
chown "$SERVICE_USER:$SERVICE_USER" /var/log/obstruction-server

# Install systemd service
echo -e "${YELLOW}[10/10] Installing systemd service...${NC}"
cp "$INSTALL_DIR/deployment/obstruction-server.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"

# Start the service
echo -e "${YELLOW}Starting the service...${NC}"
systemctl restart "$SERVICE_NAME.service"
sleep 3

# Check service status
if systemctl is-active --quiet "$SERVICE_NAME.service"; then
    echo -e "${GREEN}✓ Service is running successfully${NC}"
else
    echo -e "${RED}✗ Service failed to start. Check logs: journalctl -u $SERVICE_NAME -n 50${NC}"
    exit 1
fi

# Install and configure nginx (optional)
if [ "$SKIP_NGINX" = false ]; then
    echo -e "${YELLOW}[11/11] Installing and configuring nginx...${NC}"
    apt-get install -y nginx

    # Configure nginx
    if [ -n "$DOMAIN" ]; then
        sed "s/your-domain.com/$DOMAIN/g" "$INSTALL_DIR/deployment/nginx-obstruction-server.conf" > /etc/nginx/sites-available/obstruction-server
    else
        cp "$INSTALL_DIR/deployment/nginx-obstruction-server.conf" /etc/nginx/sites-available/obstruction-server
    fi

    # Enable site
    ln -sf /etc/nginx/sites-available/obstruction-server /etc/nginx/sites-enabled/obstruction-server

    # Test nginx configuration
    if nginx -t; then
        systemctl restart nginx
        systemctl enable nginx
        echo -e "${GREEN}✓ Nginx configured and running${NC}"
    else
        echo -e "${RED}✗ Nginx configuration test failed${NC}"
    fi

    # Setup SSL with Let's Encrypt (optional)
    if [ "$SKIP_SSL" = false ] && [ -n "$DOMAIN" ]; then
        echo -e "${YELLOW}Setting up SSL certificate...${NC}"
        apt-get install -y certbot python3-certbot-nginx
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email
        echo -e "${GREEN}✓ SSL certificate installed${NC}"
    fi
else
    echo -e "${YELLOW}[11/11] Skipping nginx installation${NC}"
fi

# Print deployment summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Application Directory: ${GREEN}$INSTALL_DIR${NC}"
echo -e "Service Name: ${GREEN}$SERVICE_NAME${NC}"
echo -e "Service User: ${GREEN}$SERVICE_USER${NC}"
echo -e "Application Port: ${GREEN}$APP_PORT${NC}"
echo -e "Log Directory: ${GREEN}/var/log/obstruction-server${NC}"
if [ "$DEBUG_MODE" = true ]; then
    echo -e "Debug Mode: ${YELLOW}ENABLED${NC}"
    echo -e "  ${YELLOW}⚠ Debug mode provides verbose logging for troubleshooting${NC}"
    echo -e "  ${YELLOW}⚠ Not recommended for production use${NC}"
else
    echo -e "Debug Mode: ${GREEN}DISABLED${NC} (production mode)"
fi
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  View service status:  ${GREEN}systemctl status $SERVICE_NAME${NC}"
echo -e "  View service logs:    ${GREEN}journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  Restart service:      ${GREEN}systemctl restart $SERVICE_NAME${NC}"
echo -e "  Stop service:         ${GREEN}systemctl stop $SERVICE_NAME${NC}"
echo ""
echo -e "${YELLOW}Test the API:${NC}"
echo -e "  ${GREEN}curl http://localhost:$APP_PORT/${NC}"
echo ""
if [ "$SKIP_NGINX" = false ] && [ -n "$DOMAIN" ]; then
    echo -e "Public URL: ${GREEN}http://$DOMAIN${NC}"
    echo ""
fi
echo -e "${GREEN}Deployment successful!${NC}"
