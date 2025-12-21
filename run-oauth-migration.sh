#!/bin/bash
# Run OAuth database migration on Railway
# This adds OAuth columns to the tenants table

echo "Running OAuth migration on Railway..."

# Read the migration file and execute via Railway CLI
railway run --service escalatesafe-api -- bash -c "
  export PGPASSWORD=\$DATABASE_PASSWORD
  psql \$DATABASE_URL < api/db/migrations/003_add_oauth_to_tenants.sql
"

echo "Migration complete! Check for errors above."
echo "Verifying columns were added..."

railway run --service escalatesafe-api -- bash -c "
  export PGPASSWORD=\$DATABASE_PASSWORD
  psql \$DATABASE_URL -c \"\\d tenants\"
"
