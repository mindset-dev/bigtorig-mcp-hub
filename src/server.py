#!/usr/bin/env python3
"""
bigtorig-mcp-hub Server - Phase 2

MCP server providing access to Hostinger infrastructure services:
- Postgres (Supabase)
- Qdrant (Vector Database)
- Neo4j (Graph Database)
"""

import os
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
import mysql.connector
from mysql.connector import Error as MySQLError

# Initialize FastMCP server
mcp = FastMCP("bigtorig-mcp-hub")

# Database connection globals (lazy initialization)
_postgres_conn = None
_qdrant_client = None
_neo4j_driver = None
_mysql_conn = None


def get_postgres_connection():
    """Get or create Postgres connection."""
    global _postgres_conn
    if _postgres_conn is None or _postgres_conn.closed:
        _postgres_conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "172.23.0.1"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB", "postgres"),
        )
    return _postgres_conn


def get_qdrant_client():
    """Get or create Qdrant client."""
    global _qdrant_client
    if _qdrant_client is None:
        api_key = os.getenv("QDRANT_API_KEY")
        _qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "172.23.0.1"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            api_key=api_key if api_key else None,
        )
    return _qdrant_client


def get_neo4j_driver():
    """Get or create Neo4j driver."""
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://172.23.0.1:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD")),
        )
    return _neo4j_driver


def get_mysql_connection():
    """Get or create MySQL connection."""
    global _mysql_conn
    if _mysql_conn is None or not _mysql_conn.is_connected():
        _mysql_conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "172.23.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "maui_user"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE", "maui_app_db"),
        )
    return _mysql_conn


# =============================================================================
# FOUNDATIONAL TOOLS
# =============================================================================


@mcp.tool()
def health_check() -> dict:
    """
    Check if the MCP server is running and healthy.

    Returns:
        dict: Status information about the server
    """
    return {
        "status": "healthy",
        "service": "bigtorig-mcp-hub",
        "version": "0.2.0",
        "phase": "2 - Database Integration",
        "message": "MCP hub is operational",
    }


@mcp.tool()
def list_services() -> dict:
    """
    List all available infrastructure services and their tools.

    Returns:
        dict: Information about available services and tools
    """
    services = {
        "postgres": {
            "name": "Supabase Postgres",
            "endpoint": f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}",
            "status": "connected",
            "tools": [
                "postgres_list_databases",
                "postgres_create_database",
                "postgres_query",
                "postgres_list_tables",
                "postgres_describe_table",
            ],
        },
        "mysql": {
            "name": "MySQL Database (maui_app_db)",
            "endpoint": f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}",
            "status": "connected",
            "tools": ["mysql_query", "mysql_list_tables", "mysql_describe_table"],
        },
        "qdrant": {
            "name": "Qdrant Vector Database",
            "endpoint": f"{os.getenv('QDRANT_HOST')}:{os.getenv('QDRANT_PORT')}",
            "status": "connected",
            "tools": ["qdrant_search", "qdrant_list_collections", "qdrant_collection_info"],
        },
        "neo4j": {
            "name": "Neo4j Graph Database",
            "endpoint": os.getenv("NEO4J_URI"),
            "status": "connected",
            "tools": ["neo4j_query", "neo4j_list_nodes", "neo4j_get_relationships"],
        },
    }

    return {
        "total_services": len(services),
        "total_tools": sum(len(s["tools"]) for s in services.values()),
        "services": services,
    }


# =============================================================================
# POSTGRES TOOLS
# =============================================================================


@mcp.tool()
def postgres_query(sql: str, limit: int = 100) -> dict:
    """
    Execute a SQL query against the Supabase Postgres database.

    Args:
        sql: SQL query to execute (SELECT statements only for safety)
        limit: Maximum number of rows to return (default: 100, max: 1000)

    Returns:
        dict: Query results with rows and metadata

    Equivalent command:
    psql -h {POSTGRES_HOST} -U {POSTGRES_USER} -d {POSTGRES_DB} -c "SELECT ..."
    """
    # Safety check: only allow SELECT statements
    if not sql.strip().upper().startswith("SELECT"):
        return {
            "error": "Only SELECT queries are allowed for safety",
            "tip": "Use postgres_list_tables() to see available tables",
        }

    # Enforce limit
    limit = min(limit, 1000)

    try:
        conn = get_postgres_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Add LIMIT if not present
            if "LIMIT" not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT {limit}"

            cur.execute(sql)
            rows = cur.fetchall()

            return {
                "success": True,
                "row_count": len(rows),
                "rows": [dict(row) for row in rows],
                "query": sql,
            }
    except Exception as e:
        return {"success": False, "error": str(e), "query": sql}


@mcp.tool()
def postgres_list_databases() -> dict:
    """
    List all databases on the Postgres server.

    Returns:
        dict: List of all databases with size and owner information

    Equivalent command:
    psql -h {POSTGRES_HOST} -U {POSTGRES_USER} -c "\\l"
    """
    try:
        conn = get_postgres_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all databases
            cur.execute(
                """
                SELECT
                    datname as database_name,
                    pg_catalog.pg_get_userbyid(datdba) as owner,
                    pg_encoding_to_char(encoding) as encoding,
                    datcollate as collate,
                    datctype as ctype
                FROM pg_catalog.pg_database
                ORDER BY datname
            """
            )

            databases = cur.fetchall()

            return {
                "success": True,
                "database_count": len(databases),
                "databases": [dict(db) for db in databases],
                "current_database": os.getenv("POSTGRES_DB", "postgres"),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def postgres_create_database(database_name: str, owner: Optional[str] = None) -> dict:
    """
    Create a new Postgres database.

    Args:
        database_name: Name of the database to create
        owner: Optional owner username (defaults to current user)

    Returns:
        dict: Creation status

    Equivalent command:
    psql -h {POSTGRES_HOST} -U {POSTGRES_USER} -c "CREATE DATABASE database_name"
    """
    try:
        # Validate database name (alphanumeric and underscores only)
        import re

        if not re.match(r"^[a-zA-Z0-9_]+$", database_name):
            return {
                "success": False,
                "error": "Database name must contain only letters, numbers, and underscores",
                "database_name": database_name,
            }

        conn = get_postgres_connection()
        # Must be outside transaction for CREATE DATABASE
        conn.autocommit = True

        with conn.cursor() as cur:
            # Check if database already exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))

            if cur.fetchone():
                return {
                    "success": False,
                    "error": f"Database '{database_name}' already exists",
                    "database_name": database_name,
                    "tip": "Use postgres_list_databases() to see all databases",
                }

            # Create the database
            if owner:
                # Validate owner exists
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (owner,))
                if not cur.fetchone():
                    return {
                        "success": False,
                        "error": f"Owner '{owner}' does not exist",
                        "database_name": database_name,
                    }
                # Use identifier quoting for safety
                from psycopg2 import sql

                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(database_name), sql.Identifier(owner)
                    )
                )
            else:
                from psycopg2 import sql

                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

        # Reset autocommit
        conn.autocommit = False

        return {
            "success": True,
            "message": f"Database '{database_name}' created successfully",
            "database_name": database_name,
            "owner": owner or os.getenv("POSTGRES_USER", "postgres"),
            "tip": "To connect to this database, update POSTGRES_DB environment variable",
        }
    except Exception as e:
        # Reset autocommit on error
        try:
            conn.autocommit = False
        except:
            pass
        return {
            "success": False,
            "error": str(e),
            "database_name": database_name,
        }


@mcp.tool()
def postgres_list_tables(schema: str = "public") -> dict:
    """
    List all tables in the Postgres database.

    Args:
        schema: Schema name (default: public)

    Returns:
        dict: List of tables with row counts

    Equivalent command:
    psql -h {POSTGRES_HOST} -U {POSTGRES_USER} -d {POSTGRES_DB} -c "\\dt"
    """
    try:
        conn = get_postgres_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get tables - simplified query without size calculation
            cur.execute(
                """
                SELECT
                    schemaname,
                    tablename
                FROM pg_tables
                WHERE schemaname = %s
                ORDER BY tablename
            """,
                (schema,),
            )

            tables = cur.fetchall()

            return {
                "success": True,
                "schema": schema,
                "table_count": len(tables),
                "tables": [dict(t) for t in tables],
            }
    except Exception as e:
        return {"success": False, "error": str(e), "schema": schema}


@mcp.tool()
def postgres_describe_table(table_name: str, schema: str = "public") -> dict:
    """
    Get detailed schema information for a specific table.

    Args:
        table_name: Name of the table
        schema: Schema name (default: public)

    Returns:
        dict: Table schema with columns, types, and constraints

    Equivalent command:
    psql -h {POSTGRES_HOST} -U {POSTGRES_USER} -d {POSTGRES_DB} -c "\\d table_name"
    """
    try:
        conn = get_postgres_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get column information
            cur.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """,
                (schema, table_name),
            )

            columns = cur.fetchall()

            # Get row count
            cur.execute(f"SELECT COUNT(*) as count FROM {schema}.{table_name}")
            row_count = cur.fetchone()["count"]

            return {
                "success": True,
                "schema": schema,
                "table": table_name,
                "row_count": row_count,
                "columns": [dict(c) for c in columns],
            }
    except Exception as e:
        return {"success": False, "error": str(e), "table": table_name}


# =============================================================================
# MYSQL TOOLS
# =============================================================================


@mcp.tool()
def mysql_query(sql: str, limit: int = 100) -> dict:
    """
    Execute a SQL query against the MySQL database.

    Args:
        sql: SQL query to execute (SELECT statements only for safety)
        limit: Maximum number of rows to return (default: 100, max: 1000)

    Returns:
        dict: Query results with rows and metadata

    Equivalent command:
    mysql -h {MYSQL_HOST} -u {MYSQL_USER} -p {MYSQL_DATABASE} -e "SELECT ..."
    """
    # Safety check: only allow SELECT statements
    if not sql.strip().upper().startswith("SELECT"):
        return {
            "error": "Only SELECT queries are allowed for safety",
            "tip": "Use mysql_list_tables() to see available tables",
        }

    # Enforce limit
    limit = min(limit, 1000)

    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        # Add LIMIT if not present
        if "LIMIT" not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT {limit}"

        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()

        return {
            "success": True,
            "row_count": len(rows),
            "rows": rows,
            "query": sql,
        }
    except MySQLError as e:
        return {"success": False, "error": str(e), "query": sql}


@mcp.tool()
def mysql_list_tables(database: Optional[str] = None) -> dict:
    """
    List all tables in the MySQL database.

    Args:
        database: Database name (default: from MYSQL_DATABASE env var)

    Returns:
        dict: List of tables

    Equivalent command:
    mysql -h {MYSQL_HOST} -u {MYSQL_USER} -p -e "SHOW TABLES"
    """
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        db_name = database or os.getenv("MYSQL_DATABASE", "maui_app_db")

        # Get tables
        cursor.execute(f"SHOW TABLES FROM {db_name}")
        tables = cursor.fetchall()

        # Extract table names from the result
        table_key = f"Tables_in_{db_name}"
        table_list = [table[table_key] for table in tables]

        cursor.close()

        return {
            "success": True,
            "database": db_name,
            "table_count": len(table_list),
            "tables": table_list,
        }
    except MySQLError as e:
        return {"success": False, "error": str(e), "database": db_name}


@mcp.tool()
def mysql_describe_table(table_name: str, database: Optional[str] = None) -> dict:
    """
    Get detailed schema information for a specific MySQL table.

    Args:
        table_name: Name of the table
        database: Database name (default: from MYSQL_DATABASE env var)

    Returns:
        dict: Table schema with columns, types, and constraints

    Equivalent command:
    mysql -h {MYSQL_HOST} -u {MYSQL_USER} -p -e "DESCRIBE table_name"
    """
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        db_name = database or os.getenv("MYSQL_DATABASE", "maui_app_db")

        # Get column information
        cursor.execute(f"DESCRIBE {db_name}.{table_name}")
        columns = cursor.fetchall()

        # Get row count
        cursor.execute(f"SELECT COUNT(*) as count FROM {db_name}.{table_name}")
        row_count = cursor.fetchone()["count"]

        cursor.close()

        return {
            "success": True,
            "database": db_name,
            "table": table_name,
            "row_count": row_count,
            "columns": columns,
        }
    except MySQLError as e:
        return {"success": False, "error": str(e), "table": table_name}


# =============================================================================
# QDRANT TOOLS
# =============================================================================


@mcp.tool()
def qdrant_search(collection: str, query_text: str, limit: int = 5) -> dict:
    """
    Perform semantic vector search in a Qdrant collection.

    Note: This is a simplified version. For actual vector search, you need
    to embed the query_text first using an embedding model.

    Args:
        collection: Name of the collection to search
        query_text: Text to search for (will be embedded)
        limit: Maximum number of results (default: 5)

    Returns:
        dict: Search results with scores

    Equivalent command:
    curl http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection}/points/search
    """
    try:
        client = get_qdrant_client()

        # NOTE: In production, you'd embed query_text here with an actual model
        # For now, return collection info as we can't embed without a model
        collection_info = client.get_collection(collection_name=collection)

        return {
            "success": True,
            "collection": collection,
            "message": "Vector search requires embedding model (not implemented yet)",
            "collection_info": {
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
            },
            "tip": "Use qdrant_list_collections() to see available collections",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "collection": collection}


@mcp.tool()
def qdrant_list_collections() -> dict:
    """
    List all Qdrant vector collections.

    Returns:
        dict: List of collections with metadata

    Equivalent command:
    curl http://{QDRANT_HOST}:{QDRANT_PORT}/collections
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections()

        collection_details = []
        for coll in collections.collections:
            try:
                info = client.get_collection(collection_name=coll.name)
                collection_details.append(
                    {
                        "name": coll.name,
                        "vectors_count": info.vectors_count,
                        "points_count": info.points_count,
                        "status": info.status,
                    }
                )
            except:
                collection_details.append({"name": coll.name, "status": "error"})

        return {
            "success": True,
            "collection_count": len(collection_details),
            "collections": collection_details,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def qdrant_collection_info(collection: str) -> dict:
    """
    Get detailed information about a specific Qdrant collection.

    Args:
        collection: Name of the collection

    Returns:
        dict: Collection metadata and statistics

    Equivalent command:
    curl http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection}
    """
    try:
        client = get_qdrant_client()
        info = client.get_collection(collection_name=collection)

        return {
            "success": True,
            "collection": collection,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
            "config": {
                "params": str(info.config.params) if info.config else None,
                "optimizer_config": str(info.config.optimizer_config) if info.config else None,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e), "collection": collection}


# =============================================================================
# NEO4J TOOLS
# =============================================================================


@mcp.tool()
def neo4j_query(cypher: str, limit: int = 100) -> dict:
    """
    Execute a Cypher query against the Neo4j graph database.

    Args:
        cypher: Cypher query to execute (READ operations only for safety)
        limit: Maximum number of results (default: 100, max: 1000)

    Returns:
        dict: Query results

    Equivalent command:
    cypher-shell -a {NEO4J_URI} -u {NEO4J_USER} -p {NEO4J_PASSWORD} "MATCH ..."
    """
    # Safety check: only allow read operations
    cypher_upper = cypher.strip().upper()
    if not any(
        cypher_upper.startswith(cmd) for cmd in ["MATCH", "RETURN", "WITH", "UNWIND", "CALL"]
    ):
        return {
            "error": "Only read queries are allowed (MATCH, RETURN, etc.)",
            "tip": "Use neo4j_list_nodes() to explore the graph",
        }

    # Enforce limit
    limit = min(limit, 1000)

    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            # Add LIMIT if not present
            if "LIMIT" not in cypher_upper:
                cypher = f"{cypher.rstrip(';')} LIMIT {limit}"

            result = session.run(cypher)
            records = [dict(record) for record in result]

            return {
                "success": True,
                "record_count": len(records),
                "records": records,
                "query": cypher,
            }
    except Exception as e:
        return {"success": False, "error": str(e), "query": cypher}


@mcp.tool()
def neo4j_list_nodes(label: Optional[str] = None, limit: int = 100) -> dict:
    """
    List nodes in the Neo4j graph database.

    Args:
        label: Optional node label to filter by (e.g., "Person", "Movie")
        limit: Maximum number of nodes to return (default: 100)

    Returns:
        dict: List of nodes with their properties

    Equivalent command:
    cypher-shell -a {NEO4J_URI} -u {NEO4J_USER} "MATCH (n) RETURN n LIMIT 100"
    """
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            if label:
                query = f"MATCH (n:{label}) RETURN n, labels(n) as labels LIMIT {limit}"
            else:
                query = f"MATCH (n) RETURN n, labels(n) as labels LIMIT {limit}"

            result = session.run(query)
            nodes = []
            for record in result:
                node = dict(record["n"])
                node["_labels"] = record["labels"]
                nodes.append(node)

            return {
                "success": True,
                "node_count": len(nodes),
                "label_filter": label,
                "nodes": nodes,
            }
    except Exception as e:
        return {"success": False, "error": str(e), "label": label}


@mcp.tool()
def neo4j_get_relationships(node_label: Optional[str] = None, limit: int = 50) -> dict:
    """
    Get relationships in the Neo4j graph.

    Args:
        node_label: Optional node label to filter relationships
        limit: Maximum number of relationships to return (default: 50)

    Returns:
        dict: List of relationships with start and end nodes

    Equivalent command:
    cypher-shell -a {NEO4J_URI} -u {NEO4J_USER} "MATCH (a)-[r]->(b) RETURN a,r,b LIMIT 50"
    """
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            if node_label:
                query = f"""
                MATCH (a:{node_label})-[r]->(b)
                RETURN a, type(r) as rel_type, b, labels(a) as start_labels, labels(b) as end_labels
                LIMIT {limit}
                """
            else:
                query = f"""
                MATCH (a)-[r]->(b)
                RETURN a, type(r) as rel_type, b, labels(a) as start_labels, labels(b) as end_labels
                LIMIT {limit}
                """

            result = session.run(query)
            relationships = []
            for record in result:
                relationships.append(
                    {
                        "start_node": dict(record["a"]),
                        "start_labels": record["start_labels"],
                        "relationship_type": record["rel_type"],
                        "end_node": dict(record["b"]),
                        "end_labels": record["end_labels"],
                    }
                )

            return {
                "success": True,
                "relationship_count": len(relationships),
                "relationships": relationships,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SERVER STARTUP
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔌 bigtorig-mcp-hub - Phase 2: Database Integration")
    print("=" * 70)
    print(f"📊 Total tools: 16")
    print(f"   • Foundational: 2 tools (health_check, list_services)")
    print(
        f"   • Postgres: 5 tools (list_databases, create_database, query, list_tables, describe_table)"
    )
    print(f"   • MySQL: 3 tools (query, list_tables, describe_table)")
    print(f"   • Qdrant: 3 tools (search, list_collections, collection_info)")
    print(f"   • Neo4j: 3 tools (query, list_nodes, get_relationships)")
    print()
    print(f"🔗 Database connections:")
    print(f"   • Postgres: {os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}")
    print(f"   • MySQL: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}")
    print(f"   • Qdrant: {os.getenv('QDRANT_HOST')}:{os.getenv('QDRANT_PORT')}")
    print(f"   • Neo4j: {os.getenv('NEO4J_URI')}")
    print("=" * 70)
    print("🚀 Starting MCP server on http://0.0.0.0:8000/sse")
    print("=" * 70)

    # Run with SSE transport for HTTP access
    mcp.run(transport="sse", port=8000, host="0.0.0.0")
