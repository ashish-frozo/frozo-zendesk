from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, 
            static_folder='static',
            template_folder='.')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/security')
def security():
    return render_template('security.html')

@app.route('/api/contact', methods=['POST'])
def contact():
    """Handle contact form submissions"""
    data = request.json
    
    # Here you can:
    # 1. Send email via SendGrid/AWS SES
    # 2. Save to database
    # 3. Send to Slack webhook
    # 4. Create ticket in your CRM
    
    # For now, just log and return success
    print(f"Contact form submission: {data}")
    
    # TODO: Add email sending logic
    # send_email(
    #     to="hello@frozo.ai",
    #     subject=f"Contact from {data.get('name')}",
    #     body=data.get('message')
    # )
    
    return jsonify({
        "success": True,
        "message": "Thank you! We'll get back to you within 24 hours."
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "escalatesafe-website"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
