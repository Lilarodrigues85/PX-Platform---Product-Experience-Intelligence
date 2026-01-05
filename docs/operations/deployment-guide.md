# Deployment Guide - PX Platform

<div align="center">

**Deployment Guide** | **Versão**: 1.0.0 | **Última Atualização**: 19/10/2025

[![Deploy](https://img.shields.io/badge/deploy-production-green)](link)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.28-blue)](link)
[![DATAMETRIA](https://img.shields.io/badge/DATAMETRIA-Standards-blue)](https://github.com/datametria/standards)

[🚀 Quick Start](#-quick-start) • [☁️ Cloud Setup](#️-cloud-setup) • [🔧 Configuration](#-configuration) • [📊 Monitoring](#-monitoring)

</div>

---

## 📋 Índice

- [🚀 Quick Start](#-quick-start)
- [☁️ Cloud Setup](#️-cloud-setup)
- [🔧 Configuration](#-configuration)
- [📊 Monitoring](#-monitoring)
- [🔒 Security](#-security)
- [📈 Scaling](#-scaling)
- [🔧 Troubleshooting](#-troubleshooting)
- [📋 Checklist](#-checklist)

---

## 🚀 Quick Start

### Pré-requisitos

| Ferramenta | Versão | Propósito |
|------------|--------|-----------|
| **Docker** | 24+ | Containerização |
| **Kubernetes** | 1.28+ | Orquestração |
| **Helm** | 3.12+ | Package manager |
| **kubectl** | 1.28+ | CLI Kubernetes |
| **Terraform** | 1.6+ | Infrastructure as Code |

### Deploy Local (Development)

```bash
# 1. Clonar repositório
git clone https://github.com/datametria/px-platform.git
cd px-platform

# 2. Setup ambiente local
cp .env.example .env
docker-compose up -d

# 3. Verificar serviços
docker-compose ps
curl http://localhost:8000/health
```

### Deploy Staging

```bash
# 1. Configurar kubectl
kubectl config use-context staging

# 2. Deploy com Helm
helm upgrade --install px-platform ./helm/px-platform \
  --namespace px-staging \
  --create-namespace \
  --values helm/values-staging.yaml

# 3. Verificar deploy
kubectl get pods -n px-staging
kubectl get ingress -n px-staging
```

### Deploy Production

```bash
# 1. Configurar kubectl
kubectl config use-context production

# 2. Deploy com Helm
helm upgrade --install px-platform ./helm/px-platform \
  --namespace px-production \
  --create-namespace \
  --values helm/values-production.yaml

# 3. Verificar deploy
kubectl get pods -n px-production
kubectl rollout status deployment/px-backend -n px-production
```

---

## ☁️ Cloud Setup

### AWS Infrastructure

#### 1. EKS Cluster

```hcl
# terraform/aws/main.tf
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "px-platform-${var.environment}"
  cluster_version = "1.28"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    main = {
      name = "px-platform-nodes"
      
      instance_types = ["m5.large"]
      
      min_size     = 3
      max_size     = 10
      desired_size = 3

      disk_size = 50
      
      labels = {
        Environment = var.environment
        Application = "px-platform"
      }
      
      taints = []
    }
    
    clickhouse = {
      name = "clickhouse-nodes"
      
      instance_types = ["r5.2xlarge"]
      
      min_size     = 3
      max_size     = 6
      desired_size = 3
      
      disk_size = 500
      
      labels = {
        Environment = var.environment
        Application = "clickhouse"
        NodeType = "storage"
      }
      
      taints = [
        {
          key    = "storage"
          value  = "clickhouse"
          effect = "NO_SCHEDULE"
        }
      ]
    }
  }

  tags = {
    Environment = var.environment
    Project     = "px-platform"
  }
}
```

#### 2. RDS PostgreSQL

```hcl
# terraform/aws/rds.tf
module "db" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "px-platform-${var.environment}"

  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.r6g.large"
  allocated_storage = 100
  storage_encrypted = true

  db_name  = "px_platform"
  username = "px_admin"
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = module.vpc.database_subnet_group

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  deletion_protection = var.environment == "production"

  tags = {
    Environment = var.environment
    Project     = "px-platform"
  }
}
```

#### 3. ElastiCache Redis

```hcl
# terraform/aws/redis.tf
resource "aws_elasticache_subnet_group" "px_platform" {
  name       = "px-platform-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_replication_group" "px_platform" {
  replication_group_id       = "px-platform-${var.environment}"
  description                = "Redis cluster for PX Platform"

  node_type                  = "cache.r6g.large"
  port                       = 6379
  parameter_group_name       = "default.redis7"

  num_cache_clusters         = 3
  automatic_failover_enabled = true
  multi_az_enabled          = true

  subnet_group_name = aws_elasticache_subnet_group.px_platform.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = {
    Environment = var.environment
    Project     = "px-platform"
  }
}
```

### GCP Infrastructure

#### 1. GKE Cluster

```hcl
# terraform/gcp/main.tf
resource "google_container_cluster" "px_platform" {
  name     = "px-platform-${var.environment}"
  location = var.region

  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
    
    network_policy_config {
      disabled = false
    }
  }

  network_policy {
    enabled = true
  }
}

resource "google_container_node_pool" "px_platform_nodes" {
  name       = "px-platform-nodes"
  location   = var.region
  cluster    = google_container_cluster.px_platform.name
  node_count = 3

  node_config {
    preemptible  = false
    machine_type = "e2-standard-4"
    disk_size_gb = 50
    disk_type    = "pd-ssd"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      environment = var.environment
      application = "px-platform"
    }
  }

  autoscaling {
    min_node_count = 3
    max_node_count = 10
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
```

#### 2. Cloud SQL PostgreSQL

```hcl
# terraform/gcp/database.tf
resource "google_sql_database_instance" "px_platform" {
  name             = "px-platform-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-custom-2-8192"
    
    disk_size = 100
    disk_type = "PD_SSD"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    database_flags {
      name  = "max_connections"
      value = "200"
    }
  }

  deletion_protection = var.environment == "production"
}

resource "google_sql_database" "px_platform" {
  name     = "px_platform"
  instance = google_sql_database_instance.px_platform.name
}
```

---

## 🔧 Configuration

### Helm Values

#### Production Values

```yaml
# helm/values-production.yaml
global:
  environment: production
  domain: px-platform.com
  
image:
  repository: gcr.io/px-platform/backend
  tag: "1.0.0"
  pullPolicy: IfNotPresent

replicaCount: 3

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "1000"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
  hosts:
    - host: api.px-platform.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: px-platform-tls
      hosts:
        - api.px-platform.com

database:
  host: px-platform-prod.cluster-xyz.us-east-1.rds.amazonaws.com
  port: 5432
  name: px_platform
  existingSecret: px-platform-secrets
  secretKeys:
    username: db-username
    password: db-password

redis:
  host: px-platform-prod.cache.amazonaws.com
  port: 6379
  existingSecret: px-platform-secrets
  secretKeys:
    password: redis-password

clickhouse:
  host: clickhouse.px-platform.svc.cluster.local
  port: 9000
  database: px_platform
  existingSecret: px-platform-secrets
  secretKeys:
    username: clickhouse-username
    password: clickhouse-password

kafka:
  bootstrapServers: px-platform-kafka:9092
  topics:
    events: events-raw
    enriched: events-enriched
    insights: insights-generated

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
  prometheusRule:
    enabled: true

secrets:
  existingSecret: px-platform-secrets
  keys:
    jwtSecret: jwt-secret
    openaiApiKey: openai-api-key
    slackWebhook: slack-webhook
```

#### Staging Values

```yaml
# helm/values-staging.yaml
global:
  environment: staging
  domain: staging.px-platform.com

replicaCount: 2

resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 512Mi

autoscaling:
  enabled: false

database:
  host: px-platform-staging.cluster-xyz.us-east-1.rds.amazonaws.com

ingress:
  hosts:
    - host: api-staging.px-platform.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: px-platform-staging-tls
      hosts:
        - api-staging.px-platform.com
```

### Environment Variables

```bash
# .env.production
# Database
DATABASE_URL=postgresql://user:pass@host:5432/px_platform
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://host:6379/0
REDIS_POOL_SIZE=10

# ClickHouse
CLICKHOUSE_URL=http://host:8123
CLICKHOUSE_DATABASE=px_platform
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=secret

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_CONSUMER_GROUP=px-platform
KAFKA_AUTO_OFFSET_RESET=earliest

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false

# Security
JWT_SECRET_KEY=super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=1000

# Monitoring
SENTRY_DSN=https://...
LOG_LEVEL=INFO
METRICS_ENABLED=true

# Features
FEATURE_AI_INSIGHTS=true
FEATURE_EXPERIMENTS=true
FEATURE_REAL_TIME=true
```

### Kubernetes Secrets

```bash
# Criar secrets
kubectl create secret generic px-platform-secrets \
  --from-literal=db-username=px_admin \
  --from-literal=db-password=super-secret-password \
  --from-literal=redis-password=redis-secret \
  --from-literal=clickhouse-username=default \
  --from-literal=clickhouse-password=clickhouse-secret \
  --from-literal=jwt-secret=jwt-super-secret-key \
  --from-literal=openai-api-key=sk-... \
  --from-literal=slack-webhook=https://hooks.slack.com/... \
  --namespace px-production
```

---

## 📊 Monitoring

### Prometheus Metrics

```yaml
# monitoring/prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: px-platform-rules
  namespace: px-production
spec:
  groups:
  - name: px-platform.rules
    rules:
    - alert: PXPlatformHighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value }} errors per second"

    - alert: PXPlatformHighLatency
      expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High latency detected"
        description: "95th percentile latency is {{ $value }}s"

    - alert: PXPlatformDatabaseConnections
      expr: database_connections_active / database_connections_max > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Database connection pool nearly exhausted"

    - alert: PXPlatformEventProcessingLag
      expr: kafka_consumer_lag_sum > 10000
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Event processing lag is high"
        description: "Kafka consumer lag is {{ $value }} messages"
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "PX Platform - Production",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Event Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(events_processed_total[5m])",
            "legendFormat": "Events/sec"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "database_connections_active",
            "legendFormat": "Active"
          },
          {
            "expr": "database_connections_idle",
            "legendFormat": "Idle"
          }
        ]
      }
    ]
  }
}
```

### Health Checks

```python
# health.py
from fastapi import APIRouter, HTTPException
import asyncio
import time

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": time.time()}

@router.get("/ready")
async def readiness_check():
    """Readiness check with dependencies"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "clickhouse": await check_clickhouse(),
        "kafka": await check_kafka()
    }
    
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(status_code=503, detail={"status": "not ready", "checks": checks})

async def check_database():
    try:
        await database.execute("SELECT 1")
        return True
    except Exception:
        return False

async def check_redis():
    try:
        await redis.ping()
        return True
    except Exception:
        return False

async def check_clickhouse():
    try:
        await clickhouse.execute("SELECT 1")
        return True
    except Exception:
        return False

async def check_kafka():
    try:
        # Check if can connect to Kafka
        return True
    except Exception:
        return False
```

---

## 🔒 Security

### Network Policies

```yaml
# security/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: px-platform-network-policy
  namespace: px-production
spec:
  podSelector:
    matchLabels:
      app: px-platform
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  - from:
    - podSelector:
        matchLabels:
          app: px-platform
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### Pod Security Standards

```yaml
# security/pod-security-policy.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: px-production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### RBAC

```yaml
# security/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: px-platform
  namespace: px-production

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: px-production
  name: px-platform-role
rules:
- apiGroups: [""]
  resources: ["secrets", "configmaps"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: px-platform-rolebinding
  namespace: px-production
subjects:
- kind: ServiceAccount
  name: px-platform
  namespace: px-production
roleRef:
  kind: Role
  name: px-platform-role
  apiGroup: rbac.authorization.k8s.io
```

---

## 📈 Scaling

### Horizontal Pod Autoscaler

```yaml
# scaling/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: px-platform-hpa
  namespace: px-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: px-platform
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### Vertical Pod Autoscaler

```yaml
# scaling/vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: px-platform-vpa
  namespace: px-production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: px-platform
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: px-platform
      maxAllowed:
        cpu: 2
        memory: 4Gi
      minAllowed:
        cpu: 100m
        memory: 256Mi
```

### Cluster Autoscaler

```yaml
# scaling/cluster-autoscaler.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  template:
    spec:
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.28.0
        name: cluster-autoscaler
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/px-platform-production
        - --balance-similar-node-groups
        - --scale-down-enabled=true
        - --scale-down-delay-after-add=10m
        - --scale-down-unneeded-time=10m
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Pod CrashLoopBackOff

```bash
# Diagnóstico
kubectl describe pod <pod-name> -n px-production
kubectl logs <pod-name> -n px-production --previous

# Soluções comuns
# - Verificar variáveis de ambiente
# - Verificar secrets
# - Verificar recursos (CPU/Memory)
# - Verificar health checks
```

#### 2. Database Connection Issues

```bash
# Verificar conectividade
kubectl exec -it <pod-name> -n px-production -- nc -zv <db-host> 5432

# Verificar secrets
kubectl get secret px-platform-secrets -n px-production -o yaml

# Verificar logs de conexão
kubectl logs <pod-name> -n px-production | grep -i database
```

#### 3. High Memory Usage

```bash
# Verificar uso de memória
kubectl top pods -n px-production

# Verificar métricas detalhadas
kubectl exec -it <pod-name> -n px-production -- cat /proc/meminfo

# Ajustar recursos
kubectl patch deployment px-platform -n px-production -p '{"spec":{"template":{"spec":{"containers":[{"name":"px-platform","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
```

#### 4. Event Processing Lag

```bash
# Verificar lag do Kafka
kubectl exec -it kafka-0 -n kafka -- kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group px-platform

# Escalar consumers
kubectl scale deployment px-event-processor -n px-production --replicas=5

# Verificar throughput
kubectl logs px-event-processor-xxx -n px-production | grep "events/sec"
```

### Debug Commands

```bash
# Logs em tempo real
kubectl logs -f deployment/px-platform -n px-production

# Exec no container
kubectl exec -it deployment/px-platform -n px-production -- /bin/bash

# Port forward para debug local
kubectl port-forward service/px-platform 8000:80 -n px-production

# Verificar eventos do cluster
kubectl get events -n px-production --sort-by='.lastTimestamp'

# Verificar recursos
kubectl describe nodes
kubectl top nodes
kubectl top pods -n px-production
```

---

## 📋 Checklist

### Pre-Deploy Checklist

- [ ] **Infrastructure**
  - [ ] Cluster Kubernetes funcionando
  - [ ] Banco de dados configurado
  - [ ] Redis configurado
  - [ ] ClickHouse configurado
  - [ ] Kafka configurado

- [ ] **Security**
  - [ ] Secrets criados
  - [ ] RBAC configurado
  - [ ] Network policies aplicadas
  - [ ] TLS certificates válidos

- [ ] **Configuration**
  - [ ] Helm values revisados
  - [ ] Environment variables configuradas
  - [ ] Resource limits definidos
  - [ ] Health checks configurados

- [ ] **Monitoring**
  - [ ] Prometheus configurado
  - [ ] Grafana dashboards importados
  - [ ] Alertas configurados
  - [ ] Logs centralizados

### Post-Deploy Checklist

- [ ] **Verification**
  - [ ] Pods running
  - [ ] Services accessible
  - [ ] Ingress working
  - [ ] Health checks passing

- [ ] **Testing**
  - [ ] Smoke tests passed
  - [ ] API endpoints responding
  - [ ] Database connectivity
  - [ ] Event processing working

- [ ] **Monitoring**
  - [ ] Metrics being collected
  - [ ] Dashboards showing data
  - [ ] Alerts not firing
  - [ ] Logs being ingested

- [ ] **Performance**
  - [ ] Response times < SLA
  - [ ] Resource usage normal
  - [ ] Autoscaling working
  - [ ] No memory leaks

### Rollback Checklist

- [ ] **Preparation**
  - [ ] Previous version identified
  - [ ] Database migrations compatible
  - [ ] Rollback plan documented

- [ ] **Execution**
  - [ ] Traffic drained
  - [ ] Rollback executed
  - [ ] Health checks passing
  - [ ] Monitoring verified

- [ ] **Verification**
  - [ ] Functionality restored
  - [ ] Performance normal
  - [ ] No data loss
  - [ ] Users notified

---

<div align="center">

**Deployment Guide mantido por Lila Rodrigues**

**Última atualização**: 19/10/2025 | **Versão**: 1.0.0

---

**Dúvidas sobre deploy?** Entre em contato via [Discord](https://discord.gg/kKYGmCC3)

</div>