# docs/deployment.md
# ===================================

# Deployment Guide

This guide covers deployment strategies for DroneSphere from development to production environments.

## Development Deployment

### Local Development

**Prerequisites:**
- Python 3.10+
- Docker & Docker Compose
- Git

**Setup:**
```bash
# Clone and setup
git clone https://github.com/yourusername/dronesphere.git
cd dronesphere
uv venv && source .venv/bin/activate
uv pip install -e .[dev]

# Start SITL
./scripts/run_sitl.sh

# Run system (separate terminals)
python -m dronesphere.agent
uvicorn dronesphere.server.api:app --port 8000 --reload
```

**Environment Variables:**
```bash
# .env
DEBUG=true
LOG_LEVEL=DEBUG
AGENT_DRONE_CONNECTION_STRING=udp://:14540
BACKEND_TELEMETRY_BACKEND=mavsdk
```

### Docker Development

**All-in-One Setup:**
```bash
# Start full stack
docker-compose up

# View logs
docker-compose logs -f server
docker-compose logs -f agent

# Stop and clean up
docker-compose down -v
```

**Services:**
- **SITL:** PX4 simulation on ports 14540/14550
- **mavlink2rest:** REST API on port 8080
- **Agent:** Command execution engine
- **Server:** REST API on port 8000

## Production Deployment

### Docker Production

**Environment Setup:**
```bash
# .env.prod
LOG_LEVEL=INFO
DEBUG=false
DRONE_CONNECTION_STRING=udp://drone-gateway:14540
TELEMETRY_BACKEND=mavlink2rest
MAVLINK2REST_URL=http://mavlink2rest:8080
SERVER_PORT=8000
```

**Deploy:**
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs server
```

**Production Services:**
- **nginx:** Reverse proxy with SSL termination
- **server:** API server with health checks
- **agent:** Command execution with resource limits
- **monitoring:** Prometheus + Grafana (optional)

### Kubernetes Deployment

**Prerequisites:**
- Kubernetes cluster (1.20+)
- kubectl configured
- Helm 3.0+ (optional)

**Basic Deployment:**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dronesphere
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dronesphere-config
  namespace: dronesphere
data:
  LOG_LEVEL: "INFO"
  BACKEND_TELEMETRY_BACKEND: "mavlink2rest"
  MAVLINK2REST_URL: "http://mavlink2rest:8080"
---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dronesphere-server
  namespace: dronesphere
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dronesphere-server
  template:
    metadata:
      labels:
        app: dronesphere-server
    spec:
      containers:
      - name: server
        image: dronesphere/server:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: dronesphere-config
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: dronesphere-server
  namespace: dronesphere
spec:
  selector:
    app: dronesphere-server
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dronesphere-ingress
  namespace: dronesphere
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.dronesphere.example.com
    secretName: dronesphere-tls
  rules:
  - host: api.dronesphere.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dronesphere-server
            port:
              number: 80
```

**Deploy to Kubernetes:**
```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment
kubectl get pods -n dronesphere
kubectl get services -n dronesphere
kubectl get ingress -n dronesphere

# View logs
kubectl logs -f deployment/dronesphere-server -n dronesphere
```

### Cloud Platforms

#### AWS ECS

**Task Definition:**
```json
{
  "family": "dronesphere",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "dronesphere-server",
      "image": "dronesphere/server:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "DEBUG", "value": "false"}
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/dronesphere",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Google Cloud Run

**Deploy:**
```bash
# Build and push image
docker build -t gcr.io/project-id/dronesphere:latest .
docker push gcr.io/project-id/dronesphere:latest

# Deploy to Cloud Run
gcloud run deploy dronesphere \
  --image gcr.io/project-id/dronesphere:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars "LOG_LEVEL=INFO,DEBUG=false"
```

#### Azure Container Instances

**Deploy:**
```bash
# Create resource group
az group create --name dronesphere-rg --location eastus

# Deploy container
az container create \
  --resource-group dronesphere-rg \
  --name dronesphere \
  --image dronesphere/server:latest \
  --cpu 1 \
  --memory 1 \
  --ports 8000 \
  --environment-variables LOG_LEVEL=INFO DEBUG=false \
  --restart-policy Always
```

## Configuration Management

### Environment Variables

**Core Settings:**
```bash
# Logging
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
LOG_FORMAT=json|text

# Agent
AGENT_HOST=localhost
AGENT_PORT=8001
AGENT_DRONE_CONNECTION_STRING=udp://:14540
AGENT_TELEMETRY_UPDATE_INTERVAL=0.25
AGENT_COMMAND_TIMEOUT=300

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_API_PREFIX=/api/v1
SERVER_CORS_ORIGINS=["http://localhost:3000"]

# Backend
BACKEND_DEFAULT_BACKEND=mavsdk
BACKEND_TELEMETRY_BACKEND=mavsdk
BACKEND_MAVLINK2REST_URL=http://localhost:8080

# Paths
PATH_SHARED_CONFIG_PATH=./shared
PATH_COMMAND_LIBRARY_PATH=./shared/commands

# Metrics
METRICS_ENABLED=true
METRICS_PORT=9090
```

### Configuration Files

**shared/config/production.yaml:**
```yaml
logging:
  level: INFO
  format: json

agent:
  telemetry_update_interval: 0.25
  command_timeout: 300

server:
  cors_origins:
    - "https://dashboard.dronesphere.com"
    - "https://api.dronesphere.com"

safety:
  global_limits:
    max_altitude: 120.0
    max_speed: 15.0
  
  geofence:
    enabled: true
    radius: 1000.0
    
  failsafe:
    enabled: true
    actions:
      rc_loss: "return_to_launch"
      low_battery: "land"
```

### Secrets Management

**Kubernetes Secrets:**
```bash
# Create secret
kubectl create secret generic dronesphere-secrets \
  --from-literal=api-key=your-api-key \
  --from-literal=database-url=postgres://... \
  -n dronesphere

# Use in deployment
spec:
  containers:
  - name: server
    envFrom:
    - secretRef:
        name: dronesphere-secrets
```

**Docker Secrets:**
```bash
# Create secret
echo "your-api-key" | docker secret create api_key -

# Use in compose
services:
  server:
    secrets:
      - api_key
    environment:
      - API_KEY_FILE=/run/secrets/api_key
```

## Monitoring & Observability

### Health Checks

**HTTP Health Endpoints:**
```bash
# System health
curl http://localhost:8000/health

# Service readiness
curl http://localhost:8000/ready

# Metrics (Prometheus format)
curl http://localhost:8000/metrics
```

**Docker Health Checks:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### Logging

**Structured Logging:**
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "dronesphere.server",
  "message": "Command executed successfully",
  "drone_id": 1,
  "command_id": "cmd_123",
  "duration": 5.2,
  "correlation_id": "req_abc"
}
```

**Log Aggregation:**
```yaml
# ELK Stack example
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"
      
  logstash:
    image: logstash:7.15.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch
      
  kibana:
    image: kibana:7.15.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### Metrics Collection

**Prometheus Configuration:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dronesphere'
    static_configs:
      - targets: ['server:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

**Grafana Dashboard:**
```json
{
  "dashboard": {
    "title": "DroneSphere Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(dronesphere_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Command Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(dronesphere_commands_completed_total[5m]) / rate(dronesphere_commands_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      }
    ]
  }
}
```

## Security

### Network Security

**Firewall Rules:**
```bash
# Allow API access
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# Allow MAVLink
iptables -A INPUT -p udp --dport 14540 -j ACCEPT
iptables -A INPUT -p udp --dport 14550 -j ACCEPT

# Block everything else
iptables -A INPUT -j DROP
```

**TLS Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.dronesphere.com;
    
    ssl_certificate /etc/ssl/certs/dronesphere.crt;
    ssl_certificate_key /etc/ssl/private/dronesphere.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://dronesphere-backend;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Access Control

**Rate Limiting:**
```nginx
# Nginx rate limiting
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=commands:10m rate=1r/s;
    
    server {
        location /command/ {
            limit_req zone=commands burst=5 nodelay;
            proxy_pass http://backend;
        }
        
        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

**API Keys (Future):**
```python
# Header-based authentication
headers = {
    "Authorization": "Bearer your-api-key",
    "X-API-Key": "your-api-key"
}
```

## Backup & Recovery

### Configuration Backup

```bash
# Backup configuration
tar -czf dronesphere-config-$(date +%Y%m%d).tar.gz \
  shared/ \
  .env \
  docker-compose.yml

# Automated backup
0 2 * * * /usr/local/bin/backup-dronesphere.sh
```

### Disaster Recovery

**Recovery Procedures:**
1. **Infrastructure Recreation:** Redeploy containers/pods
2. **Configuration Restore:** Apply backed-up configurations
3. **Service Verification:** Run health checks
4. **Drone Reconnection:** Verify drone connectivity

**Recovery Script:**
```bash
#!/bin/bash
# disaster-recovery.sh

echo "Starting DroneSphere disaster recovery..."

# Stop services
docker-compose down

# Restore configuration
tar -xzf latest-config-backup.tar.gz

# Restart services
docker-compose up -d

# Wait for health
while ! curl -f http://localhost:8000/health; do
    echo "Waiting for service..."
    sleep 5
done

echo "Recovery complete!"
```

## Performance Tuning

### Resource Optimization

**Container Resources:**
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

**Python Optimizations:**
```bash
# Environment variables
PYTHONOPTIMIZE=1
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

### Database Optimization (Future)

**PostgreSQL Tuning:**
```sql
-- Connection pooling
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB

-- Telemetry table optimization
CREATE INDEX CONCURRENTLY idx_telemetry_drone_timestamp 
ON telemetry (drone_id, timestamp DESC);
```

### Caching Strategy

**Redis Caching:**
```python
# Telemetry caching
TELEMETRY_CACHE_TTL = 1  # 1 second
STATUS_CACHE_TTL = 5     # 5 seconds
```

## Troubleshooting

### Common Issues

**Connection Problems:**
```bash
# Check drone connectivity
nc -u -z drone-ip 14540

# Check service health
curl http://localhost:8000/health

# View logs
docker logs dronesphere-server
kubectl logs deployment/dronesphere-server
```

**Performance Issues:**
```bash
# Check resource usage
docker stats
kubectl top pods

# Monitor metrics
curl http://localhost:8000/metrics | grep -E "(request|command|telemetry)"
```

**Configuration Issues:**
```bash
# Validate configuration
python -c "from dronesphere.core.config import get_settings; print(get_settings())"

# Check command library
python -c "from dronesphere.commands.registry import load_command_library; load_command_library()"
```

### Debug Mode

**Enable Debug Logging:**
```bash
# Environment variable
export DEBUG=true
export LOG_LEVEL=DEBUG

# Runtime configuration
curl -X POST http://localhost:8000/admin/log-level -d '{"level": "DEBUG"}'
```

**Debug Endpoints:**
```bash
# System information
curl http://localhost:8000/debug/info

# Configuration dump
curl http://localhost:8000/debug/config

# Health details
curl http://localhost:8000/debug/health
```

This deployment guide provides comprehensive coverage of deployment strategies from development to produc