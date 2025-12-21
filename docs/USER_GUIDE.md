# User Guide

How to use EscalateSafe to safely escalate support tickets to engineering.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your First Escalation](#creating-your-first-escalation)
3. [Understanding PII Detection](#understanding-pii-detection)
4. [Reviewing & Approving](#reviewing--approving)
5. [Managing Settings](#managing-settings)
6. [Best Practices](#best-practices)
7. [FAQ](#faq)

---

## Getting Started

### Accessing the App

1. **Open any Zendesk ticket**
2. **Look for "EscalateSafe"** in the right sidebar
3. If not visible, click **Apps** button and select **EscalateSafe**

The app will load showing the main interface with two options:
- 🚀 **Generate Engineering Pack** - Create escalation
- ⚙️ **Settings** - Configure Jira/Slack

---

## Creating Your First Escalation

### Step 1: Generate Pack

1. **Open a ticket** that needs engineering escalation
2. **Click "🚀 Generate Engineering Pack"**
3. **Wait** while the app:
   - Fetches ticket content
   - Analyzes for PII
   - Redacts sensitive information
   - Generates preview

**What happens:**
```
Processing... (5-10 seconds)
↓
✓ Preview Generated
```

### Step 2: Review Preview

You'll see a preview showing:

```
URGENT: Customer cannot access their account

Customer Details:
- Name: [NAME_REDACTED]
- Email: [EMAIL_REDACTED]
- Phone: [PHONE_NUMBER_REDACTED]

Issue Description:
The customer reports they cannot log in...

API Key: [API_KEY_REDACTED]

Credit card: [CREDIT_CARD_REDACTED]
```

**PII Detected section shows:**
- `EMAIL_ADDRESS: 2` - Found 2 email addresses
- `PHONE_NUMBER: 1` - Found 1 phone number
- `NAME: 1` - Found 1 person name
- `API_KEY: 1` - Found 1 API key
- `CREDIT_CARD: 1` - Found 1 credit card

**Total Redactions: 6**

### Step 3: Approve & Export

If the preview looks good:

1. **Click "✓ Approve & Create Jira Issue"**
2. **Wait** for creation
3. **Success!** You'll see:
   ```
   ✅ Successfully Exported!
   
   Jira Issue: SCRUM-123 (clickable link)
   
   [Create Another]
   ```

4. **Click the Jira link** to open the issue in Jira
5. **Or click "Create Another"** to escalate another ticket

---

## Understanding PII Detection

### What Gets Detected

**Personal Information:**
- ✅ Names (John Doe, Sarah Smith)
- ✅ Email addresses
- ✅ Phone numbers (all formats)
  - +1-555-123-4567
  - (555) 987-6543
  - 555.123.4567
- ✅ Locations/addresses

**Financial Data:**
- ✅ Credit cards (all formats)
  - 4532-1234-5678-9012
  - 4532 1234 5678 9012
  - 4532123456789012

**Technical Secrets:**
- ✅ API keys
- ✅ Bearer tokens
- ✅ Long random strings

### Redaction Format

Each detected entity is replaced with:
```
[ENTITY_TYPE_REDACTED]
```

Examples:
- Name → `[NAME_REDACTED]` or `[PERSON_REDACTED]`
- Email → `[EMAIL_REDACTED]`
- Phone → `[PHONE_NUMBER_REDACTED]`
- Credit Card → `[CREDIT_CARD_REDACTED]`
- API Key → `[API_KEY_REDACTED]`

### Confidence Levels

The system uses AI to detect PII with confidence scores:
- **High (0.8-1.0):** Definitely PII → Always redacted
- **Medium (0.6-0.8):** Probably PII → Redacted
- **Low (0.5-0.6):** Maybe PII → Redacted with warning

**Low confidence warnings** appear in logs for admin review.

---

## Reviewing & Approving

### What to Check

Before approving, verify:

1. **✅ All sensitive data redacted**
   - Customer names hidden
   - Email addresses masked
   - Phone numbers removed

2. **✅ Issue still understandable**
   - Engineers can still debug
   - Error messages intact
   - Context preserved

3. **✅ No over-redaction**
   - Product names visible
   - Technical terms intact
   - Error codes readable

### Common Scenarios

**Scenario 1: Customer API Key**
```
Before: "API Key: sk_live_4o4E78g..."
After:  "API Key: [API_KEY_REDACTED]"
✅ Good - Secret protected
```

**Scenario 2: Product Name**
```
Before: "Using Enterprise Pro plan"
After:  "Using Enterprise Pro plan"
✅ Good - Not PII, left intact
```

**Scenario 3: Error Message**
```
Before: "Error: Invalid token 'abc123'"
After:  "Error: Invalid token '[API_KEY_REDACTED]'"
✅ Good - Error preserved, token hidden
```

### When to Cancel

**Cancel and edit ticket if:**
- ❌ Critical context lost
- ❌ Issue becomes unclear
- ❌ Too much redaction for debugging

Then manually sanitize and create Jira issue directly.

---

## Managing Settings

### Accessing Settings

1. **Click "⚙️ Settings"** in the app
2. **Configure Jira** (required for first use)
3. **Configure Slack** (optional)

### Jira Configuration

**Required fields:**
- **Server URL:** `https://yourcompany.atlassian.net`
- **Email:** Your Jira account email
- **API Token:** Generated from Jira
- **Project Key:** e.g., `SCRUM`, `ENG`, `SUP`

**Get Jira API Token:**
1. Go to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Copy and paste into app

**Click "💾 Save Jira"** when done.

### Slack Configuration

**Optional fields:**
- **Webhook URL:** From Slack incoming webhook
- **Channel:** e.g., `#engineering-escalations`

**Get Slack Webhook:**
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create app → Incoming Webhooks
3. Add webhook to workspace
4. Copy URL

**Click "💾 Save Slack"** when done.

### Testing Configuration

Settings are tested when you create your first escalation.

**Jira test:**
- Issue created successfully → ✅ Working
- Error → ❌ Check credentials

**Slack test:**
- Notification sent → ✅ Working
- No notification → ⚠️ Check webhook

---

## Best Practices

### For Support Agents

**Do's:**
- ✅ Review preview before approving
- ✅ Check redactions make sense
- ✅ Add context to ticket before escalating
- ✅ Use descriptive ticket titles

**Don'ts:**
- ❌ Blindly approve without review
- ❌ Share unredacted screenshots externally
- ❌ Override redactions manually
- ❌ Export same ticket multiple times

### For Admins

**Do's:**
- ✅ Train agents on app usage
- ✅ Monitor escalation quality
- ✅ Review low-confidence redactions
- ✅ Update settings as needed

**Don'ts:**
- ❌ Share API tokens publicly
- ❌ Use personal Jira accounts
- ❌ Disable PII detection
- ❌ Ignore security updates

### Privacy Tips

1. **Always review** - Don't auto-approve
2. **Check attachments** - App doesn't redact images (yet)
3. **Be careful with screenshots** - May contain PII
4. **Use internal notes** - For truly sensitive info
5. **Regular audits** - Review exported tickets monthly

---

## FAQ

### General

**Q: How long does it take to create an escalation?**  
A: 10-15 seconds total - 5 sec for PII detection, 5 sec for Jira creation.

**Q: Can I edit the redacted content before exporting?**  
A: Currently no. If you need changes, cancel and edit the source ticket.

**Q: Does it redact attachments?**  
A: Not yet. Images/PDFs are not currently redacted. Coming in v1.1!

**Q: Can I customize what gets redacted?**  
A: Custom patterns coming in v1.1. Contact support for enterprise features.

### Technical

**Q: What happens if Jira is down?**  
A: Export fails with error message. Try again later. Data not lost.

**Q: How is PII detected?**  
A: Uses Microsoft Presidio AI + spaCy NLP + custom patterns.

**Q: Where is my data stored?**  
A: Redacted content only. Original tickets stay in Zendesk. OAuth tokens encrypted in database.

**Q: Is it GDPR compliant?**  
A: Yes. See [SECURITY.md](SECURITY.md) for details.

### Troubleshooting

**Q: App not loading in sidebar?**  
A: Refresh page, check if app is enabled, contact admin.

**Q: "OAuth not configured" error?**  
A: Admin needs to set up OAuth. Using fallback temporarily.

**Q: Jira issue creation failed?**  
A: Check settings, verify API token, ensure project exists.

**Q: No Slack notification?**  
A: Optional feature. Check webhook URL in settings.

---

## Getting Help

**For Users:**
- Check this guide first
- Ask your team admin
- Email: [hello@frozo.ai](mailto:hello@frozo.ai)

**For Admins:**
- See [INSTALLATION.md](INSTALLATION.md)
- Check [API Reference](API.md)
- GitHub Issues: [github.com/ashish-frozo/frozo-zendesk/issues](https://github.com/ashish-frozo/frozo-zendesk/issues)

---

**Happy Escalating! 🚀**
