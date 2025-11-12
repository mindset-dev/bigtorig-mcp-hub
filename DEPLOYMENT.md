# 🚀 Deployment Guide - bigtorig-mcp-hub

Complete step-by-step deployment guide for the bigtorig MCP hub on Kubernetes (KIND).

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Hostinger server access** - SSH with sudo privileges
- [ ] **KIND cluster running** - 3-node setup (1 control-plane, 2 workers)
- [ ] **Docker installed** - Version 20.10+
- [ ] **kubectl installed** - Configured for KIND cluster
- [ ] **Caddy running** - Reverse proxy container
- [ ] **Domain configured** - `mcp.bigtorig.com` A record pointing to server
- [ ] **Git repository** - Access to project repository

### Verify Prerequisites

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10.0 or higher

# Check kubectl
kubectl version --client
# Expected: Client Version: v1.XX.X

# Check KIND cluster
kubectl cluster-info
# Expected: Kubernetes control plane is running at https://127.0.0.1:XXXXX

# Check nodes
kubectl get nodes
# Expected: 3 nodes in Ready status

# Check Caddy
docker ps | grep caddy
# Expected: Caddy container running

# Test domain resolution
nslookup mcp.bigtorig.com
# Expected: Returns your server IP
```

---

## 🎯 Deployment Overview

The deployment process consists of 10 steps:

1. Clone/navigate to repository
2. Build Docker image
3. Load image into KIND cluster
4. Create Kubernetes secrets
5. Deploy to Kubernetes
6. Create service
7. Verify deployment
8. Configure Caddy reverse proxy
9. Test external access
10. Configure Claude Desktop

**Estimated time:** 15-20 minutes

---

## Step 1: Navigate to Project Directory

```bash
# If already cloned
cd /home/charles/projects/02-StreamableHTTP-mcp-server/02.bigtorig-mcp-hub

# Or clone repository
git clone https://github.com/mindset-dev/bigtorig-mcp-hub.git
cd bigtorig-mcp-hub
```

**Verify files:**
```bash
ls -la
# Expected files:
# - README.md
# - Dockerfile
# - pyproject.toml
# - src/server.py
# - k8s/ directory
```

---

## Step 2: Build Docker Image

Build the container image with FastMCP server.

```bash
docker build -t bigtorig-mcp-hub:latest .
```

**Expected output:**
```
[+] Building 6.0s (14/14) FINISHED
 => exporting to image
 => => naming to docker.io/library/bigtorig-mcp-hub:latest
```

**Verify image:**
```bash
docker images | grep bigtorig-mcp-hub
# Expected: bigtorig-mcp-hub   latest   <IMAGE_ID>   <SIZE>
```

**Troubleshooting:**

If build fails with "README.md not found":
```bash
# Ensure README.md exists
ls -la README.md

# Rebuild
docker build -t bigtorig-mcp-hub:latest .
```

If build fails with "Unable to find lockfile":
```bash
# The Dockerfile generates uv.lock automatically
# Check Dockerfile includes: RUN uv lock && uv sync --frozen --no-dev
cat Dockerfile | grep "uv lock"
```

---

## Step 3: Load Image into KIND Cluster

KIND runs Kubernetes inside Docker containers, so images must be explicitly loaded.

```bash
kind load docker-image bigtorig-mcp-hub:latest --name k8s
```

**This may take 1-2 minutes.** The command will appear to hang - this is normal.

**Verify image loaded:**
```bash
docker exec k8s-control-plane crictl images | grep bigtorig
# Expected: docker.io/library/bigtorig-mcp-hub   latest   <IMAGE_ID>   <SIZE>
```

**Troubleshooting:**

If command times out:
```bash
# Check if load is still running
ps aux | grep "kind load"

# Wait for completion, then verify
docker exec k8s-control-plane crictl images | grep bigtorig
```

---

## Step 4: Create Kubernetes Secrets

Secrets store sensitive credentials (database passwords, API keys).

### Option A: Using Example Template

```bash
# Copy template
cp k8s/secrets-example.yaml k8s/secrets.yaml

# Edit with real credentials
nano k8s/secrets.yaml
# Replace:
# - YOUR_POSTGRES_PASSWORD with actual Postgres password
# - YOUR_QDRANT_API_KEY with actual Qdrant API key
# - YOUR_NEO4J_PASSWORD with actual Neo4j password

# Apply secrets
kubectl apply -f k8s/secrets.yaml

# IMPORTANT: Don't commit secrets.yaml to Git!
echo "k8s/secrets.yaml" >> .gitignore
```

### Option B: Using kubectl directly

```bash
kubectl create secret generic mcp-hub-secrets \
  --from-literal=postgres-user=postgres \
  --from-literal=postgres-password=YOUR_POSTGRES_PASSWORD \
  --from-literal=qdrant-api-key=YOUR_QDRANT_API_KEY \
  --from-literal=neo4j-user=neo4j \
  --from-literal=neo4j-password=YOUR_NEO4J_PASSWORD
```

### Option C: Using Placeholder Values (Testing Only)

For Phase 1 testing (without actual database connections):

```bash
cat <<'EOSECRETS' | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: mcp-hub-secrets
  namespace: default
type: Opaque
stringData:
  postgres-user: "postgres"
  postgres-password: "placeholder-password"
  qdrant-api-key: "placeholder-api-key"
  neo4j-user: "neo4j"
  neo4j-password: "placeholder-password"
EOSECRETS
```

**Verify secrets created:**
```bash
kubectl get secret mcp-hub-secrets
# Expected: NAME                TYPE     DATA   AGE
#           mcp-hub-secrets     Opaque   5      10s
```

**View secret contents (base64 encoded):**
```bash
kubectl get secret mcp-hub-secrets -o yaml
# Shows base64-encoded values
```

---

## Step 5: Deploy to Kubernetes

Deploy the MCP hub with 2 replicas for high availability.

```bash
kubectl apply -f k8s/deployment.yaml
```

**Expected output:**
```
deployment.apps/mcp-hub created
```

**Watch deployment progress:**
```bash
kubectl get pods -l app=mcp-hub -w
# Watch pods start (press Ctrl+C to exit)
```

**Expected pod status:**
```
NAME                      READY   STATUS    RESTARTS   AGE
mcp-hub-64c475c6b-xxxxx   1/1     Running   0          10s
mcp-hub-64c475c6b-yyyyy   1/1     Running   0          10s
```

**Check deployment details:**
```bash
kubectl describe deployment mcp-hub
# Shows: Replicas, Strategy, Pod Template, Events
```

**Check pod logs:**
```bash
kubectl logs -l app=mcp-hub --tail=20
# Expected: FastMCP startup banner, "Starting MCP server"
```

**Troubleshooting:**

If pods are in `ImagePullBackOff`:
```bash
# Image not loaded into KIND
kind load docker-image bigtorig-mcp-hub:latest --name k8s
kubectl rollout restart deployment/mcp-hub
```

If pods are in `CrashLoopBackOff`:
```bash
# Check logs for errors
kubectl logs -l app=mcp-hub --tail=50

# Common issues:
# - Missing dependencies in Dockerfile
# - Python syntax errors in server.py
# - Port conflicts
```

If pods are in `Pending`:
```bash
# Check node resources
kubectl describe pod -l app=mcp-hub | grep -A 10 Events
# Look for resource constraints or scheduling issues
```

---

## Step 6: Create Service

Create a NodePort service to expose the MCP hub externally.

```bash
kubectl apply -f k8s/service.yaml
```

**Expected output:**
```
service/mcp-hub-service created
```

**Verify service:**
```bash
kubectl get svc mcp-hub-service
# Expected:
# NAME              TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
# mcp-hub-service   NodePort   10.96.81.155    <none>        8000:30800/TCP   10s
```

**Key details:**
- **Type:** NodePort (accessible from host machine)
- **ClusterIP:** 10.96.81.155 (internal cluster IP)
- **Port:** 8000 (internal service port)
- **NodePort:** 30800 (external access port)
- **Session Affinity:** ClientIP (critical for SSE sessions with multiple replicas)
- **Affinity Timeout:** 10800 seconds (3 hours)

> **⚠️ Important:** Session affinity is **required** when running multiple replicas with FastMCP 2.x SSE transport. Without it, sessions stored in memory aren't shared between pods, causing "Could not find session" errors.

**Test internal service access:**
```bash
kubectl run -it --rm test-curl --image=curlimages/curl --restart=Never \
  -- curl -I http://mcp-hub-service:8000/sse

# Expected: HTTP/1.1 200 OK
```

---

## Step 7: Verify Deployment

Comprehensive deployment verification.

### Check All Resources

```bash
kubectl get deployments,pods,svc -l app=mcp-hub
```

**Expected output:**
```
NAME                      READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/mcp-hub   2/2     2            2           5m

NAME                          READY   STATUS    RESTARTS   AGE
pod/mcp-hub-64c475c6b-xxxxx   1/1     Running   0          5m
pod/mcp-hub-64c475c6b-yyyyy   1/1     Running   0          5m

NAME                      TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)          AGE
service/mcp-hub-service   NodePort   10.96.81.155   <none>        8000:30800/TCP   4m
```

✅ **All checks passed** if:
- Deployment shows `2/2 READY`
- Both pods are `Running`
- Service has `ClusterIP` assigned

### Check Pod Distribution

```bash
kubectl get pods -l app=mcp-hub -o wide
```

**Expected:** Pods distributed across different worker nodes for high availability.

```
NAME                      ... NODE          ...
mcp-hub-64c475c6b-xxxxx   ... k8s-worker   ...
mcp-hub-64c475c6b-yyyyy   ... k8s-worker2  ...
```

### Check Pod Logs

```bash
kubectl logs -l app=mcp-hub --tail=30
```

**Expected startup messages:**
```
╭──────────────────────────────────────────╮
│         FastMCP 2.13.0.2                 │
│  🖥  Server name: bigtorig-mcp-hub       │
│  📦 Transport:   SSE                     │
│  🔗 Server URL:  http://0.0.0.0:8000/sse │
╰──────────────────────────────────────────╯

INFO Starting MCP server 'bigtorig-mcp-hub' with transport 'sse'
INFO Uvicorn running on http://0.0.0.0:8000
```

### Test NodePort Access

Get KIND control-plane IP:
```bash
docker inspect k8s-control-plane | grep IPAddress | grep -v null
# Example: "IPAddress": "172.23.0.3"
```

Test NodePort:
```bash
curl -I -m 2 http://172.23.0.3:30800/sse
```

**Expected response:**
```
HTTP/1.1 200 OK
content-type: text/event-stream; charset=utf-8
cache-control: no-store
```

---

## Step 8: Configure Caddy Reverse Proxy

Add reverse proxy configuration for external HTTPS access.

### Get KIND Control-Plane IP

```bash
docker inspect k8s-control-plane | grep '"IPAddress"' | head -1
# Example output: "IPAddress": "172.23.0.3"
```

### Add to Caddyfile

```bash
# Backup existing Caddyfile
cp /home/charles/local-ai-packaged/Caddyfile /home/charles/local-ai-packaged/Caddyfile.backup

# Add MCP hub configuration
cat >> /home/charles/local-ai-packaged/Caddyfile << 'EOCADDY'

# MCP Hub (Kubernetes)
mcp.bigtorig.com {
    reverse_proxy http://172.23.0.3:30800
}
EOCADDY
```

**Replace `172.23.0.3` with your actual control-plane IP!**

### Validate Caddyfile

```bash
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
```

**Expected:** No errors, or only formatting warnings.

### Reload Caddy

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

**Expected output:**
```json
{"level":"info","ts":...,"msg":"using config from file","file":"/etc/caddy/Caddyfile"}
{"level":"info","ts":...,"msg":"adapted config to JSON","adapter":"caddyfile"}
```

### Verify Caddy Configuration

```bash
docker exec caddy caddy config | jq '.apps.http.servers'
# Should show mcp.bigtorig.com in server list
```

---

## Step 9: Test External Access

Verify the MCP hub is accessible via HTTPS from the internet.

### Test from Server

```bash
curl -I -m 2 https://mcp.bigtorig.com/sse
```

**Expected response:**
```
HTTP/2 200
date: Tue, 04 Nov 2025 XX:XX:XX GMT
content-type: text/event-stream; charset=utf-8
server: cloudflare
via: 1.1 Caddy
```

✅ **Key indicators:**
- HTTP/2 200 status
- `content-type: text/event-stream`
- `via: 1.1 Caddy` (request went through Caddy)

### Test with mcp-remote

```bash
npx mcp-remote https://mcp.bigtorig.com/sse
```

**Expected output:**
```
[PID] Using automatically selected callback port: XXXXX
[PID] Connecting to remote server: https://mcp.bigtorig.com/sse
[PID] Using transport strategy: http-first
[PID] Connection successful
```

Press Ctrl+C to exit.

### Test from External Machine

From your laptop or another machine:

```bash
curl -I https://mcp.bigtorig.com/sse
```

Should return same HTTP/2 200 response.

---

## Step 10: Configure Claude Desktop

Add the MCP hub to Claude Desktop for AI assistant access.

### Locate Configuration File

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Add Configuration

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bigtorig-hub": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.bigtorig.com/sse"
      ]
    }
  }
}
```

If you already have other MCP servers configured:

```json
{
  "mcpServers": {
    "hostinger-monitor": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp-docker.bigtorig.com/sse"]
    },
    "bigtorig-hub": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.bigtorig.com/sse"]
    }
  }
}
```

### Restart Claude Desktop

**IMPORTANT:** Complete restart required!

**Windows:**
1. Right-click Claude Desktop in system tray
2. Choose "Quit"
3. Wait 5 seconds
4. Start Claude Desktop again

**macOS:**
1. Cmd+Q to quit Claude Desktop
2. Wait 5 seconds
3. Start Claude Desktop again

**Linux:**
1. Close Claude Desktop completely
2. Wait 5 seconds
3. Start Claude Desktop again

### Verify in Claude Desktop

After restart, look for the MCP server indicator (usually a hammer icon or tools menu).

**Test commands:**
```
"Check if the bigtorig MCP hub is healthy"
"What infrastructure services are available in bigtorig?"
```

Claude should use the `health_check` and `list_services` tools.

---

## 🎉 Deployment Complete!

### Verification Checklist

- [ ] Docker image built successfully
- [ ] Image loaded into KIND cluster
- [ ] Kubernetes secrets created
- [ ] Deployment shows 2/2 pods running
- [ ] Service created with NodePort
- [ ] Pods distributed across worker nodes
- [ ] NodePort accessible (http://172.23.0.3:30800/sse)
- [ ] Caddy configured and reloaded
- [ ] External HTTPS access working (https://mcp.bigtorig.com/sse)
- [ ] Claude Desktop configured and restarted
- [ ] Tools accessible from Claude Desktop

### Your Infrastructure

```
Internet (HTTPS)
    ↓
Cloudflare DNS (mcp.bigtorig.com)
    ↓
Caddy Reverse Proxy (TLS termination)
    ↓
KIND NodePort (172.23.0.3:30800)
    ↓
Kubernetes Service (Load Balancer)
    ↓
┌─────────────┬─────────────┐
│   Pod 1     │   Pod 2     │
│ k8s-worker  │ k8s-worker2 │
└─────────────┴─────────────┘
```

### Next Steps

1. **Monitor deployment:**
   ```bash
   kubectl get pods -l app=mcp-hub -w
   kubectl logs -l app=mcp-hub -f
   ```

2. **Test tools in Claude Desktop:**
   - "Check bigtorig hub health"
   - "List available services"

3. **Explore Kubernetes features:**
   - Self-healing: `kubectl delete pod <pod-name>`
   - Scaling: `kubectl scale deployment mcp-hub --replicas=3`
   - Updates: Modify code, rebuild, reload

4. **Phase 2 preparation:**
   - Review database connection requirements
   - Plan tool implementation
   - See [README.md](./README.md) roadmap

---

## 🔧 Common Post-Deployment Tasks

### View Real-Time Logs

```bash
kubectl logs -l app=mcp-hub -f --all-containers=true
```

### Scale Deployment

```bash
# Scale up
kubectl scale deployment mcp-hub --replicas=5

# Scale down
kubectl scale deployment mcp-hub --replicas=2
```

### Update Application

```bash
# 1. Make code changes in src/server.py
# 2. Rebuild image
docker build -t bigtorig-mcp-hub:latest .

# 3. Load into KIND
kind load docker-image bigtorig-mcp-hub:latest --name k8s

# 4. Rolling restart
kubectl rollout restart deployment/mcp-hub

# 5. Watch rollout
kubectl rollout status deployment/mcp-hub
```

### Delete Deployment

```bash
# Delete all resources
kubectl delete deployment mcp-hub
kubectl delete service mcp-hub-service
kubectl delete secret mcp-hub-secrets

# Or delete from files
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/service.yaml
```

---

## 📞 Need Help?

**Troubleshooting:** See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

**Kubernetes benefits:** See [KUBERNETES-BENEFITS.md](./KUBERNETES-BENEFITS.md)

**Main documentation:** See [README.md](./README.md)

**Issues:** [GitHub Issues](https://github.com/mindset-dev/bigtorig-mcp-hub/issues)

---

**Deployment guide completed successfully! 🚀**
