# 🌐 Network Architecture Guide - bigtorig-mcp-hub

Complete guide to understanding the network topology and connectivity strategy for the MCP hub running on Kubernetes (KIND) with external database services.

---

## 📊 Network Topology Overview

```
Internet (HTTPS)
    ↓
[Cloudflare DNS: mcp.bigtorig.com]
    ↓
[Caddy Reverse Proxy: 82.25.116.252]
    ↓
[KIND NodePort: 172.23.0.3:30800]
    ↓
[Kubernetes Service: 10.96.81.155:8000]
    ↓
┌──────────────────────┬──────────────────────┐
│  MCP Hub Pod 1       │  MCP Hub Pod 2       │
│  10.244.2.x:8000     │  10.244.1.x:8000     │
└──────────────────────┴──────────────────────┘
           ↓
    [Host Gateway: 82.25.116.252]
           ↓
┌────────────────────────────────────────────┐
│  Database Services (Docker Containers)     │
│  • Postgres: 82.25.116.252:5432           │
│  • Qdrant:   82.25.116.252:6333           │
│  • Neo4j:    82.25.116.252:7687           │
└────────────────────────────────────────────┘
```

---

## 🏗️ Network Layers Explained

### Layer 1: Internet to Caddy

**Route:** `Internet → Cloudflare → Caddy`

| Component | Address | Purpose |
|-----------|---------|---------|
| **Domain** | `mcp.bigtorig.com` | Public DNS name |
| **Cloudflare** | DNS + CDN | DNS resolution, DDoS protection |
| **Caddy** | `82.25.116.252:443` | TLS termination, reverse proxy |

**How it works:**
1. User/Claude Desktop connects to `https://mcp.bigtorig.com/sse`
2. Cloudflare resolves DNS to Hostinger server IP: `82.25.116.252`
3. Caddy receives HTTPS request on port 443
4. Caddy terminates TLS and forwards to KIND NodePort

---

### Layer 2: Caddy to Kubernetes

**Route:** `Caddy → KIND Cluster`

| Component | Address | Network | Purpose |
|-----------|---------|---------|---------|
| **Caddy** | `172.23.0.1` | Docker bridge | Source of proxy requests |
| **KIND Control Plane** | `172.23.0.3` | KIND network | Kubernetes API & NodePort |
| **NodePort** | `172.23.0.3:30800` | - | External access to K8s service |

**Caddy Configuration:**
```caddyfile
mcp.bigtorig.com {
    reverse_proxy http://172.23.0.3:30800
}
```

**How it works:**
1. Caddy forwards HTTP to KIND control-plane: `http://172.23.0.3:30800`
2. KIND's NodePort (30800) receives the request
3. NodePort routes to Kubernetes Service

---

### Layer 3: Kubernetes Internal Routing

**Route:** `NodePort → Service → Pods`

| Component | Address | Network | Purpose |
|-----------|---------|---------|---------|
| **NodePort** | `30800` | - | External access point |
| **Service (ClusterIP)** | `10.96.81.155:8000` | K8s Service Network | Load balancer |
| **Pod 1** | `10.244.2.x:8000` | Pod Network (worker) | MCP server instance |
| **Pod 2** | `10.244.1.x:8000` | Pod Network (worker2) | MCP server instance |

**Service Configuration:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-hub-service
spec:
  type: NodePort
  selector:
    app: mcp-hub
  ports:
  - port: 8000        # Service port
    targetPort: 8000  # Pod port
    nodePort: 30800   # External port
```

**How it works:**
1. Request arrives at NodePort 30800
2. Kubernetes Service (`mcp-hub-service`) receives it
3. Service load-balances across healthy pods (round-robin)
4. Request reaches one of the MCP Hub pods

---

### Layer 4: Pods to Database Services

**Route:** `Pods → Host Gateway → Database Containers`

This is the **most complex** part due to Docker network isolation.

#### Network Isolation Challenge

```
┌─────────────────────────────────────────────────────────┐
│  Docker Host (Hostinger Server: 82.25.116.252)         │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  KIND Network: 172.23.0.0/16                     │  │
│  │  Gateway: 172.23.0.1                             │  │
│  │  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │  Pod 1      │  │  Pod 2      │               │  │
│  │  │ 10.244.2.x  │  │ 10.244.1.x  │               │  │
│  │  └─────────────┘  └─────────────┘               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Caddy-Shared Network: 172.19.0.0/16            │  │
│  │  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │  Qdrant     │  │  Neo4j      │               │  │
│  │  │ 172.19.0.6  │  │ 172.19.0.8  │               │  │
│  │  └─────────────┘  └─────────────┘               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Supabase Network: 172.20.0.0/16                │  │
│  │  ┌─────────────┐                                 │  │
│  │  │  Postgres   │                                 │  │
│  │  │ 172.20.0.15 │                                 │  │
│  │  └─────────────┘                                 │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Problem:** KIND network (172.23.0.0/16) **cannot** directly reach:
- Caddy-shared network (172.19.0.0/16)
- Supabase network (172.20.0.0/16)

**Solution:** Use the **host machine as a bridge** via exposed ports!

---

## 🔑 Connection Strategy: Host IP + Exposed Ports

### Why Use Host IP (82.25.116.252)?

Docker networks are isolated from each other, but all containers can reach the **host machine**. By exposing database ports on the host, KIND pods can connect via:

```
Pod → Host IP:Port → Docker Port Mapping → Database Container
```

### Database Connection Table

| Service | Container IP | Docker Network | Exposed on Host | Pod Connection String |
|---------|-------------|----------------|-----------------|----------------------|
| **Postgres** | `172.20.0.15:5432` | supabase | ✅ `0.0.0.0:5432` | `82.25.116.252:5432` |
| **Qdrant** | `172.19.0.6:6333` | caddy-shared | ✅ `0.0.0.0:6333` | `82.25.116.252:6333` |
| **Neo4j** | `172.19.0.8:7687` | caddy-shared | ✅ `0.0.0.0:7687` | `82.25.116.252:7687` ⚠️ |

**Legend:**
- ✅ = Working
- ⚠️ = Partially working (needs additional config)

---

## 📍 IP Address Reference

### Static vs Dynamic Addresses

| Address Type | Address | Stability | Notes |
|--------------|---------|-----------|-------|
| **Hostinger Public IP** | `82.25.116.252` | 🟢 Static | Fixed by hosting provider |
| **Kubernetes Service** | `10.96.81.155` | 🟡 Semi-static | Changes only on service deletion |
| **Pod IPs** | `10.244.x.x` | 🔴 Dynamic | Changes on pod restart |
| **Container IPs** | `172.19.0.x`, `172.20.0.x` | 🟠 Usually static | Can change if container recreated |
| **KIND Network** | `172.23.0.0/16` | 🟢 Static | Fixed in KIND config |
| **KIND Gateway** | `172.23.0.1` | 🟢 Static | Fixed in KIND network |

### Why Container IPs Change

Container IPs (`172.19.0.6`, `172.20.0.15`, etc.) are assigned by Docker and will change if:
1. Container is recreated (`docker rm` + `docker run`)
2. Docker daemon is restarted
3. Network is recreated

**Best Practice:** Always use the **host IP + port** strategy, not direct container IPs!

---

## 🎯 Correct Connection Patterns

### ✅ CORRECT: Use Host IP + Port

```yaml
# Kubernetes Secret (Current Configuration)
stringData:
  postgres-host: "82.25.116.252"  # Host IP
  postgres-port: "5432"            # Exposed port
  
  qdrant-host: "82.25.116.252"    # Host IP
  qdrant-port: "6333"              # Exposed port
  
  neo4j-uri: "bolt://82.25.116.252:7687"  # Host IP
```

**Why this works:**
1. Pods can reach host IP from any Docker network
2. Host port mappings remain stable
3. Firewall rules protect access
4. DNS not needed (host IP is static)

---

### ❌ INCORRECT: Direct Container IPs

```yaml
# This DOES NOT work from KIND pods
stringData:
  postgres-host: "172.20.0.15"  # Unreachable from KIND
  qdrant-host: "172.19.0.6"     # Unreachable from KIND
```

**Why this fails:**
- KIND network (172.23.0.0/16) cannot route to other Docker networks
- Docker bridge networks are isolated by design

---

### ❌ INCORRECT: KIND Gateway IP

```yaml
# This DOES NOT work either
stringData:
  postgres-host: "172.23.0.1"   # Gateway can't route back to host ports
  qdrant-host: "172.23.0.1"
```

**Why this fails:**
- `172.23.0.1` is the gateway **within** the KIND network
- It doesn't route back to host ports properly
- Creates a routing loop

---

## 🔐 Firewall Configuration

### UFW Rules for KIND Access

```bash
# Allow KIND cluster (172.23.0.0/16) to reach database ports
sudo ufw allow from 172.23.0.0/16 to any port 5432 comment 'Postgres for KIND'
sudo ufw allow from 172.23.0.0/16 to any port 6333 comment 'Qdrant for KIND'
sudo ufw allow from 172.23.0.0/16 to any port 7687 comment 'Neo4j for KIND'
```

**Why needed:**
- UFW blocks by default
- KIND pods use host IP to connect
- Without these rules, connections timeout

**Current Firewall Status:**
```bash
Status: active

To                         Action      From
--                         ------      ----
5432                       ALLOW       Anywhere
6333                       ALLOW       172.23.0.0/16  # Added for KIND
7687                       ALLOW       172.23.0.0/16  # Added for KIND
```

---

## 🔄 Port Mapping Strategy

### Database Port Exposure

Each database service must be exposed on the host for KIND pods to access:

```bash
# Postgres (Already exposed by Supabase)
docker ps | grep supabase-db
# 0.0.0.0:5432->5432/tcp  ✅

# Qdrant (We added port mapping)
docker run -d --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant:latest  ✅

# Neo4j (Already exposed)
docker ps | grep neo4j
# 0.0.0.0:7687->7687/tcp  ✅
```

**Port Mapping Format:**
```
-p [HOST_IP]:[HOST_PORT]:[CONTAINER_PORT]

-p 6333:6333           # Bind to all interfaces (0.0.0.0)
-p 127.0.0.1:6333:6333 # Bind only to localhost (NOT accessible from KIND)
```

---

## 🧪 Testing Connectivity

### From Host Machine

```bash
# Test Postgres
psql -h localhost -U postgres -d postgres -c "SELECT version();"

# Test Qdrant
curl http://localhost:6333/collections

# Test Neo4j
docker exec neo4j cypher-shell -u neo4j -p PASSWORD "RETURN 1;"
```

### From KIND Pod

```bash
# Test Postgres
kubectl exec deployment/mcp-hub -- sh -c "
  cd /app && uv run python3 -c '
    import psycopg2
    conn = psycopg2.connect(host=\"82.25.116.252\", port=5432, user=\"postgres\", password=\"PASSWORD\", database=\"postgres\")
    print(\"✅ Postgres connected\")
  '
"

# Test Qdrant
kubectl exec deployment/mcp-hub -- sh -c "
  cd /app && uv run python3 -c '
    from qdrant_client import QdrantClient
    client = QdrantClient(host=\"82.25.116.252\", port=6333)
    print(\"✅ Qdrant connected:\", len(client.get_collections().collections), \"collections\")
  '
"
```

---

## 🎭 DNS vs IP Addresses

### Why Not Use DNS?

**Question:** Why use `82.25.116.252` instead of DNS names like `postgres.local`?

**Answer:** Docker DNS is network-scoped!

```
┌─────────────────────────────────────────────────┐
│  Caddy-Shared Network (172.19.0.0/16)          │
│  DNS: postgres → 172.19.0.x                     │
│  DNS: qdrant → 172.19.0.6                       │
├─────────────────────────────────────────────────┤
│  KIND Network (172.23.0.0/16)                   │
│  DNS: postgres → NOT FOUND ❌                    │
│  DNS: qdrant → NOT FOUND ❌                      │
└─────────────────────────────────────────────────┘
```

**Docker DNS Rules:**
1. Each Docker network has its own DNS
2. DNS names only resolve within the same network
3. KIND pods cannot resolve names from caddy-shared or supabase networks

**Exception:** You could set up custom DNS entries or use Docker's special hostname `host.docker.internal`, but:
- `host.docker.internal` doesn't work in KIND by default
- Custom DNS adds complexity
- Static host IP is simpler and reliable

---

## 📝 Network Summary

### Current Working Configuration

| Layer | Component | Address | Status |
|-------|-----------|---------|--------|
| **External** | Domain | `mcp.bigtorig.com` | ✅ |
| **External** | Caddy | `82.25.116.252:443` | ✅ |
| **K8s** | NodePort | `172.23.0.3:30800` | ✅ |
| **K8s** | Service | `10.96.81.155:8000` | ✅ |
| **K8s** | Pods | `10.244.x.x:8000` | ✅ |
| **Database** | Postgres | `82.25.116.252:5432` | ✅ |
| **Database** | Qdrant | `82.25.116.252:6333` | ✅ |
| **Database** | Neo4j | `82.25.116.252:7687` | ⚠️ |

### Key Takeaways

1. **Host IP (82.25.116.252) is the bridge** between isolated Docker networks
2. **Port exposure** is required for cross-network communication
3. **Firewall rules** must allow KIND network (172.23.0.0/16) to reach database ports
4. **Container IPs are dynamic** - always use host IP + port
5. **DNS doesn't work** across Docker networks - use IPs

---

## 🚀 Adding New Database Services

### Example: Adding MariaDB

**Step 1: Ensure port is exposed**
```bash
docker run -d \
  --name mariadb \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=password \
  mariadb:latest
```

**Step 2: Add firewall rule**
```bash
sudo ufw allow from 172.23.0.0/16 to any port 3306 comment 'MariaDB for KIND'
```

**Step 3: Update Kubernetes secrets**
```yaml
stringData:
  mariadb-host: "82.25.116.252"
  mariadb-port: "3306"
  mariadb-user: "root"
  mariadb-password: "password"
```

**Step 4: Connect from pod**
```python
import mysql.connector
conn = mysql.connector.connect(
    host=os.getenv("MARIADB_HOST"),
    port=int(os.getenv("MARIADB_PORT")),
    user=os.getenv("MARIADB_USER"),
    password=os.getenv("MARIADB_PASSWORD")
)
```

**✅ Same pattern for any database service!**

---

## 🔧 Troubleshooting Network Issues

### Connection Timeout

**Symptom:** `timed out` or `Connection refused`

**Check:**
1. Is service exposed on host port? `docker ps | grep <service>`
2. Is firewall rule added? `sudo ufw status | grep <port>`
3. Is service listening on 0.0.0.0? `docker inspect <service> | grep HostIp`
4. Can host reach service? `curl http://localhost:<port>`

### Wrong IP Used

**Symptom:** Works from host, fails from pod

**Check:**
- Are you using host IP (`82.25.116.252`)?
- Not using container IP (`172.19.0.x`)?
- Not using gateway IP (`172.23.0.1`)?

### DNS Resolution Failure

**Symptom:** `Name or service not known`

**Solution:**
- Don't use DNS names across networks
- Use IP addresses instead

---

## 📚 Further Reading

- [KIND Networking](https://kind.sigs.k8s.io/docs/user/configuration/#networking)
- [Docker Networks](https://docs.docker.com/network/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [UFW Firewall](https://help.ubuntu.com/community/UFW)

---

**Created:** 2025-11-05  
**Status:** Phase 2 Complete - Postgres ✅ Qdrant ✅ Working
