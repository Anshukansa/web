import hashlib
import hmac
import time
from functools import wraps
from flask import request, abort, g, current_app, redirect, url_for

def verify_telegram_auth(f):
    """Decorator to verify Telegram authentication from URL parameters."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get required parameters from URL
        user_id = request.args.get('user_id')
        user_name = request.args.get('user_name')
        timestamp = request.args.get('timestamp')
        signature = request.args.get('signature')
        
        # Verify all required parameters are present
        if not all([user_id, user_name, timestamp, signature]):
            return redirect(url_for('main.access_denied'))
        
        # Check if link has expired (30 minutes)
        now = int(time.time())
        if now - int(timestamp) > 1800:  # 30 minutes expiration
            return redirect(url_for('main.access_denied', reason='expired'))
        
        # Rebuild the query string for verification
        data = {
            'user_id': user_id,
            'user_name': user_name,
            'timestamp': timestamp
        }
        
        # Create query string in the same order
        query_params = []
        for key in sorted(data.keys()):
            query_params.append(f"{key}={data[key]}")
        query_string = "&".join(query_params)
        
        # Generate expected signature
        expected_signature = hmac.new(
            current_app.config['SECRET_KEY'].encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures using constant-time comparison
        if not hmac.compare_digest(signature, expected_signature):
            return redirect(url_for('main.access_denied', reason='invalid'))
        
        # Store validated user info in Flask g object for the view function
        g.telegram_user_id = user_id
        g.telegram_user_name = user_name
        
        return f(*args, **kwargs)
    return decorated_function