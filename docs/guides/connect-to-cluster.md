# Connect Sentinel AI to a Real Cluster

> How to plug Sentinel AI into your existing Kubernetes cluster and observability stack.

---

## Overview

Sentinel AI ships in **simulation mode** — no real connections needed. This guide shows you how to connect it to real infrastructure so it can:

- **Receive alerts** from Prometheus AlertManager → auto-create incidents
- **Query metrics** from Prometheus → real CPU, memory, latency data
- **Read logs** from Fluent Bit → real application logs
- **Talk to Kubernetes** → real pod status, events, deployment state
- **Track deployments** from GitHub → real CI/CD pipeline events

### What You Need

| Component | Required? | Purpose |
|-----------|-----------|---------|
| Kubernetes cluster | ✅ Yes | The thing being monitored |
| Prometheus | ✅ Yes | Metrics collection |
| AlertManager | Recommended | Alert routing to Sentinel AI |
| Fluent Bit / Fluentd | Optional | Log forwarding |
| OpenSearch / Elasticsearch | Optional | Log storage (for querying) |
| GitHub repo | Optional | Deployment tracking |

---

## Quick Start: Prometheus Only (5 minutes)

The fastest path — just connect Prometheus and get real metrics.

### Step 1: Ensure Prometheus is Running

```bash
# Verify Prometheus is accessible
kubectl get svc -n monitoring prometheus
# or
curl http://prometheus:9090/api/v1/status/config
```

### Step 2: Start Sentinel AI with Prometheus URL

```bash
# Set the Prometheus URL
export PROMETHEUS_URL=http://prometheus:9090

# Start Sentinel AI
uvicorn services.gateway.main:app --reload --port 8000
```

### Step 3: Query Real Metrics

```bash
# The metrics collector now queries your real Prometheus
curl "http://localhost:8000/api/v1/analysis/simulate?scenario=missing_env_var"

# Or use the Prometheus MCP tools directly
python -c "
from services.mcp.tools.prometheus import query_instant
import asyncio
result = asyncio.run(query_instant(
    promql='rate(container_cpu_usage_seconds_total{namespace=\"default\"}[5m])'
))
print(result)
"
```

---

## Full Setup: Docker Compose (All-in-One)

If you don't have an existing stack, this spins up everything locally.

### Step 1: Use the Real-Stack Compose File

```bash
# Start Prometheus + AlertManager + Fluent Bit + OpenSearch + Sentinel AI
docker compose -f docker-compose.real.yml up -d
```

### Step 2: Verify

```bash
# Sentinel AI
curl http://localhost:8000/health

# Prometheus (metrics)
curl http://localhost:9090/api/v1/status/config

# OpenSearch (logs)
curl http://localhost:9200/_cluster/health

# AlertManager
curl http://localhost:9093/api/v2/status
```

---

## Integration Details

### 1. Prometheus → Sentinel AI (Metrics)

**What flows:** Prometheus scrapes your pods → Sentinel AI queries Prometheus for real metrics.

**Config:**
```env
# .env
PROMETHEUS_URL=http://prometheus:9090
```

**How it works:**
- The `PrometheusClient` in `services/collector/prometheus_client.py` queries Prometheus
- PromQL queries fetch real CPU, memory, request rate, error rate, latency
- The metrics agent uses this data instead of generated fake data

**Example PromQL queries the system uses:**
```promql
# CPU usage per pod
rate(container_cpu_usage_seconds_total{namespace="default", pod=~"myapp-.*"}[5m])

# Memory usage
container_memory_working_set_bytes{namespace="default", pod=~"myapp-.*"}

# Request rate
rate(http_requests_total{namespace="default"}[5m])

# Error rate
rate(http_requests_total{namespace="default", code=~"5.."}[5m])

# P99 latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{namespace="default"}[5m]))
```

---

### 2. AlertManager → Sentinel AI (Alerts → Incidents)

**What flows:** Prometheus fires alert → AlertManager sends webhook → Sentinel AI auto-creates incident.

**Step 1: Add AlertManager webhook receiver**

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

receivers:
  - name: sentinel-ai
    webhook_configs:
      - url: 'http://sentinel-api:8000/api/v1/webhooks/alertmanager'
        send_resolved: true

route:
  receiver: sentinel-ai
  group_by: ['alertname', 'namespace']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: sentinel-ai
      match:
        severity: critical
```

**Step 2: Sentinel AI receives the webhook**

The webhook endpoint at `/api/v1/webhooks/alertmanager` automatically:
1. Parses the AlertManager payload
2. Creates an incident with severity, title, description
3. Links the alert labels to the incident
4. Triggers AI analysis (if configured)

**Step 3: Test it**

```bash
# Simulate an AlertManager webhook
curl -X POST http://localhost:8000/api/v1/webhooks/alertmanager \
  -H "Content-Type: application/json" \
  -d '{
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "PodCrashLooping",
        "namespace": "default",
        "pod": "myapp-abc123",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Pod myapp-abc123 is crash looping",
        "description": "Pod has been restarting for 10 minutes"
      },
      "startsAt": "2026-08-27T14:30:00Z"
    }]
  }'
```

---

### 3. Fluent Bit → OpenSearch → Sentinel AI (Logs)

**What flows:** Pods emit logs → Fluent Bit collects → OpenSearch stores → Sentinel AI queries.

**Step 1: Fluent Bit sends logs to OpenSearch**

```yaml
# fluent-bit.conf
[OUTPUT]
    Name  opensearch
    Match *
    Host  opensearch
    Port  9200
    Index sentinel-logs
    Type  _doc
    Logstash_Format On
    Logstash_Prefix sentinel-logs
```

**Step 2: Sentinel AI queries OpenSearch**

```env
# .env
OPENSEARCH_URL=http://opensearch:9200
```

**Step 3: Query real logs**

The log collector queries OpenSearch for real application logs:

```python
# What the system queries (PromQL → log search equivalent)
logs = await opensearch_client.search_logs(
    service="sentinel-api",
    level="ERROR",
    last_minutes=30
)
```

---

### 4. Kubernetes API → Sentinel AI (Cluster State)

**What flows:** Sentinel AI calls Kubernetes API → gets real pod status, events, deployment state.

**Step 1: Create a ServiceAccount with read access**

```yaml
# sentinel-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sentinel-ai
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: sentinel-ai-reader
rules:
  - apiGroups: [""]
    resources: ["pods", "events", "configmaps", "services"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sentinel-ai-reader
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: sentinel-ai-reader
subjects:
  - kind: ServiceAccount
    name: sentinel-ai
    namespace: monitoring
```

```bash
kubectl apply -f sentinel-rbac.yaml
```

**Step 2: Mount the ServiceAccount token**

```yaml
# In your Sentinel AI deployment
spec:
  serviceAccountName: sentinel-ai
  containers:
    - name: sentinel-ai
      env:
        - name: K8S_IN_CLUSTER
          value: "true"
```

**Step 3: The system uses the token automatically**

```python
# services/kubernetes/real_client.py
from kubernetes import config, client

class RealK8sClient:
    def __init__(self):
        # Automatically uses the mounted ServiceAccount token
        config.load_incluster_config()
        self.core = client.CoreV1Api()
        self.apps = client.AppsV1Api()

    async def get_crashlooping_pods(self, namespace="default"):
        """Find pods in CrashLoopBackOff — this is how it detects failures."""
        pods = self.core.list_namespaced_pod(namespace)
        problems = []
        for pod in pods.items:
            for cs in (pod.status.container_statuses or []):
                if cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                    problems.append({
                        "pod": pod.metadata.name,
                        "namespace": namespace,
                        "restart_count": cs.restart_co
