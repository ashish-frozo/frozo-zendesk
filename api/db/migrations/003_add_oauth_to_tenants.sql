-- Migration: Add OAuth support to tenants table
-- This enables per-tenant Zendesk OAuth tokens for marketplace deployment

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

-- Add comment explaining the schema
COMMENT ON COLUMN tenants.oauth_access_token IS 'Zendesk OAuth access token (encrypted)';
COMMENT ON COLUMN tenants.oauth_refresh_token IS 'Zendesk OAuth refresh token (encrypted)';
COMMENT ON COLUMN tenants.oauth_token_expires_at IS 'When the access token expires (UTC)';
COMMENT ON COLUMN tenants.oauth_scopes IS 'Granted OAuth scopes (e.g., "read write")';
COMMENT ON COLUMN tenants.installation_id IS 'Zendesk app installation GUID';
COMMENT ON COLUMN tenants.installation_status IS 'Installation status: pending, active, suspended';
