"""
Run OAuth migration on Railway database.
Connects directly to PostgreSQL and adds OAuth columns.
"""

import os
import psycopg2
from urllib.parse import urlparse

# Get DATABASE_URL from Railway
# You can get this from Railway dashboard -> Variables -> DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL") or input("Paste DATABASE_URL from Railway: ")

# Parse the URL
result = urlparse(DATABASE_URL)
username = result.username
password = result.password
database = result.path[1:]
hostname = result.hostname
port = result.port

print(f"Connecting to {hostname}:{port}/{database}...")

# Connect to database
conn = psycopg2.connect(
    database=database,
    user=username,
    password=password,
    host=hostname,
    port=port
)

conn.autocommit = True
cursor = conn.cursor()

print("Running OAuth migration...")

# Read and execute migration
with open('api/db/migrations/003_add_oauth_to_tenants.sql', 'r') as f:
    migration_sql = f.read()
    cursor.execute(migration_sql)

print("✅ Migration complete!")

# Verify columns were added
print("\nVerifying new columns...")
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'tenants' 
    AND column_name LIKE 'oauth%' OR column_name LIKE 'installation%'
    ORDER BY column_name;
""")

columns = cursor.fetchall()
print("\nNew columns:")
for col in columns:
    print(f"  - {col[0]}: {col[1]}")

cursor.close()
conn.close()

print("\n✅ All done! OAuth columns added successfully.")
