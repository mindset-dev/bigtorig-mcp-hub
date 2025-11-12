#!/usr/bin/env python3
"""Test script to create affirmation_app database using MCP tools"""

import os
import psycopg2
from psycopg2 import sql

# Set environment variables (read from K8s secrets)
os.environ["POSTGRES_HOST"] = "82.25.116.252"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_USER"] = "postgres"
os.environ["POSTGRES_DB"] = "postgres"

# Get password from user
password = os.getenv("POSTGRES_PASSWORD")
if not password or password == "YOUR_POSTGRES_PASSWORD":
    print("ERROR: POSTGRES_PASSWORD not set or still placeholder")
    print("Please set POSTGRES_PASSWORD environment variable")
    exit(1)

print("=" * 70)
print("Step 1: Listing current databases")
print("=" * 70)

try:
    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=password,
        database=os.environ["POSTGRES_DB"],
    )
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT datname, pg_catalog.pg_get_userbyid(datdba) as owner
            FROM pg_catalog.pg_database
            ORDER BY datname
        """)
        
        databases = cur.fetchall()
        print(f"\nFound {len(databases)} databases:")
        for db in databases:
            print(f"  - {db[0]} (owner: {db[1]})")
    
    print("\n" + "=" * 70)
    print("Step 2: Creating 'affirmation_app' database")
    print("=" * 70)
    
    # Check if database exists
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("affirmation_app",))
        exists = cur.fetchone()
        
        if exists:
            print("\n✓ Database 'affirmation_app' already exists!")
        else:
            # Must use autocommit for CREATE DATABASE
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier("affirmation_app")))
            conn.autocommit = False
            print("\n✓ Database 'affirmation_app' created successfully!")
    
    print("\n" + "=" * 70)
    print("Step 3: Verifying new database")
    print("=" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT datname, pg_catalog.pg_get_userbyid(datdba) as owner
            FROM pg_catalog.pg_database
            WHERE datname = 'affirmation_app'
        """)
        
        db_info = cur.fetchone()
        if db_info:
            print(f"\n✓ Database: {db_info[0]}")
            print(f"  Owner: {db_info[1]}")
    
    conn.close()
    print("\n" + "=" * 70)
    print("SUCCESS: Database setup complete!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    exit(1)
