# Deployment Guide

## Deployment Options

### 1. Docker Compose (Development/Staging)

```bash
# Full stack
docker compose up -d

# Minimal stack (app + postgres + redis + kafka)
docker compose -f docker-compose.minimal.yml up -d

# View logs
docker compose logs -f sentinel

# Stop
docker compose down
```

### 2. Kubernetes (Production)

```bash
# Apply all manifests
kubectl apply -f infrastructure/kubernetes/services/sentinel-service.yaml
kubectl apply -f infrastructure/kubernetes/configmaps/sentinel-config.yaml
kubectl apply -f infrastructure/kubernetes/configmaps/sentinel-secrets.yaml
kubectl apply -f infrastructure/kubernetes/deployments/sentinel-deployment.yaml

# Check status
kubectl -n sentinel get pods
kubectl -n sentinel rollout status deployment/sentinel-ai

# View logs
kubectl -n sentinel logs -f deployment/sentinel-ai

# Scale
kubectl -n sentinel scale deployment/sentinel-ai --replicas=5
```

### 3. Terraform (AWS ECS)

```bash
cd infrastructure/terraform
terraform init
terraform plan -var="environment=production"
terraform apply -var="environment=production"
```

## Environment Variables

### Required for Production

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://host:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | `kafka1:9092,kafka2:9092` |

### Optional (AI Mode)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Use real OpenAI GPT-4 |
| `ANTHROPIC_API_KEY` | Use real Claude |
| *(none)* | Falls back to simulation mode |

### Optional (Integrations)

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub API access |
| `JIRA_BASE_URL` | Jira instance URL |
| `JIRA_API_TOKEN` | Jira API token |
| `SLACK_BOT_TOKEN` | Slack bot token |

## Health Checks

The application exposes Kubernetes-compatible health probes:

- **Liveness** (`/health`): Returns 200 if the process is alive
- **Readiness** (`/ready`): Returns 200 only if PostgreSQL and Redis are reachable

## Scaling Considerations

- **Horizontal**: Scale the Sentinel AI deployment (stateless)
- **Kafka consumers**: Each consumer group processes independently
- **Database**: Use read replicas for query-heavy workloads
- **Redis**: Use Redis Cluster for high-throughput caching

## Monitoring

When deployed with the full observability stack:
- **Prometheus**: `http://prometheus:9090` — Metrics collection
- **Grafana**: `http://grafana:3001` — Dashboards (admin/admin)
- **OpenTelemetry**: Distributed tracing to `otel-collector:4317`
