# Docker Deployment Guide

This guide explains how to deploy the Obstruction Server using Docker on a virtual machine.

## Why Docker?

Docker deployment offers several advantages:
- **Consistent environment**: Same setup across all systems
- **Easy updates**: Simply pull and restart containers
- **Isolated dependencies**: No Python version conflicts
- **Quick rollback**: Easy to revert to previous versions
- **Resource management**: Built-in CPU and memory limits

---

## Prerequisites

- VM running Ubuntu 20.04+ or Debian 11+
- Root/sudo access
- At least 2GB RAM
- 5GB free disk space

Docker will be installed automatically by the deployment script if not present.

---

## Quick Start

### Option 1: Automated Docker Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/upskiller-xyz/server_obstruction.git
cd server_obstruction/deployment

# Run Docker deployment script
sudo bash deploy-docker.sh
```

### Option 2: With Nginx Reverse Proxy

```bash
sudo bash deploy-docker.sh --with-nginx
```

### Option 3: Custom Port

```bash
sudo bash deploy-docker.sh --port 8082
```

### Option 4: Force Rebuild

```bash
sudo bash deploy-docker.sh --build
```

---

## Manual Docker Deployment

If you prefer manual deployment:

### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional, for non-root usage)
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Install Docker Compose

```bash
# Install Docker Compose plugin
sudo apt-get update
sudo apt-get install -y docker-compose-plugin
```

### Step 3: Clone Repository

```bash
git clone https://github.com/upskiller-xyz/server_obstruction.git
cd server_obstruction/deployment
```

### Step 4: Configure Environment (Optional)

```bash
# Edit environment variables if needed
nano .env.docker
```

### Step 5: Build and Start

```bash
# Build and start the service
docker compose up -d

# Or with nginx:
docker compose --profile with-nginx up -d
```

### Step 6: Verify Deployment

```bash
# Check if containers are running
docker ps

# View logs
docker logs -f obstruction-server

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

## Docker Compose Configuration

The `docker-compose.yml` file defines the service configuration:

```yaml
services:
  obstruction-server:
    build: ..
    ports:
      - "8081:8080"  # Host:Container
    restart: unless-stopped
    env_file: .env.docker
```

### Service Ports

- **Container Port**: 8080 (internal, fixed)
- **Host Port**: 8081 (external, configurable)

To change the host port, edit `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:8080"
```

### Environment Variables

Configure in `.env.docker`:
```bash
PORT=8080                      # Internal port (don't change)
FLASK_ENV=production           # Production mode
FLASK_DEBUG=False              # Disable debug
CUDA_VISIBLE_DEVICES=-1        # Disable GPU
```

---

## Container Management

### Start/Stop Services

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# Stop without removing containers
docker compose stop

# Start stopped containers
docker compose start
```

### View Logs

```bash
# Follow logs (real-time)
docker logs -f obstruction-server

# Last 100 lines
docker logs --tail 100 obstruction-server

# Logs since 1 hour ago
docker logs --since 1h obstruction-server

# Both stdout and stderr
docker compose logs -f
```

### Execute Commands in Container

```bash
# Open bash shell in container
docker exec -it obstruction-server bash

# Run a single command
docker exec obstruction-server curl http://localhost:8080/

# Check Python version
docker exec obstruction-server python --version
```

### Container Resource Usage

```bash
# View resource usage
docker stats obstruction-server

# Detailed container info
docker inspect obstruction-server
```

---

## Nginx Reverse Proxy (Optional)

### Start with Nginx

```bash
docker compose --profile with-nginx up -d
```

This starts:
- `obstruction-server` on port 8081 (internal)
- `nginx` on ports 80 and 443 (public)

### Nginx Configuration

Edit `nginx-docker.conf` to customize:
- Domain name
- SSL certificates
- Upload limits
- Timeouts

### SSL/TLS Certificates

To use SSL with the nginx container:

1. Obtain certificates (e.g., Let's Encrypt)
2. Update `docker-compose.yml`:
   ```yaml
   volumes:
     - ./ssl/cert.pem:/etc/nginx/ssl/cert.pem:ro
     - ./ssl/key.pem:/etc/nginx/ssl/key.pem:ro
   ```
3. Update `nginx-docker.conf` to use SSL
4. Restart: `docker compose --profile with-nginx restart`

---

## Updating the Application

### Update to Latest Version

```bash
# Stop containers
docker compose down

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose build --no-cache
docker compose up -d

# Verify
curl http://localhost:8081/
```

### Quick Update (No Build)

If using pre-built images:
```bash
docker compose pull
docker compose up -d
```

### Rollback to Previous Version

```bash
# Stop current containers
docker compose down

# Checkout previous version
git log  # Find the commit hash
git checkout <previous-commit-hash>

# Rebuild and start
docker compose build
docker compose up -d
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker logs obstruction-server

# Check container status
docker ps -a

# Inspect container
docker inspect obstruction-server

# Common issues:
# 1. Port already in use
sudo lsof -i :8081

# 2. Build errors - rebuild with no cache
docker compose build --no-cache
```

### Service Not Responding

```bash
# Check if container is running
docker ps | grep obstruction-server

# Check service health
docker inspect obstruction-server | grep -A 10 Health

# Test from inside container
docker exec obstruction-server curl http://localhost:8080/

# Check logs
docker logs --tail 50 obstruction-server
```

### High Memory Usage

```bash
# Check memory usage
docker stats obstruction-server

# Limit memory in docker-compose.yml:
services:
  obstruction-server:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Can't Access from Outside VM

```bash
# Check firewall
sudo ufw status
sudo ufw allow 8081/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check port binding
docker port obstruction-server

# Ensure binding to 0.0.0.0, not 127.0.0.1
```

### Container Keeps Restarting

```bash
# Check why container is restarting
docker logs --tail 100 obstruction-server

# Check last exit code
docker inspect obstruction-server | grep -A 5 State

# Disable auto-restart temporarily
docker update --restart=no obstruction-server
```

---

## Performance Tuning

### Gunicorn Workers

Adjust in `Dockerfile` or override with docker-compose:

```yaml
services:
  obstruction-server:
    command: gunicorn --bind :8080 --workers 4 --threads 8 --timeout 900 main:app
```

Rule of thumb: `workers = (2 x CPU_CORES) + 1`

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  obstruction-server:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Enable Logging to File

```yaml
services:
  obstruction-server:
    volumes:
      - ./logs:/var/log/obstruction-server
```

---

## Security Best Practices

### 1. Use Non-Root User (Already Implemented)

The Dockerfile should run as non-root user for security.

### 2. Limit Container Capabilities

Add to `docker-compose.yml`:
```yaml
services:
  obstruction-server:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
```

### 3. Use Read-Only Root Filesystem

```yaml
services:
  obstruction-server:
    read_only: true
    tmpfs:
      - /tmp
```

### 4. Network Isolation

```yaml
networks:
  obstruction-network:
    driver: bridge
    internal: true  # No external access
```

### 5. Regular Updates

```bash
# Update base image and dependencies regularly
docker compose build --pull --no-cache
docker compose up -d
```

---

## Backup and Recovery

### Backup Configuration

```bash
# Backup deployment files
tar -czf obstruction-backup.tar.gz \
  docker-compose.yml \
  .env.docker \
  nginx-docker.conf \
  nginx-obstruction-server.conf

# Backup logs (if persisted)
tar -czf logs-backup.tar.gz logs/
```

### Export/Import Docker Images

```bash
# Save image to file
docker save obstruction-server:latest -o obstruction-server.tar

# Load image from file
docker load -i obstruction-server.tar
```

### Restore from Backup

```bash
# Extract backup
tar -xzf obstruction-backup.tar.gz

# Rebuild and start
docker compose build
docker compose up -d
```

---

## Comparison: Docker vs Native Deployment

| Feature | Docker | Native (systemd) |
|---------|--------|------------------|
| Setup Time | 5-10 min | 15-30 min |
| Python Version | Fixed in image | System dependent |
| Updates | Pull & restart | Git pull & restart service |
| Isolation | Complete | Process level |
| Resource Usage | Slight overhead | Native performance |
| Portability | Highly portable | OS dependent |
| Complexity | Moderate | Low |

**Recommendation**: Use Docker for:
- Quick deployments
- Multiple environments
- Version consistency
- Easy updates

Use Native for:
- Maximum performance
- Minimal resource overhead
- Integration with system services

---

## Advanced: Production Deployment

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml obstruction

# Scale service
docker service scale obstruction_obstruction-server=3
```

### Using with Traefik

Add Traefik labels for automatic SSL and load balancing:

```yaml
services:
  obstruction-server:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.obstruction.rule=Host(`your-domain.com`)"
      - "traefik.http.routers.obstruction.entrypoints=websecure"
      - "traefik.http.routers.obstruction.tls.certresolver=letsencrypt"
```

---

## Support

For issues with Docker deployment:

1. Check logs: `docker logs obstruction-server`
2. Review [Docker documentation](https://docs.docker.com/)
3. Open an issue: https://github.com/upskiller-xyz/server_obstruction/issues

---

**Last Updated**: 2025-01-19
