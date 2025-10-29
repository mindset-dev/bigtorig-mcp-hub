# 🚀 bigtorig-mcp-hub Setup Guide

Step-by-step instructions for deploying your MCP hub to the Hostinger KIND cluster.

---

## 📋 Prerequisites

- ✅ Access to Hostinger server
- ✅ KIND cluster running (3-node setup)
- ✅ Docker installed
- ✅ kubectl configured for KIND cluster
- ✅ UV installed locally (for development)

---

## Step 1: Create the Repository on GitHub

1. Go to https://github.com/organizations/mindset-dev/repositories/new
2. Repository name: `bigtorig-mcp-hub`
3. Description: "MCP Server for Hostinger Infrastructure Services"
4. Make it **Public**
5. Do NOT initialize with README (we already have one)
6. Click "Create repository"

---

## Step 2: Initialize Local Repository

```bash
# On your Hostinger server (or local machine)
cd /path/to/your/workspace

# Create the directory structure
mkdir -p bigtorig-mcp-hub/src bigtorig-mcp-hub/k8s bigtorig-mcp-hub/tests

# Copy all files I created for you into this directory
# (From the outputs folder Claude provided)
```

---

## Step 3: Initialize Git and Push

```bash
cd bigtorig-mcp-hub

# Initialize git
git init
git add .
git commit -m "Initial commit: FastMCP hub for bigtorig.com infrastructure"

# Connect to GitHub
git branch -M main
git remote add origin https://github.com/mindset-dev/bigtorig-mcp-hub.git
git push -u origin main
```

---

## Step 4: Test Locally (Optional)

```bash
# Install dependencies
uv sync

# Create .env file from template
cp .env.example .env
# Edit .env with your actual credentials

# Run the server locally
uv run python src/server.py

# In another terminal, test it
curl http://localhost:8000/health
```

---

## Step 5: Build Docker Image

```bash
# Build the image
docker build -t bigtorig-mcp-hub:latest .

# Test the container locally (optional)
docker run -p 8000:8000 bigtorig-mcp-hub:latest

# In another terminal
curl http://localhost:8000/health
```

---

## Step 6: Load Image into KIND Cluster

```bash
# Load the image into your KIND cluster
kind load docker-image bigtorig-mcp-hub:latest --name k8s

# Verify it was loaded
docker exec -it k8s-control-plane crictl images | grep mcp-hub
```

---

## Step 7: Create Kubernetes Secrets

```bash
# Copy the secrets template
cp k8s/secrets-example.yaml k8s/secrets.yaml

# Edit with your actual credentials
nano k8s/secrets.yaml

# Apply the secrets
kubectl apply -f k8s/secrets.yaml

# Verify
kubectl get secrets mcp-hub-secrets
```

---

## Step 8: Deploy to Kubernetes

```bash
# Apply the deployment
kubectl apply -f k8s/deployment.yaml

# Apply the service
kubectl apply -f k8s/service.yaml

# Check the deployment
kubectl get deployments
kubectl get pods -l app=mcp-hub

# Check the service
kubectl get svc mcp-hub-service
```

---

## Step 9: Verify the Deployment

```bash
# Get pod status
kubectl get pods -l app=mcp-hub

# Check logs
kubectl logs -l app=mcp-hub

# Test from within the cluster
kubectl run -it --rm test-pod --image=curlimages/curl --restart=Never \
  -- curl http://mcp-hub-service:8000/health

# Get the NodePort
kubectl get svc mcp-hub-service
# Note the NodePort (should be 30800)
```

---

## Step 10: Configure Caddy

Get your KIND control-plane IP:

```bash
docker inspect k8s-control-plane | grep IPAddress
# Example output: "IPAddress": "172.23.0.3"
```

Add this to your Caddyfile:

```caddyfile
mcp.bigtorig.com {
    reverse_proxy http://172.23.0.3:30800
}
```

Reload Caddy:

```bash
# If Caddy is running in Docker
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Or if running as a service
sudo systemctl reload caddy
```

---

## Step 11: Test External Access

```bash
# From your local machine (not Hostinger)
curl https://mcp.bigtorig.com/health

# Expected response:
# {"status": "healthy", "service": "bigtorig-mcp-hub", "version": "0.1.0", ...}
```

---

## Step 12: Pin the Repository

1. Go to https://github.com/journeyman33
2. Click "Customize your pins"
3. Select `mindset-dev/bigtorig-mcp-hub`
4. Arrange it as your 6th pin

Your 6 pins should now be:
1. ai-infra-hostinger (mindset-dev)
2. kubernetes-resume-challenge (journeyman33)
3. kodekloud (journeyman33)
4. hugo-site (journeyman33)
5. k8s-resume-blog (journeyman33)
6. bigtorig-mcp-hub (mindset-dev) ← NEW!

---

## 🎉 Success!

Your MCP hub is now:
- ✅ Deployed to KIND cluster
- ✅ Accessible internally at `mcp-hub-service:8000`
- ✅ Accessible via NodePort at `<node-ip>:30800`
- ✅ Accessible publicly at `https://mcp.bigtorig.com`
- ✅ Pinned on your GitHub profile

---

## 🔧 Troubleshooting

### Pod Not Starting

```bash
# Check events
kubectl describe pod -l app=mcp-hub

# Check logs
kubectl logs -l app=mcp-hub

# Common issues:
# - Image not loaded into KIND
# - Missing secrets
# - Port conflicts
```

### Can't Access via NodePort

```bash
# Verify NodePort service
kubectl get svc mcp-hub-service -o yaml

# Test from Hostinger directly
curl http://172.23.0.3:30800/health

# Check Caddy logs
docker logs caddy
```

### Secrets Not Working

```bash
# Verify secret exists
kubectl get secret mcp-hub-secrets

# Check secret contents (base64 encoded)
kubectl get secret mcp-hub-secrets -o yaml

# Recreate if needed
kubectl delete secret mcp-hub-secrets
kubectl apply -f k8s/secrets.yaml
kubectl rollout restart deployment/mcp-hub
```

---

## 🚀 Next Steps

Now that your basic MCP hub is running, you can:

1. Add actual Postgres tools (next phase)
2. Add Qdrant vector search tools
3. Add Neo4j graph query tools
4. Test with Claude Desktop
5. Expand to other services (n8n, Flowise, etc.)

---

## 📞 Need Help?

Check the main README.md for more details, or review the ai-infra-hostinger documentation.
