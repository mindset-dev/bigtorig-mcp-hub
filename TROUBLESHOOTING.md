# 🔧 Troubleshooting Guide - bigtorig-mcp-hub

Quick reference for common issues when deploying and running the MCP hub on Kubernetes.

---

## 📋 Quick Diagnostic Commands

```bash
# Check everything at once
kubectl get deployments,pods,svc -l app=mcp-hub

# Check pod status
kubectl get pods -l app=mcp-hub -o wide

# Check pod logs
kubectl logs -l app=mcp-hub --tail=50

# Check pod events
kubectl describe pod -l app=mcp-hub

# Check service
kubectl get svc mcp-hub-service -o yaml

# Check deployment
kubectl describe deployment mcp-hub

# Check secrets
kubectl get secret mcp-hub-secrets
```

---

## 🚨 Common Issues

### Issue #1: "Could not find session" Errors with Claude Desktop ⚠️ CRITICAL

**Symptoms:**
```
Claude Desktop MCP server appears in list but won't turn on
OR
Server connects briefly then fails with errors like:
"Error POSTing to endpoint (HTTP 404): Could not find session"
"WARNING:mcp.server.sse:Could not find session for ID: xxx-xxx-xxx"
```

**Cause:** FastMCP 2.x stores SSE sessions **in memory**. With multiple replicas (2+ pods), load balancing sends requests to different pods that don't have the session.

**Root Cause:**
1. Claude Desktop connects via `mcp-remote` → Pod 1 (creates session in Pod 1's memory)
2. Next request gets load-balanced → Pod 2 (doesn't have the session)
3. Result: HTTP 404 "Could not find session"

**Solution:** Add **ClientIP session affinity** to the service

```bash
# Edit k8s/service.yaml and add:
sessionAffinity: ClientIP
sessionAffinityConfig:
  clientIP:
    timeoutSeconds: 10800  # 3 hours

# Apply the change
kubectl apply -f k8s/service.yaml

# Verify
kubectl describe service mcp-hub-service | grep -A 2 "Session Affinity"
# Should show: Session Affinity: ClientIP

# Completely quit and restart Claude Desktop
```

**Why this works:** Session affinity ensures all requests from the same client IP always go to the same pod, so the session is always found.

**Alternative:** Scale down to 1 replica (loses high availability)
```bash
kubectl scale deployment mcp-hub --replicas=1
```

---

### Issue #2: Pods Not Starting (ImagePullBackOff)

**Symptoms:**
```bash
kubectl get pods -l app=mcp-hub
# NAME                      READY   STATUS             RESTARTS   AGE
# mcp-hub-xxx               0/1     ImagePullBackOff   0          2m
```

**Cause:** Docker image not loaded into KIND cluster

**Solution:**
```bash
# Verify image exists locally
docker images | grep bigtorig-mcp-hub

# If missing, build it
docker build -t bigtorig-mcp-hub:latest /path/to/02.bigtorig-mcp-hub

# Load image into KIND
kind load docker-image bigtorig-mcp-hub:latest --name k8s

# Verify image loaded
docker exec k8s-control-plane crictl images | grep bigtorig

# Restart deployment
kubectl rollout restart deployment/mcp-hub
```

---

### Issue #2: Pods Crash Immediately (CrashLoopBackOff)

**Symptoms:**
```bash
kubectl get pods -l app=mcp-hub
# NAME                      READY   STATUS             RESTARTS   AGE
# mcp-hub-xxx               0/1     CrashLoopBackOff   5          3m
```

**Diagnosis:**
```bash
# Check logs for errors
kubectl logs -l app=mcp-hub --tail=50

# Check previous pod logs
kubectl logs mcp-hub-xxx --previous
```

**Common causes & solutions:**

**Cause 1: Python import error**
```
Error: ModuleNotFoundError: No module named 'fastmcp'
```
**Solution:** Missing dependency in pyproject.toml
```bash
# Verify pyproject.toml includes all dependencies
grep "fastmcp" /path/to/pyproject.toml

# Rebuild image
docker build -t bigtorig-mcp-hub:latest .
kind load docker-image bigtorig-mcp-hub:latest --name k8s
kubectl rollout restart deployment/mcp-hub
```

**Cause 2: Port already in use**
```
Error: [Errno 98] Address already in use
```
**Solution:** Change port in server.py or check for port conflicts
```bash
# Check what's using port 8000 in pod
kubectl exec mcp-hub-xxx -- netstat -tulpn | grep 8000
```

**Cause 3: Python syntax error**
```
Error: SyntaxError: invalid syntax
```
**Solution:** Fix syntax error in src/server.py
```bash
# Test locally first
cd /path/to/02.bigtorig-mcp-hub
python src/server.py
```

---

### Issue #3: Pods Running But Not Ready

**Symptoms:**
```bash
kubectl get pods -l app=mcp-hub
# NAME                      READY   STATUS    RESTARTS   AGE
# mcp-hub-xxx               0/1     Running   0          2m
```

**Cause:** Readiness probe failing

**Diagnosis:**
```bash
# Check pod events
kubectl describe pod mcp-hub-xxx | grep -A 10 Events
# Look for: Readiness probe failed
```

**Solution:**
```bash
# Check if health endpoint exists
kubectl exec mcp-hub-xxx -- curl -I http://localhost:8000/health

# If endpoint doesn't exist, remove readiness probe from deployment.yaml
# Or implement /health endpoint in server.py
```

**Current workaround:** deployment.yaml doesn't include health probes yet

---

### Issue #4: Service Not Accessible Externally

**Symptoms:**
```bash
curl https://mcp.bigtorig.com/sse
# Error: Connection refused or timeout
```

**Diagnosis steps:**

**Step 1: Check pods**
```bash
kubectl get pods -l app=mcp-hub
# All pods should be Running and Ready (1/1)
```

**Step 2: Check service**
```bash
kubectl get svc mcp-hub-service
# Should show NodePort with port 8000:30800
```

**Step 3: Test NodePort directly**
```bash
# Get control-plane IP
docker inspect k8s-control-plane | grep IPAddress | grep -v null
# Example: "IPAddress": "172.23.0.3"

# Test NodePort
curl -I http://172.23.0.3:30800/sse
```

**If NodePort works but external doesn't:**

**Problem:** Caddy configuration issue

**Solution:**
```bash
# Check Caddy is running
docker ps | grep caddy

# Check Caddy config
docker exec caddy caddy validate --config /etc/caddy/Caddyfile

# Verify mcp.bigtorig.com is in Caddyfile
grep "mcp.bigtorig.com" /home/charles/local-ai-packaged/Caddyfile

# If missing, add:
cat >> /home/charles/local-ai-packaged/Caddyfile << 'EOCADDY'

mcp.bigtorig.com {
    reverse_proxy http://172.23.0.3:30800
}
EOCADDY

# Reload Caddy
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Check Caddy logs
docker logs caddy --tail=50
```

---

### Issue #5: "Connection Refused" from Claude Desktop

**Symptoms:**
```
Claude Desktop shows: "Could not connect to server"
Test with mcp-remote shows: Connection refused
```

**Diagnosis:**
```bash
# Test SSE endpoint
curl -I https://mcp.bigtorig.com/sse

# Should return:
# HTTP/2 200
# content-type: text/event-stream
```

**Solutions:**

**Cause 1: Wrong endpoint in config**

Check `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "bigtorig-hub": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.bigtorig.com/sse"  ← Must be /sse, not just /
      ]
    }
  }
}
```

**Cause 2: Claude Desktop not restarted**

- Completely quit Claude Desktop (not just close window)
- Wait 5 seconds
- Start Claude Desktop again

**Cause 3: Firewall blocking**

```bash
# Check if port 443 is open
sudo ufw status | grep 443

# If blocked, allow:
sudo ufw allow 443/tcp
```

---

### Issue #6: High Memory Usage / OOM Kills

**Symptoms:**
```bash
kubectl get pods -l app=mcp-hub
# NAME                      READY   STATUS    RESTARTS   AGE
# mcp-hub-xxx               1/1     Running   3          5m  ← Multiple restarts
```

**Diagnosis:**
```bash
# Check resource usage
kubectl top pods -l app=mcp-hub
# NAME                      CPU(cores)   MEMORY(bytes)
# mcp-hub-xxx               50m          480Mi  ← Near limit (512Mi)

# Check pod events for OOM
kubectl describe pod mcp-hub-xxx | grep OOM
# OOMKilled: true
```

**Solution:**

**Option 1: Increase memory limits**

Edit `k8s/deployment.yaml`:
```yaml
resources:
  requests:
    memory: "256Mi"
  limits:
    memory: "1Gi"  # Increased from 512Mi
```

Apply changes:
```bash
kubectl apply -f k8s/deployment.yaml
```

**Option 2: Investigate memory leak**
```bash
# Check logs for memory-intensive operations
kubectl logs mcp-hub-xxx --tail=100

# Profile memory usage (if needed)
kubectl exec mcp-hub-xxx -- python -m memory_profiler src/server.py
```

---

### Issue #7: KIND Cluster Not Accessible

**Symptoms:**
```bash
kubectl get nodes
# Error: The connection to the server localhost:8080 was refused
```

**Cause:** kubectl not configured or KIND cluster not running

**Solution:**

**Check KIND cluster:**
```bash
docker ps | grep kind
# Should show k8s-control-plane, k8s-worker, k8s-worker2
```

**If cluster not running:**
```bash
# Restart cluster (example)
docker start k8s-control-plane k8s-worker k8s-worker2

# Or recreate cluster
kind create cluster --name k8s --config kind-config.yaml
```

**Configure kubectl:**
```bash
# Get kubectl config
kind get kubeconfig --name k8s > ~/.kube/config

# Or export to current session
export KUBECONFIG=$(kind get kubeconfig-path --name k8s)

# Test
kubectl get nodes
```

---

### Issue #8: Deployment Stuck in "Progressing"

**Symptoms:**
```bash
kubectl get deployment mcp-hub
# NAME      READY   UP-TO-DATE   AVAILABLE   AGE
# mcp-hub   1/2     2            1           5m
```

**Diagnosis:**
```bash
# Check rollout status
kubectl rollout status deployment/mcp-hub

# Check events
kubectl describe deployment mcp-hub | grep -A 20 Events
```

**Common causes:**

**Cause 1: Image pull issue**
```bash
kubectl describe pod mcp-hub-xxx | grep -A 5 "Failed"
# Solution: Reload image into KIND (see Issue #1)
```

**Cause 2: Insufficient resources**
```bash
kubectl describe pod mcp-hub-xxx | grep "Insufficient"
# Solution: Scale down other workloads or adjust resource requests
```

**Cause 3: Pod stuck in initialization**
```bash
kubectl logs mcp-hub-xxx --previous
# Check for startup errors
```

---

### Issue #9: Secrets Not Found

**Symptoms:**
```bash
kubectl logs mcp-hub-xxx
# Error: KeyError: 'POSTGRES_PASSWORD'
```

**Diagnosis:**
```bash
# Check if secret exists
kubectl get secret mcp-hub-secrets
```

**Solution:**

**If secret missing:**
```bash
# Create secret
kubectl apply -f k8s/secrets-example.yaml
# Or create manually with placeholder values (see DEPLOYMENT.md Step 4)
```

**If secret exists but pod can't access:**
```bash
# Check secret is in correct namespace
kubectl get secret mcp-hub-secrets -n default

# Check deployment references correct secret name
kubectl describe deployment mcp-hub | grep secretKeyRef

# Restart pods to pick up secret
kubectl rollout restart deployment/mcp-hub
```

---

### Issue #10: Slow Pod Startup

**Symptoms:**
```bash
kubectl get pods -l app=mcp-hub -w
# Pods take 30+ seconds to become ready
```

**Causes:**

1. **UV dependency installation:** First run installs packages
2. **Image not cached:** Pulling image from registry
3. **Resource constraints:** Limited CPU/memory

**Solutions:**

**Pre-build dependencies:**

Update Dockerfile to pre-install dependencies:
```dockerfile
# Already done in our Dockerfile:
RUN uv sync --frozen --no-dev
# Dependencies installed at build time, not runtime ✅
```

**Pre-load image:**
```bash
# Ensure image is loaded before deployment
kind load docker-image bigtorig-mcp-hub:latest --name k8s
```

**Adjust resource requests:**
```yaml
resources:
  requests:
    cpu: "200m"  # More CPU for faster startup
```

---

## 🔄 Complete Reset Procedure

If everything is broken and you want to start fresh:

```bash
# Step 1: Delete all resources
kubectl delete deployment mcp-hub
kubectl delete service mcp-hub-service
kubectl delete secret mcp-hub-secrets

# Step 2: Verify deletion
kubectl get all -l app=mcp-hub
# Should show: No resources found

# Step 3: Remove image from KIND
docker exec k8s-control-plane crictl rmi bigtorig-mcp-hub:latest

# Step 4: Rebuild from scratch
cd /path/to/02.bigtorig-mcp-hub
docker build -t bigtorig-mcp-hub:latest .
kind load docker-image bigtorig-mcp-hub:latest --name k8s

# Step 5: Redeploy
kubectl apply -f k8s/secrets-example.yaml  # Edit first!
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Step 6: Verify
kubectl get all -l app=mcp-hub
```

---

## 🔍 Advanced Debugging

### Debug Pod with Shell Access

```bash
# Start shell in running pod
kubectl exec -it mcp-hub-xxx -- /bin/bash

# Inside pod, test server
curl http://localhost:8000/sse

# Check environment variables
env | grep -E "POSTGRES|QDRANT|NEO4J"

# Check processes
ps aux | grep python

# Check listening ports
netstat -tulpn

# Exit
exit
```

### Debug Networking

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup mcp-hub-service

# Test service connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl -I http://mcp-hub-service:8000/sse

# Check service endpoints
kubectl get endpoints mcp-hub-service
# Should list pod IPs

# Check pod network
kubectl exec mcp-hub-xxx -- ip addr
```

### Enable Verbose Logging

Edit `src/server.py` to add debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then rebuild and redeploy
```

---

## 📊 Monitoring Commands

### Watch Resources in Real-Time

```bash
# Watch pods
watch kubectl get pods -l app=mcp-hub

# Watch logs (follow)
kubectl logs -l app=mcp-hub -f

# Watch events
kubectl get events --watch
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -l app=mcp-hub

# Node resource usage
kubectl top nodes

# Detailed pod description
kubectl describe pod mcp-hub-xxx
```

---

## 📞 Getting Help

### Check Documentation

1. [README.md](./README.md) - Project overview
2. [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
3. [KUBERNETES-BENEFITS.md](./KUBERNETES-BENEFITS.md) - Architecture details

### Useful Resources

- [Kubernetes Debugging](https://kubernetes.io/docs/tasks/debug/)
- [KIND Documentation](https://kind.sigs.k8s.io/docs/user/quick-start/)
- [FastMCP Docs](https://github.com/jlowin/fastmcp)

### Log Collection for Support

```bash
# Collect all diagnostic info
kubectl get all -l app=mcp-hub > debug-resources.txt
kubectl describe pod -l app=mcp-hub > debug-pods.txt
kubectl logs -l app=mcp-hub --tail=200 > debug-logs.txt
kubectl get events --sort-by='.lastTimestamp' > debug-events.txt

# Package and share
tar -czf debug-info.tar.gz debug-*.txt
```

---

## ✅ Health Check Checklist

Run through this checklist to verify everything is working:

- [ ] KIND cluster running: `docker ps | grep kind`
- [ ] 3 nodes ready: `kubectl get nodes`
- [ ] Image loaded: `docker exec k8s-control-plane crictl images | grep bigtorig`
- [ ] Secret exists: `kubectl get secret mcp-hub-secrets`
- [ ] Deployment ready: `kubectl get deployment mcp-hub` shows `2/2`
- [ ] Pods running: `kubectl get pods -l app=mcp-hub` shows `Running`
- [ ] Service exists: `kubectl get svc mcp-hub-service`
- [ ] NodePort accessible: `curl -I http://172.23.0.3:30800/sse`
- [ ] Caddy configured: `grep mcp.bigtorig.com /path/to/Caddyfile`
- [ ] External HTTPS works: `curl -I https://mcp.bigtorig.com/sse`
- [ ] Claude Desktop configured: Check `claude_desktop_config.json`
- [ ] Claude Desktop restarted: Complete restart performed
- [ ] Tools accessible: Test in Claude Desktop

If all checked ✅, deployment is healthy!

---

**Still having issues? Check the logs:**
```bash
kubectl logs -l app=mcp-hub --tail=100 --all-containers=true
```

**The logs tell the truth!** 🔍
