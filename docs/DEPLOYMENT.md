# Executive Safety Dashboard - Deployment Guide

This comprehensive deployment guide covers all aspects of deploying the Executive Safety Dashboard in various environments, from development to enterprise production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Cloud Platform Deployment](#cloud-platform-deployment)
6. [Production Considerations](#production-considerations)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

#### Development Environment
- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB free disk space
- **OS**: Linux, macOS, or Windows 10/11

#### Production Environment
- **CPU**: 8+ cores per node
- **RAM**: 32GB minimum per node
- **Storage**: 100GB+ SSD storage
- **Network**: 1Gbps+ bandwidth

### Software Dependencies

#### Required
- Docker 20.10+ with Docker Compose 2.0+
- Git 2.30+
- OpenSSL 1.1.1+

#### For Kubernetes Deployment
- kubectl 1.25+
- Helm 3.8+ (optional but recommended)
- Kubernetes cluster 1.25+

#### For Cloud Deployment
- AWS CLI 2.0+ (for AWS)
- Azure CLI 2.0+ (for Azure)
- gcloud CLI (for GCP)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/perdomonestor01-hue/executive-safety-dashboard.git
cd executive-safety-dashboard
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (see Environment Variables section below)
nano .env
```

### 3. Environment Variables

#### Required Variables

```bash
# Database Configuration
DB_PASSWORD=your_secure_database_password_here
DATABASE_URL=postgresql://dashboard_user:${DB_PASSWORD}@postgres:5432/safety_dashboard

# Redis Configuration
REDIS_PASSWORD=your_secure_redis_password_here
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379

# Security
JWT_SECRET=your_super_secure_jwt_secret_minimum_32_characters
SESSION_SECRET=your_secure_session_secret_here

# n8n Configuration
N8N_USER=admin
N8N_PASSWORD=your_secure_n8n_password_here
N8N_DB_PASSWORD=your_secure_n8n_db_password_here

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_grafana_password_here
```

#### Optional Variables for Enterprise Features

```bash
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@company.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=safety-dashboard@company.com
ALERT_EMAIL=executives@company.com

# Cloud Storage (AWS S3)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=safety-dashboard-files

# Single Sign-On (Azure AD)
SSO_ENABLED=true
SSO_PROVIDER=azure-ad
SSO_CLIENT_ID=your_sso_client_id
SSO_CLIENT_SECRET=your_sso_client_secret
SSO_TENANT_ID=your_sso_tenant_id

# Feature Flags
FEATURE_REAL_TIME_ALERTS=true
FEATURE_PREDICTIVE_ANALYTICS=true
FEATURE_EXECUTIVE_REPORTS=true
FEATURE_MOBILE_NOTIFICATIONS=true
```

## Docker Deployment

### Development Deployment

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f

# Access application
open http://localhost
```

### Production Deployment

```bash
# Start production environment with all services
docker-compose up -d

# Scale web application for load balancing
docker-compose up -d --scale web-app=3

# Verify health
curl http://localhost/health
```

### Service Management

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (caution: data loss)
docker-compose down -v

# Restart specific service
docker-compose restart web-app

# View resource usage
docker stats

# Update and restart services
docker-compose pull
docker-compose up -d
```

## Kubernetes Deployment

### 1. Cluster Setup

#### Local Development (minikube)

```bash
# Start minikube
minikube start --cpus=4 --memory=8192 --disk-size=20g

# Enable addons
minikube addons enable ingress
minikube addons enable metrics-server
```

#### Production Cluster Requirements

- **Nodes**: 3+ worker nodes
- **Resources**: 8+ CPU, 32+ GB RAM per node
- **Storage**: Dynamic provisioning enabled
- **Network**: CNI plugin (Calico recommended)

### 2. Prerequisites Installation

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (edit values first)
kubectl create secret generic safety-dashboard-secrets \
  --from-literal=database-url="postgresql://dashboard_user:PASSWORD@postgres:5432/safety_dashboard" \
  --from-literal=redis-url="redis://:PASSWORD@redis:6379" \
  --from-literal=jwt-secret="your-jwt-secret" \
  -n safety-dashboard

# Create ConfigMaps
kubectl apply -f k8s/configmaps.yaml
```

### 3. Storage Setup

```bash
# Create storage class (example for AWS EBS)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  fsType: ext4
allowVolumeExpansion: true
```

### 4. Database Deployment

```bash
# Deploy PostgreSQL and Redis
kubectl apply -f k8s/database-deployment.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres-db -n safety-dashboard --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis-cache -n safety-dashboard --timeout=300s
```

### 5. Application Deployment

```bash
# Deploy web application
kubectl apply -f k8s/web-app-deployment.yaml

# Deploy analytics service
kubectl apply -f k8s/analytics-deployment.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl get pods -n safety-dashboard
kubectl get services -n safety-dashboard
```

### 6. Auto-scaling Setup

```bash
# Apply Horizontal Pod Autoscaler
kubectl apply -f k8s/hpa.yaml

# Verify HPA
kubectl get hpa -n safety-dashboard
```

## Cloud Platform Deployment

### AWS EKS Deployment

#### 1. EKS Cluster Creation

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create EKS cluster
eksctl create cluster \
  --name safety-dashboard-prod \
  --region us-east-1 \
  --nodegroup-name workers \
  --node-type m5.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# Install AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=safety-dashboard-prod
```

#### 2. AWS-Specific Configuration

```bash
# Apply AWS-specific resources
kubectl apply -f k8s/aws/storage-class.yaml
kubectl apply -f k8s/aws/ingress.yaml

# Setup EBS CSI driver
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"
```

### Azure AKS Deployment

#### 1. AKS Cluster Creation

```bash
# Login to Azure
az login

# Create resource group
az group create --name safety-dashboard --location eastus

# Create AKS cluster
az aks create \
  --resource-group safety-dashboard \
  --name safety-dashboard-prod \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-addons monitoring,http_application_routing \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group safety-dashboard --name safety-dashboard-prod
```

#### 2. Azure-Specific Configuration

```bash
# Apply Azure-specific resources
kubectl apply -f k8s/azure/storage-class.yaml
kubectl apply -f k8s/azure/ingress.yaml
```

### Google GKE Deployment

#### 1. GKE Cluster Creation

```bash
# Set project
gcloud config set project your-project-id

# Create cluster
gcloud container clusters create safety-dashboard-prod \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials safety-dashboard-prod --zone us-central1-a
```

#### 2. GCP-Specific Configuration

```bash
# Apply GCP-specific resources
kubectl apply -f k8s/gcp/storage-class.yaml
kubectl apply -f k8s/gcp/ingress.yaml
```

## Production Considerations

### Security Hardening

#### 1. Network Security

```bash
# Apply network policies
kubectl apply -f k8s/security/network-policies.yaml

# Setup Pod Security Standards
kubectl label namespace safety-dashboard pod-security.kubernetes.io/enforce=restricted
```

#### 2. RBAC Configuration

```bash
# Create service accounts with minimal permissions
kubectl apply -f k8s/security/rbac.yaml
```

#### 3. Secrets Management

```bash
# Use external secrets operator with HashiCorp Vault
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# Apply external secrets
kubectl apply -f k8s/security/external-secrets.yaml
```

### Performance Optimization

#### 1. Resource Limits and Requests

```yaml
# Example resource configuration
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

#### 2. Database Optimization

```bash
# PostgreSQL configuration for production
kubectl apply -f k8s/production/postgres-config.yaml

# Redis configuration for production
kubectl apply -f k8s/production/redis-config.yaml
```

### High Availability

#### 1. Multi-Zone Deployment

```yaml
# Pod anti-affinity for high availability
spec:
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: safety-dashboard-web
          topologyKey: kubernetes.io/zone
```

#### 2. Database High Availability

```bash
# Deploy PostgreSQL with high availability
kubectl apply -f k8s/production/postgres-ha.yaml
```

## Monitoring Setup

### 1. Prometheus and Grafana

```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values k8s/monitoring/prometheus-values.yaml

# Verify installation
kubectl get pods -n monitoring
```

### 2. Custom Dashboards

```bash
# Apply custom Grafana dashboards
kubectl apply -f k8s/monitoring/dashboards/
```

### 3. Alerting Rules

```bash
# Apply alerting rules
kubectl apply -f k8s/monitoring/alerts/
```

## Backup & Recovery

### 1. Database Backups

```bash
# Create backup CronJob
kubectl apply -f k8s/backup/postgres-backup-cronjob.yaml

# Manual backup
kubectl create job --from=cronjob/postgres-backup postgres-backup-manual -n safety-dashboard
```

### 2. Application Backups

```bash
# Install Velero for cluster backups
kubectl apply -f https://github.com/vmware-tanzu/velero/releases/download/v1.10.0/00-prereqs.yaml

# Create backup
velero backup create safety-dashboard-backup --include-namespaces safety-dashboard
```

### 3. Disaster Recovery

```bash
# Restore from Velero backup
velero restore create --from-backup safety-dashboard-backup

# Database point-in-time recovery
kubectl exec -it postgres-0 -n safety-dashboard -- pg_restore -d safety_dashboard /backups/backup.dump
```

## Troubleshooting

### Common Issues

#### 1. Pod Startup Issues

```bash
# Check pod status
kubectl get pods -n safety-dashboard

# Describe pod for events
kubectl describe pod <pod-name> -n safety-dashboard

# Check logs
kubectl logs <pod-name> -n safety-dashboard --previous
```

#### 2. Service Discovery Issues

```bash
# Check services
kubectl get services -n safety-dashboard

# Test service connectivity
kubectl run test-pod --image=busybox --rm -it --restart=Never -- nslookup postgres-service.safety-dashboard.svc.cluster.local
```

#### 3. Storage Issues

```bash
# Check PVCs
kubectl get pvc -n safety-dashboard

# Check storage classes
kubectl get storageclass

# Describe PVC for events
kubectl describe pvc <pvc-name> -n safety-dashboard
```

#### 4. Performance Issues

```bash
# Check resource usage
kubectl top pods -n safety-dashboard
kubectl top nodes

# Check HPA status
kubectl get hpa -n safety-dashboard

# Scale manually if needed
kubectl scale deployment safety-dashboard-web --replicas=5 -n safety-dashboard
```

### Debug Commands

```bash
# Execute shell in container
kubectl exec -it <pod-name> -n safety-dashboard -- /bin/bash

# Port forward for debugging
kubectl port-forward service/postgres-service 5432:5432 -n safety-dashboard

# Copy files from pod
kubectl cp safety-dashboard/<pod-name>:/app/logs /local/path

# Check cluster events
kubectl get events --sort-by=.metadata.creationTimestamp -n safety-dashboard
```

### Log Analysis

```bash
# Stream logs from multiple pods
kubectl logs -f deployment/safety-dashboard-web -n safety-dashboard

# Filter logs with grep
kubectl logs deployment/safety-dashboard-web -n safety-dashboard | grep ERROR

# Use stern for advanced log tailing
stern safety-dashboard -n safety-dashboard
```

---

For additional support or questions about deployment, please contact our support team at support@jufipai.com.