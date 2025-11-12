# Affirmation App Database Setup

This document describes the `affirmation_app` Postgres database created for the Flutter affirmation application project.

## Database Details

- **Database Name:** `affirmation_app`
- **Location:** Supabase Postgres at `82.25.116.252:5432`
- **Owner:** `postgres`
- **Encoding:** UTF8
- **Created:** 2025-11-10
- **Purpose:** Backend database for Android affirmation app (Flutter)

## Connection Details

### From MCP Server (Kubernetes)

The bigtorig-mcp-hub server is configured to connect to this database via Kubernetes secrets:

```bash
kubectl get secret mcp-hub-secrets -o yaml
```

**Environment variables in pods:**
- `POSTGRES_HOST`: `82.25.116.252`
- `POSTGRES_PORT`: `5432`
- `POSTGRES_USER`: `postgres`
- `POSTGRES_DB`: `affirmation_app`
- `POSTGRES_PASSWORD`: (stored in secret)

### From Flutter App (Windows Desktop Development)

For local development on Windows 10 in PowerShell:

```yaml
# pubspec.yaml dependencies
dependencies:
  postgres: ^3.0.0
  # or
  supabase_flutter: ^2.0.0
```

**Connection string:**
```dart
final connection = PostgreSQLConnection(
  '82.25.116.252',
  5432,
  'affirmation_app',
  username: 'postgres',
  password: 'YOUR_PASSWORD',
);
```

### From Direct SQL Client

```bash
# psql
psql -h 82.25.116.252 -p 5432 -U postgres -d affirmation_app

# Or with password in environment
export PGPASSWORD='YOUR_PASSWORD'
psql -h 82.25.116.252 -p 5432 -U postgres -d affirmation_app
```

## Available MCP Tools

You can manage this database via Claude Desktop using the bigtorig-hub MCP server:

### List All Databases
```
"List all Postgres databases on my server"
```

### Check Current Database
```
"What tables exist in the affirmation_app database?"
```

### Create Tables
```
"Run this query: CREATE TABLE affirmations (
  id SERIAL PRIMARY KEY,
  text TEXT NOT NULL,
  category VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
)"
```

### Query Data
```
"Show me all rows from the affirmations table"
"Count how many affirmations are in each category"
```

### Inspect Schema
```
"Describe the structure of the affirmations table"
```

## Suggested Schema for Affirmation App

Here's a recommended schema for your affirmation app:

### Tables

#### 1. categories
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sample data
INSERT INTO categories (name, description, icon) VALUES
('motivation', 'Motivational affirmations', 'star'),
('confidence', 'Build self-confidence', 'heart'),
('gratitude', 'Practice gratitude', 'sun'),
('success', 'Achievement and success', 'trophy'),
('health', 'Health and wellness', 'fitness');
```

#### 2. affirmations
```sql
CREATE TABLE affirmations (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    author VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_affirmations_category ON affirmations(category_id);
CREATE INDEX idx_affirmations_active ON affirmations(is_active);

-- Sample data
INSERT INTO affirmations (text, category_id) VALUES
('I am capable of achieving great things', 1),
('I trust in my abilities and myself', 2),
('I am grateful for all the blessings in my life', 3),
('Success comes naturally to me', 4),
('My body is healthy and strong', 5);
```

#### 3. user_favorites (optional - for user tracking)
```sql
CREATE TABLE user_favorites (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,  -- Could be device ID or user UUID
    affirmation_id INTEGER REFERENCES affirmations(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, affirmation_id)
);

CREATE INDEX idx_favorites_user ON user_favorites(user_id);
```

#### 4. user_history (optional - track which affirmations were shown)
```sql
CREATE TABLE user_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    affirmation_id INTEGER REFERENCES affirmations(id) ON DELETE CASCADE,
    shown_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_history_user_date ON user_history(user_id, shown_at DESC);
```

## Usage via MCP (Claude Desktop)

### Setup Database Schema

```
"Create the categories table in affirmation_app with columns: id (serial primary key), name (varchar 50 not null unique), description (text), icon (varchar 50), created_at (timestamp default now)"

"Create the affirmations table with columns: id (serial primary key), text (text not null), category_id (integer references categories), author (varchar 100), is_active (boolean default true), created_at (timestamp), updated_at (timestamp)"

"Insert sample categories: motivation, confidence, gratitude, success, health"
```

### Add Affirmations

```
"Insert an affirmation: 'I am worthy of love and respect' in the confidence category"

"Add multiple affirmations for the motivation category"
```

### Query Affirmations

```
"Show me all affirmations in the confidence category"

"Get a random affirmation from the database"

"List all categories with their affirmation counts"
```

## Flutter App Integration

### 1. Install Postgres Package

```yaml
# pubspec.yaml
dependencies:
  postgres: ^3.0.0
```

### 2. Create Database Service

```dart
import 'package:postgres/postgres.dart';

class DatabaseService {
  late PostgreSQLConnection connection;
  
  Future<void> connect() async {
    connection = PostgreSQLConnection(
      '82.25.116.252',
      5432,
      'affirmation_app',
      username: 'postgres',
      password: 'YOUR_PASSWORD',
    );
    
    await connection.open();
  }
  
  Future<List<Map<String, dynamic>>> getRandomAffirmation() async {
    return await connection.query(
      'SELECT a.text, a.author, c.name as category '
      'FROM affirmations a '
      'JOIN categories c ON a.category_id = c.id '
      'WHERE a.is_active = true '
      'ORDER BY RANDOM() '
      'LIMIT 1'
    );
  }
  
  Future<List<Map<String, dynamic>>> getAffirmationsByCategory(String category) async {
    return await connection.query(
      'SELECT a.text, a.author '
      'FROM affirmations a '
      'JOIN categories c ON a.category_id = c.id '
      'WHERE c.name = @category AND a.is_active = true',
      substitutionValues: {'category': category}
    );
  }
  
  Future<void> close() async {
    await connection.close();
  }
}
```

### 3. Usage in App

```dart
void main() async {
  final db = DatabaseService();
  await db.connect();
  
  // Get random affirmation
  final result = await db.getRandomAffirmation();
  if (result.isNotEmpty) {
    print('Today\'s affirmation: ${result.first['text']}');
  }
  
  await db.close();
}
```

## Security Considerations

### For Production

1. **Create a dedicated user** instead of using `postgres`:
```sql
CREATE USER affirmation_app_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE affirmation_app TO affirmation_app_user;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO affirmation_app_user;
```

2. **Use environment variables** for credentials:
```dart
final password = Platform.environment['DB_PASSWORD'] ?? '';
```

3. **Consider using Supabase SDK** instead of direct Postgres connection:
```yaml
dependencies:
  supabase_flutter: ^2.0.0
```

## Updating Kubernetes to Use Different Database

To switch the MCP server to a different database:

```bash
# Update the secret
kubectl patch secret mcp-hub-secrets -p '{"stringData":{"postgres-db":"different_database"}}'

# Restart pods to apply change
kubectl rollout restart deployment/mcp-hub

# Verify
kubectl exec deployment/mcp-hub -- env | grep POSTGRES_DB
```

## Backup and Migration

### Backup Current Database

```bash
pg_dump -h 82.25.116.252 -p 5432 -U postgres -d affirmation_app > affirmation_app_backup.sql
```

### Restore from Backup

```bash
psql -h 82.25.116.252 -p 5432 -U postgres -d affirmation_app < affirmation_app_backup.sql
```

### Export Data as JSON (via MCP)

```
"Export all affirmations as JSON format from the affirmations table"
```

## Next Steps

1. **Design your schema** - Customize the suggested schema above
2. **Create tables** - Use MCP tools via Claude Desktop
3. **Populate data** - Add your affirmations
4. **Test queries** - Verify data structure works for your app
5. **Connect Flutter app** - Implement database service
6. **Build UI** - Create affirmation display screens
7. **Deploy** - Package for Android and deploy to Hostinger

## Troubleshooting

### Can't Connect from Flutter App

```dart
// Test connection
try {
  final conn = PostgreSQLConnection(
    '82.25.116.252',
    5432,
    'affirmation_app',
    username: 'postgres',
    password: 'YOUR_PASSWORD',
  );
  await conn.open();
  print('Connected successfully!');
  await conn.close();
} catch (e) {
  print('Connection failed: $e');
}
```

### MCP Tools Not Working

```bash
# Check if pods are connected to correct database
kubectl exec deployment/mcp-hub -- env | grep POSTGRES

# Check logs for connection errors
kubectl logs -l app=mcp-hub --tail=50
```

### Permission Denied

Make sure you're using the correct password stored in the Kubernetes secret:

```bash
kubectl get secret mcp-hub-secrets -o jsonpath='{.data.postgres-password}' | base64 -d
```

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Postgres Package for Flutter](https://pub.dev/packages/postgres)
- [Flutter Database Best Practices](https://docs.flutter.dev/data-and-backend/state-mgmt/options)

---

**Last Updated:** 2025-11-10  
**Database Status:** ✅ Created and Ready  
**MCP Integration:** ✅ Connected via bigtorig-hub  
**Flutter Integration:** 📋 Pending Implementation
