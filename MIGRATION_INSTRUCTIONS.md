# OAuth Database Migration Instructions

## Run This Migration on Railway

**Via Railway Dashboard:**
1. Go to Railway → Your Project → PostgreSQL
2. Click "Query" tab
3. Copy and paste this SQL:

```sql
-- Migration: Add OAuth support to tenants table

-- Add OAuth token columns
ALTER TABLE tenants 
ADD COLUMN IF NOT EXISTS oauth_access_token VARCHAR(500),
ADD COLUMN IF NOT EXISTS oauth_refresh_token VARCHAR(500),
ADD COLUMN IF NOT EXISTS oauth_token_expires_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS oauth_scopes VARCHAR(200);

-- Add installation tracking columns
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS installation_id VARCHAR(100) UNIQUE,
ADD COLUMN IF NOT EXISTS installed_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS installation_status VARCHAR(20) DEFAULT 'pending';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tenants_installation_id ON tenants(installation_id);
CREATE INDEX IF NOT EXISTS idx_tenants_subdomain ON tenants(zendesk_subdomain);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(installation_status);
```

4. Click "Run Query"
5. Verify: Run `SELECT * FROM tenants LIMIT 1;` to see new columns

## Verify Migration

Check that these columns exist:
- oauth_access_token
- oauth_refresh_token  
- oauth_token_expires_at
- oauth_scopes
- installation_id
- installed_at
- installation_status

## After Migration

Railway will automatically detect the code changes and redeploy with OAuth endpoints active.

Check logs for:
```
INFO:     Application startup complete.
```

Then test OAuth endpoint:
```bash
curl https://web-production-ccebe.up.railway.app/v1/oauth/status
```

Should return list of tenants (currently empty or with existing tenant).
