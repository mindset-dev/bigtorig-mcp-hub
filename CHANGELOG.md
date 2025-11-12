# Changelog - bigtorig-mcp-hub

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-11-10 - Phase 2 Complete

### 🎉 Major Release: Full Database Integration

This release completes Phase 2 with full database integration and critical production fixes.

### ✨ Added

#### New Postgres Tools (5 total)
- `postgres_list_databases()` - List all databases on Supabase server
- `postgres_create_database()` - Create new databases with validation
- `postgres_query()` - Execute SELECT queries (read-only for safety)
- `postgres_list_tables()` - List tables in current database
- `postgres_describe_table()` - Get detailed table schema

#### New MySQL Tools (3 total)
- `mysql_query()` - Execute SELECT queries
- `mysql_list_tables()` - List tables
- `mysql_describe_table()` - Get table schema

#### New Qdrant Tools (3 total)
- `qdrant_search()` - Vector search (placeholder - needs embedding model)
- `qdrant_list_collections()` - List all collections
- `qdrant_collection_info()` - Get collection details

#### New Neo4j Tools (3 total)
- `neo4j_query()` - Execute Cypher queries (read-only)
- `neo4j_list_nodes()` - List graph nodes
- `neo4j_get_relationships()` - Get node relationships

#### Database Setup
- Created `affirmation_app` Postgres database for Flutter project
- Updated Kubernetes secrets with real credentials
- Connected MCP server to affirmation_app database

### 🔧 Fixed

#### Critical: Session Affinity for SSE (Issue #1)
**Problem:** FastMCP 2.x stores SSE sessions in memory. With 2+ pod replicas, load balancing caused "Could not find session" errors (HTTP 404).

**Solution:** Added ClientIP session affinity to Kubernetes service:
```yaml
sessionAffinity: ClientIP
sessionAffinityConfig:
  clientIP:
    timeoutSeconds: 10800  # 3 hours
```

**Impact:** Claude Desktop now connects reliably with multiple replicas maintaining high availability.

**Files changed:**
- `k8s/service.yaml` - Added session affinity configuration
- `TROUBLESHOOTING.md` - New Issue #1 with detailed solution
- `DEPLOYMENT.md` - Added session affinity documentation
- `README.md` - Updated Phase 2 status and critical configuration note

### 📚 Documentation

#### New Files
- `AFFIRMATION_APP_DATABASE.md` - Complete guide for affirmation app database
  - Database connection details
  - Suggested schema (categories, affirmations, user_favorites, user_history)
  - Flutter integration examples
  - MCP usage examples
  - Security considerations
  - Backup/restore procedures

#### Updated Files
- `CLAUDE.md`
  - Updated Phase 2 status to "Complete"
  - Added all 16 tools with descriptions
  - Updated tool counts and categories
  - Added session affinity to service.yaml example
  - Updated database connection details
- `README.md`
  - Updated Phase 2 status to "Complete"
  - Replaced "Planned" section with "Delivered" features
  - Added critical session affinity configuration note
  - Documented all 16 tools with examples
- `DEPLOYMENT.md`
  - Added session affinity importance and configuration
  - Added warning about multi-replica SSE sessions
- `TROUBLESHOOTING.md`
  - New Issue #1: "Could not find session" with detailed solution
  - Renumbered existing issues
  - Added session affinity verification steps

### 📊 Statistics

- **Total Tools:** 16 (up from 2)
- **Tool Categories:** 5 (Foundational, Postgres, MySQL, Qdrant, Neo4j)
- **Lines of Code:** ~850+ (up from ~70)
- **Documentation Pages:** 7 files updated/created

### 🐛 Known Issues

- Qdrant vector search requires embedding model (not yet implemented)
- No connection pooling (using direct connections)
- No liveness/readiness probes yet (Phase 3)

### 🚀 Performance

- Session affinity timeout: 10800 seconds (3 hours)
- Multi-replica support: ✅ Works with session affinity
- Zero-downtime deployments: ✅ Maintained
- High availability: ✅ 2 replicas with self-healing

### 🔐 Security

- Read-only SQL queries enforced (SELECT only)
- Database name validation (alphanumeric + underscores)
- SQL injection protection via parameterized queries
- Safe identifier quoting with psycopg2.sql
- Credentials stored in Kubernetes secrets

### 📝 Configuration Changes

**Kubernetes Secrets Updated:**
```yaml
postgres-db: "affirmation_app"  # Changed from "postgres"
postgres-password: "<actual_password>"  # Changed from placeholder
```

**Kubernetes Service Updated:**
```yaml
sessionAffinity: ClientIP  # Changed from "None"
sessionAffinityConfig:
  clientIP:
    timeoutSeconds: 10800  # Added
```

### 🎯 Phase 3 Preview

Upcoming features planned for Phase 3:
- [ ] Horizontal Pod Autoscaler
- [ ] Liveness/Readiness probes
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Connection pooling
- [ ] Integration with n8n workflows
- [ ] Flowise chatbot integration
- [ ] mem0 memory system integration

---

## [0.1.0] - 2025-11-04 - Phase 1 Complete

### Initial Release - Infrastructure Foundation

#### Added
- 3-node KIND cluster deployment (1 control-plane, 2 workers)
- Multi-replica deployment (2 pods)
- NodePort service (port 30800)
- Kubernetes Secrets management
- External HTTPS access via Caddy
- Self-healing capability
- Horizontal scaling support
- Zero-downtime rolling updates

#### Tools
- `health_check` - Server health status
- `list_services` - Infrastructure service inventory

#### Documentation
- Initial README.md
- DEPLOYMENT.md guide
- TROUBLESHOOTING.md
- KUBERNETES-BENEFITS.md
- NETWORK.md

---

**Version Format:** MAJOR.MINOR.PATCH
- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes

**Last Updated:** 2025-11-10
