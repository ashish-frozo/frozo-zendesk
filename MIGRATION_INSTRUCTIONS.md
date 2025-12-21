# Run OAuth Migration - Simple Instructions

## Quick Method: Python Script

1. **Get DATABASE_URL from Railway:**
   - Go to Railway Dashboard
   - Click on PostgreSQL service
   - Go to "Variables" tab
   - Copy the `DATABASE_URL` value

2. **Run the migration script:**
   ```bash
   cd /Users/ashishdhiman/WORK/Frozo-projects/frozo-zendesk
   python run_migration.py
   ```

3. **When prompted, paste your DATABASE_URL**

4. **Done!** The script will:
   - Connect to Railway database
   - Add OAuth columns
   - Verify they were added
   - Show you the new columns

## Expected Output:

```
Connecting to containers-us-west-xxx.railway.app:5432/railway...
Running OAuth migration...
✅ Migration complete!

Verifying new columns...

New columns:
  - installation_id: character varying
  - installation_status: character varying
  - installed_at: timestamp without time zone
  - oauth_access_token: character varying
  - oauth_refresh_token: character varying
  - oauth_scopes: character varying  
  - oauth_token_expires_at: timestamp without time zone

✅ All done! OAuth columns added successfully.
```

## Troubleshooting

**If you see "connection refused":**
- Check DATABASE_URL is correct
- Make sure you copied the entire URL including `postgresql://`

**If you see "permission denied":**
- The Railway database user should have ALTER TABLE permissions (it should by default)

**If columns already exist:**
- The script uses `IF NOT EXISTS` so it's safe to run multiple times
- You'll see no errors, just "Migration complete!"

## After Migration

1. Check Railway logs - backend should still be running fine
2. Test OAuth endpoint:
   ```bash
   curl https://web-production-ccebe.up.railway.app/v1/oauth/status
   ```
   Should return: `{"total_tenants": X, "tenants": [...]}`

3. Ready for Phase 4 (Frontend updates)!
