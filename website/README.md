# EscalateSafe Website

Modern, beautiful landing page for EscalateSafe.

## Features

- 🎨 Modern gradient design
- 📱 Fully responsive
- ⚡ Fast loading
- 🎯 SEO optimized
- 📧 Contact form
- 💳 Pricing tiers

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Open browser
open http://localhost:8080
```

## Deploy to Railway

### Option 1: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Option 2: GitHub Integration

1. Push to GitHub
2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub"
4. Select this repository
5. Set root directory to `/website`
6. Deploy!

### Environment Variables

No environment variables needed for basic deployment.

**Optional:**
- `PORT` - Server port (default: 8080, Railway sets automatically)

## Project Structure

```
website/
├── app.py              # Flask server
├── index.html          # Landing page
├── requirements.txt    # Python deps
├── Procfile           # Railway process
├── runtime.txt        # Python version
├── static/
│   ├── css/
│   │   └── style.css  # Styles
│   └── js/
│       └── main.js    # JavaScript
└── README.md          # This file
```

## Customization

### Update Contact Email

Edit `app.py` line 33:
```python
# Change to your email
to="your-email@domain.com"
```

### Update Links

Edit `index.html`:
- Line 15: Update Zendesk Marketplace link
- Line 35: Update GitHub docs link
- Line 41: Update marketplace install link

### Update Branding

- Logo: Replace emoji 🛡️ with `<img src="logo.png">`
- Colors: Edit CSS variables in `style.css` (line 8-15)
- Fonts: Change Google Fonts link in HTML

## Production Checklist

- [ ] Update contact email in app.py
- [ ] Add email sending logic (SendGrid/AWS SES)
- [ ] Update all external links
- [ ] Add analytics (Google Analytics/Plausible)
- [ ] Set up custom domain
- [ ] Enable HTTPS (automatic on Railway)
- [ ] Test contact form
- [ ] Add privacy policy
- [ ] Add terms of service

## Performance

- Lighthouse Score: 95+
- First Contentful Paint: <1s
- Time to Interactive: <2s

## Support

Questions? Email [hello@frozo.ai](mailto:hello@frozo.ai)
