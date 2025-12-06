# Debug Logging Guide

This guide explains how to enable and use debug logging for troubleshooting the Obstruction Server.

---

## Quick Start

### Enable Debug Mode During Deployment

**Docker Deployment:**
```bash
sudo bash deploy-docker.sh --debug
```

**Native Deployment:**
```bash
sudo bash deploy.sh --debug
```

### Enable Debug Mode on Existing Installation

**Docker:**
```bash
cd /path/to/server_obstruction/deployment

# Use debug environment file
cp .env.docker.debug .env.docker

# Restart containers
docker compose restart
```

**Native (systemd):**
```bash
# Backup current environment
sudo cp /opt/obstruction-server/.env /opt/obstruction-server/.env.backup

# Use debug environment file
sudo cp /opt/obstruction-server/deployment/.env.production.debug /opt/obstruction-server/.env

# Restart service
sudo systemctl restart obstruction-server
```

---

## What Debug Mode Does

Debug mode enables verbose logging throughout the application:

| Component | Production | Debug |
|-----------|-----------|-------|
| **Flask** | INFO level | DEBUG level with detailed errors |
| **Gunicorn** | info logging | debug logging |
| **Application** | INFO messages | DEBUG messages |
| **Requests** | Basic logging | Full request/response logging |
| **TensorFlow** | Errors only | Warnings and errors |

### Debug Environment Variables

```bash
# Debug configuration
FLASK_ENV=development          # Enable development mode
FLASK_DEBUG=True               # Enable Flask debugger
LOG_LEVEL=DEBUG                # Maximum verbosity
DEBUG_REQUESTS=True            # Log all requests/responses
GUNICORN_LOG_LEVEL=debug       # Verbose Gunicorn logs
PYTHONUNBUFFERED=1             # Immediate log output
TF_CPP_MIN_LOG_LEVEL=2         # Show TF warnings
```

---

## Viewing Debug Logs

### Docker Deployment

```bash
# Follow logs in real-time
docker logs -f obstruction-server

# Last 100 lines
docker logs --tail 100 obstruction-server

# Logs since 1 hour ago
docker logs --since 1h obstruction-server

# Save logs to file
docker logs obstruction-server > debug.log 2>&1
```

### Native Deployment (systemd)

```bash
# Follow logs in real-time
sudo journalctl -u obstruction-server -f

# Last 100 lines
sudo journalctl -u obstruction-server -n 100

# Logs since today
sudo journalctl -u obstruction-server --since today

# Show only errors
sudo journalctl -u obstruction-server -p err

# Save logs to file
sudo journalctl -u obstruction-server --since today > debug.log
```

### Application Log Files

If `LOG_FILE` is configured in `.env`:

```bash
# Native deployment
sudo tail -f /var/log/obstruction-server/app.log

# Docker deployment (if volume mounted)
tail -f deployment/logs/app.log
```

---

## Common Debug Scenarios

### 1. Service Won't Start

**Symptoms:** Container/service fails to start

**Debug Steps:**
```bash
# Docker
docker logs obstruction-server

# Native
sudo journalctl -u obstruction-server -n 50
```

**Look for:**
- Port already in use errors
- Missing dependencies
- Configuration errors
- Permission issues

### 2. API Requests Failing

**Symptoms:** Getting 500 errors or unexpected responses

**Debug Steps:**
```bash
# Enable debug mode (shows full request/response)
# Then test the API
curl -X POST http://localhost:8081/obstruction \
  -H "Content-Type: application/json" \
  -d '{"x": 0, "y": 3, "z": 0, "direction_angle": 0, "mesh": [[10,0,-5],[10,5,-5],[10,0,5]]}'

# Watch logs while testing
docker logs -f obstruction-server  # Docker
sudo journalctl -u obstruction-server -f  # Native
```

**Look for:**
- Request validation errors
- Stack traces showing where code fails
- Data type mismatches
- Calculation errors

### 3. Slow Performance

**Symptoms:** Requests taking too long

**Debug Steps:**
```bash
# Check detailed timing in logs
# Debug mode logs processing time for each step

# Monitor resource usage
docker stats obstruction-server  # Docker
top  # Native
```

**Look for:**
- Time spent in different calculation steps
- Memory usage patterns
- CPU bottlenecks
- Large mesh processing times

### 4. Memory Issues

**Symptoms:** Out of memory errors, container restarts

**Debug Steps:**
```bash
# Monitor memory usage
docker stats obstruction-server

# Check logs for memory-related errors
docker logs obstruction-server | grep -i "memory\|oom"
```

**Look for:**
- Large mesh sizes
- Memory allocation failures
- Garbage collection issues

---

## Log Output Examples

### Production Mode (Normal)
```
2025-01-19 10:30:45 - INFO - Server starting on port 8081
2025-01-19 10:30:45 - INFO - Application initialized successfully
2025-01-19 10:31:02 - INFO - POST /obstruction - 200 OK
```

### Debug Mode (Verbose)
```
2025-01-19 10:30:45 - DEBUG - Loading configuration from environment
2025-01-19 10:30:45 - DEBUG - Port: 8081, Workers: 1, Threads: 4
2025-01-19 10:30:45 - INFO - Server starting on port 8081
2025-01-19 10:30:45 - DEBUG - Initializing ObstructionService
2025-01-19 10:30:45 - DEBUG - Triangle filter initialized
2025-01-19 10:30:45 - DEBUG - Plane-triangle intersector initialized
2025-01-19 10:30:45 - INFO - Application initialized successfully
2025-01-19 10:31:02 - DEBUG - Received POST /obstruction
2025-01-19 10:31:02 - DEBUG - Request body: {"x": 0.0, "y": 3.0, "z": 0.0, ...}
2025-01-19 10:31:02 - DEBUG - Validating request data
2025-01-19 10:31:02 - DEBUG - Processing mesh with 1000 triangles
2025-01-19 10:31:02 - DEBUG - Filtering triangles by direction
2025-01-19 10:31:02 - DEBUG - 234 triangles remain after filtering
2025-01-19 10:31:02 - DEBUG - Calculating horizon angle
2025-01-19 10:31:02 - DEBUG - Horizon angle: 23.45 degrees
2025-01-19 10:31:02 - DEBUG - Calculating zenith angle
2025-01-19 10:31:02 - DEBUG - Zenith angle: 15.32 degrees
2025-01-19 10:31:02 - DEBUG - Request completed in 0.043s
2025-01-19 10:31:02 - INFO - POST /obstruction - 200 OK
```

---

## Filtering Debug Logs

### Show Only Specific Components

```bash
# Docker - show only application logs (not gunicorn)
docker logs obstruction-server 2>&1 | grep -v "gunicorn"

# Show only errors and warnings
docker logs obstruction-server 2>&1 | grep -E "ERROR|WARNING"

# Show only calculation-related logs
docker logs obstruction-server 2>&1 | grep -i "calculation\|angle"
```

### Native - Filter by Priority

```bash
# Show errors only
sudo journalctl -u obstruction-server -p err

# Show warnings and errors
sudo journalctl -u obstruction-server -p warning

# Show debug and above
sudo journalctl -u obstruction-server -p debug
```

---

## Disabling Debug Mode

### Return to Production Mode

**Docker:**
```bash
cd /path/to/server_obstruction/deployment

# Restore production environment
cp .env.docker.backup .env.docker
# Or manually edit .env.docker

# Restart containers
docker compose restart
```

**Native:**
```bash
# Restore production environment
sudo cp /opt/obstruction-server/.env.backup /opt/obstruction-server/.env
# Or manually edit /opt/obstruction-server/.env

# Restart service
sudo systemctl restart obstruction-server
```

### Quick Toggle (Edit Environment File)

Edit `.env` or `.env.docker` and change:

```bash
# Change from debug
FLASK_ENV=development
FLASK_DEBUG=True
LOG_LEVEL=DEBUG

# To production
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=INFO
```

Then restart the service.

---

## Performance Impact

Debug mode has performance overhead:

| Metric | Production | Debug | Impact |
|--------|-----------|-------|--------|
| Response Time | ~50ms | ~55ms | +10% |
| Memory Usage | ~200MB | ~220MB | +10% |
| Log Volume | ~1MB/day | ~50MB/day | +50x |
| CPU Usage | ~5% | ~7% | +40% |

**⚠ Warning:** Debug mode should NOT be used in production:
- Higher resource usage
- Slower response times
- Large log files
- Potential security information disclosure

---

## Best Practices

### 1. Use Debug Mode Temporarily
Enable debug mode only when troubleshooting, then disable it.

### 2. Monitor Log File Size
```bash
# Check log file size
docker logs obstruction-server 2>&1 | wc -c  # Docker
du -h /var/log/obstruction-server/  # Native
```

### 3. Save Debug Logs
```bash
# Capture debug session
docker logs obstruction-server > debug-$(date +%Y%m%d-%H%M%S).log

# Or for native
sudo journalctl -u obstruction-server --since "10 minutes ago" > debug.log
```

### 4. Share Logs When Reporting Issues
When opening GitHub issues, include:
- Debug logs showing the error
- Request that caused the issue
- Environment details (Docker vs Native, OS, etc.)

### 5. Sensitive Data
Debug logs may contain:
- Request payloads
- Mesh data
- Calculation results
- System paths

Sanitize logs before sharing publicly.

---

## Troubleshooting Debug Mode Itself

### Debug Mode Not Taking Effect

**Check environment file:**
```bash
# Docker
cat deployment/.env.docker

# Native
sudo cat /opt/obstruction-server/.env
```

**Verify service restarted:**
```bash
# Docker
docker ps -a  # Check container restart time
docker compose restart  # Force restart

# Native
sudo systemctl status obstruction-server
sudo systemctl restart obstruction-server
```

### Too Many Logs

**Reduce verbosity:**
```bash
# Keep debug mode but reduce gunicorn logs
GUNICORN_LOG_LEVEL=info  # Instead of debug

# Or disable request logging
DEBUG_REQUESTS=False
```

### Logs Not Appearing

**Check log configuration:**
```bash
# Verify PYTHONUNBUFFERED is set
echo $PYTHONUNBUFFERED  # Should be 1

# Check if logs are buffered
docker logs obstruction-server --tail 1  # Force output
```

---

## Additional Resources

- **Application logs:** Check `src/server/services/logging.py` for logging implementation
- **Environment variables:** See `.env.production` and `.env.docker` for all options
- **Flask debug mode:** https://flask.palletsprojects.com/en/latest/debugging/
- **Gunicorn logging:** https://docs.gunicorn.org/en/stable/settings.html#logging

---

## Support

If debug logs don't help identify the issue:

1. Save the debug logs
2. Create a minimal reproduction case
3. Open an issue at: https://github.com/upskiller-xyz/server_obstruction/issues
4. Include debug logs and system information

---

**Last Updated**: 2025-01-19
