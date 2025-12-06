# Virtual Machine Deployment Guide

This guide provides comprehensive instructions for deploying the Obstruction Server on a Linux virtual machine (VM).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start (Automated Deployment)](#quick-start-automated-deployment)
- [Manual Deployment](#manual-deployment)
- [Configuration](#configuration)
- [Service Management](#service-management)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
- [Security Considerations](#security-considerations)
- [Updating the Application](#updating-the-application)
- [Backup and Recovery](#backup-and-recovery)

---

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or later (or Debian 11+)
- **Python**: Python 3.11 or higher (3.13 recommended)
- **RAM**: Minimum 2GB, recommended 4GB or more
- **Disk Space**: At least 5GB free space
- **CPU**: 2+ cores recommended for production use
- **Network**: Open port 80 (HTTP) and optionally 443 (HTTPS)

### Access Requirements

- Root or sudo access to the VM
- SSH access to the VM
- Basic knowledge of Linux command line
- (Optional) Domain name pointed to your VM's IP address

---

## Quick Start (Automated Deployment)

The automated deployment script handles all installation and configuration steps.

### Step 1: Connect to Your VM

```bash
ssh user@your-vm-ip
```

### Step 2: Download Deployment Files

```bash
# Clone the repository
git clone https://github.com/upskiller-xyz/server_obstruction.git
cd server_obstruction/deployment
```

### Step 3: Run Deployment Script

```bash
# Basic deployment (HTTP only, no nginx)
sudo bash deploy.sh --skip-nginx

# Full deployment with nginx
sudo bash deploy.sh

# Full deployment with custom domain and SSL
sudo bash deploy.sh --domain your-domain.com

# Custom port
sudo bash deploy.sh --port 8082
```

### Step 4: Verify Deployment

```bash
# Check service status
systemctl status obstruction-server

# Test the API
curl http://localhost:8081/
```

Expected response:
```json
{
  "status": "ready",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

---

## Manual Deployment

If you prefer manual deployment or need to customize the process, follow these steps.

### Step 1: Update System and Install Dependencies

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y \
    python3.13 \
    python3.13-venv \
    python3-pip \
    git \
    build-essential \
    nginx \
    curl \
    wget
```

If Python 3.13 is not available:
```bash
# Add deadsnakes PPA for newer Python versions
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv
```

### Step 2: Create Service User

```bash
# Create dedicated user for the service
sudo useradd -r -s /bin/bash -m -d /opt/obstruction-server obstruction
```

### Step 3: Clone Repository

```bash
# Clone as the service user
sudo -u obstruction git clone https://github.com/upskiller-xyz/server_obstruction.git /opt/obstruction-server
cd /opt/obstruction-server
```

### Step 4: Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
sudo -u obstruction python3.13 -m venv /opt/obstruction-server/venv

# Install dependencies
sudo -u obstruction /opt/obstruction-server/venv/bin/pip install --upgrade pip
sudo -u obstruction /opt/obstruction-server/venv/bin/pip install -r /opt/obstruction-server/requirements.txt
```

### Step 5: Configure Environment

```bash
# Copy and edit environment file
sudo cp /opt/obstruction-server/deployment/.env.production /opt/obstruction-server/.env
sudo nano /opt/obstruction-server/.env

# Set ownership
sudo chown obstruction:obstruction /opt/obstruction-server/.env
```

### Step 6: Create Log Directory

```bash
sudo mkdir -p /var/log/obstruction-server
sudo chown obstruction:obstruction /var/log/obstruction-server
```

### Step 7: Install Systemd Service

```bash
# Copy service file
sudo cp /opt/obstruction-server/deployment/obstruction-server.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable obstruction-server
sudo systemctl start obstruction-server

# Check status
sudo systemctl status obstruction-server
```

### Step 8: Configure Nginx (Optional but Recommended)

```bash
# Copy nginx configuration
sudo cp /opt/obstruction-server/deployment/nginx-obstruction-server.conf /etc/nginx/sites-available/obstruction-server

# Edit configuration (replace your-domain.com with your actual domain or IP)
sudo nano /etc/nginx/sites-available/obstruction-server

# Enable site
sudo ln -s /etc/nginx/sites-available/obstruction-server /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 9: Setup SSL Certificate (Optional)

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate (replace your-domain.com with your actual domain)
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure nginx for HTTPS
```

---

## Configuration

### Environment Variables

Edit `/opt/obstruction-server/.env` to configure the application:

```bash
# Application port (internal)
PORT=8081

# Flask environment
FLASK_ENV=production
FLASK_DEBUG=False

# Gunicorn workers
WORKERS=4          # Typically 2-4 x number of CPU cores
THREADS=8          # Threads per worker
TIMEOUT=900        # Request timeout in seconds

# System configuration
CUDA_VISIBLE_DEVICES=-1              # Disable GPU
TF_CPP_MIN_LOG_LEVEL=3              # Reduce TensorFlow logging
OPENCV_IO_ENABLE_OPENEXR=0          # Disable OpenEXR
OMP_NUM_THREADS=1                    # OpenMP threads
```

### Systemd Service Configuration

Edit `/etc/systemd/system/obstruction-server.service` to modify service settings:

```ini
[Service]
# Change number of workers
ExecStart=/opt/obstruction-server/venv/bin/gunicorn \
    --workers 4 \
    --threads 8 \
    ...

# Modify restart policy
Restart=always
RestartSec=10s

# Adjust resource limits
LimitNOFILE=65536
LimitNPROC=4096
```

After editing, reload the service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart obstruction-server
```

### Nginx Configuration

Edit `/etc/nginx/sites-available/obstruction-server`:

- Change `server_name` to your domain or IP
- Adjust `client_max_body_size` for larger mesh uploads
- Modify timeout values for longer calculations
- Enable/disable SSL configuration

After editing:
```bash
sudo nginx -t                    # Test configuration
sudo systemctl reload nginx      # Apply changes
```

---

## Service Management

### Common Commands

```bash
# Start the service
sudo systemctl start obstruction-server

# Stop the service
sudo systemctl stop obstruction-server

# Restart the service
sudo systemctl restart obstruction-server

# Check service status
sudo systemctl status obstruction-server

# Enable service to start on boot
sudo systemctl enable obstruction-server

# Disable service from starting on boot
sudo systemctl disable obstruction-server

# View service logs
sudo journalctl -u obstruction-server -f

# View last 50 log entries
sudo journalctl -u obstruction-server -n 50

# View logs since today
sudo journalctl -u obstruction-server --since today
```

### Nginx Commands

```bash
# Start nginx
sudo systemctl start nginx

# Stop nginx
sudo systemctl stop nginx

# Restart nginx
sudo systemctl restart nginx

# Reload nginx configuration (no downtime)
sudo systemctl reload nginx

# Test nginx configuration
sudo nginx -t

# View nginx access logs
sudo tail -f /var/log/nginx/obstruction-server-access.log

# View nginx error logs
sudo tail -f /var/log/nginx/obstruction-server-error.log
```

---

## Monitoring and Troubleshooting

### Health Check

```bash
# Check if service is responding
curl http://localhost:8081/

# Expected response:
# {"status": "ready", "timestamp": "2025-01-01T00:00:00Z"}
```

### Test API Endpoint

```bash
# Test obstruction calculation
curl -X POST http://localhost:8081/obstruction \
  -H "Content-Type: application/json" \
  -d '{
    "x": 0.0,
    "y": 3.0,
    "z": 0.0,
    "direction_angle": 0.0,
    "mesh": [
        [10.0, 0.0, -5.0],
        [10.0, 5.0, -5.0],
        [10.0, 0.0, 5.0]
    ]
  }'
```

### Common Issues

#### Service Won't Start

```bash
# Check detailed logs
sudo journalctl -u obstruction-server -n 100

# Common causes:
# 1. Port already in use
sudo lsof -i :8081

# 2. Permission issues
sudo chown -R obstruction:obstruction /opt/obstruction-server

# 3. Missing dependencies
sudo -u obstruction /opt/obstruction-server/venv/bin/pip install -r /opt/obstruction-server/requirements.txt

# 4. Python version mismatch
/opt/obstruction-server/venv/bin/python --version
```

#### High Memory Usage

```bash
# Check memory usage
free -h
top -p $(pgrep -f gunicorn)

# Reduce number of workers in .env or service file
# WORKERS=2 (instead of 4)
```

#### Slow Response Times

```bash
# Check worker/thread configuration
# Increase workers or threads in .env

# Check system resources
htop
df -h

# Check nginx timeout settings
# Increase timeout in nginx configuration
```

#### Can't Access from Outside

```bash
# Check firewall settings
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check nginx is running
sudo systemctl status nginx

# Check DNS resolution (if using domain)
nslookup your-domain.com

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Performance Monitoring

```bash
# Monitor system resources
htop

# Monitor disk usage
df -h

# Monitor network connections
sudo netstat -tlnp | grep 8081

# Monitor application logs for errors
sudo journalctl -u obstruction-server -p err -f

# Check gunicorn worker status
ps aux | grep gunicorn
```

---

## Security Considerations

### Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH (important - don't lock yourself out!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check firewall status
sudo ufw status
```

### SSL/TLS Certificate

Always use HTTPS in production:

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured by default
# Test renewal
sudo certbot renew --dry-run
```

### Security Best Practices

1. **Keep System Updated**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

2. **Use Strong Passwords**
   - Use SSH keys instead of passwords
   - Disable password authentication in SSH

3. **Limit Access**
   - Use firewall rules to restrict access
   - Consider IP whitelisting for admin access

4. **Regular Backups**
   - Backup `/opt/obstruction-server/.env`
   - Backup nginx configuration
   - Backup application data if any

5. **Monitor Logs**
   ```bash
   # Check for suspicious activity
   sudo journalctl -u obstruction-server -p warning -f
   ```

6. **Run as Non-Root User**
   - The service already runs as the `obstruction` user
   - Never run the application as root

---

## Updating the Application

### Update Process

```bash
# 1. Stop the service
sudo systemctl stop obstruction-server

# 2. Backup current version
sudo cp -r /opt/obstruction-server /opt/obstruction-server.backup

# 3. Pull latest changes
cd /opt/obstruction-server
sudo -u obstruction git pull origin main

# 4. Update dependencies
sudo -u obstruction /opt/obstruction-server/venv/bin/pip install -r requirements.txt

# 5. Restart service
sudo systemctl start obstruction-server

# 6. Verify
sudo systemctl status obstruction-server
curl http://localhost:8081/
```

### Rollback (If Needed)

```bash
# Stop service
sudo systemctl stop obstruction-server

# Restore backup
sudo rm -rf /opt/obstruction-server
sudo mv /opt/obstruction-server.backup /opt/obstruction-server

# Restart service
sudo systemctl start obstruction-server
```

### Zero-Downtime Updates (Advanced)

For production systems, consider:
1. Using a load balancer with multiple instances
2. Blue-green deployment strategy
3. Docker containers with orchestration

---

## Backup and Recovery

### What to Backup

1. **Environment Configuration**
   ```bash
   sudo cp /opt/obstruction-server/.env /backup/location/
   ```

2. **Nginx Configuration**
   ```bash
   sudo cp /etc/nginx/sites-available/obstruction-server /backup/location/
   ```

3. **SSL Certificates** (if using Let's Encrypt)
   ```bash
   sudo cp -r /etc/letsencrypt /backup/location/
   ```

4. **Application Logs** (optional)
   ```bash
   sudo tar -czf logs-backup.tar.gz /var/log/obstruction-server/
   ```

### Automated Backup Script

Create `/usr/local/bin/backup-obstruction-server.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup/obstruction-server"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR/$DATE"

# Backup configuration
cp /opt/obstruction-server/.env "$BACKUP_DIR/$DATE/"
cp /etc/nginx/sites-available/obstruction-server "$BACKUP_DIR/$DATE/"
cp /etc/systemd/system/obstruction-server.service "$BACKUP_DIR/$DATE/"

# Backup logs (last 7 days)
tar -czf "$BACKUP_DIR/$DATE/logs.tar.gz" /var/log/obstruction-server/

# Remove backups older than 30 days
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR/$DATE"
```

Schedule with cron:
```bash
sudo crontab -e

# Add this line to run daily at 2 AM
0 2 * * * /usr/local/bin/backup-obstruction-server.sh
```

### Recovery Process

```bash
# Stop service
sudo systemctl stop obstruction-server

# Restore configuration
sudo cp /backup/location/.env /opt/obstruction-server/
sudo cp /backup/location/obstruction-server /etc/nginx/sites-available/

# Restart services
sudo systemctl start obstruction-server
sudo systemctl reload nginx
```

---

## Additional Resources

- **Project Repository**: https://github.com/upskiller-xyz/server_obstruction
- **API Documentation**: See `docs/api.md` in the repository
- **Issue Tracker**: https://github.com/upskiller-xyz/server_obstruction/issues

---

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review application logs: `sudo journalctl -u obstruction-server -n 100`
3. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
4. Open an issue on GitHub with relevant logs and error messages

---

**Last Updated**: 2025-01-19
