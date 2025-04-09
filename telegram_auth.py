import hashlib
import hmac
import time
import logging
from functools import wraps
from flask import request, abort, g, current_app, redirect, url_for

# Set up logging
logger = logging.getLogger(__name__)

def verify_telegram_auth(f):
    """Decorator to verify Telegram authentication from URL parameters."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get required parameters from URL
        user_id = request.args.get('user_id')
        user_name = request.args.get('user_name')
        timestamp = request.args.get('timestamp')
        signature = request.args.get('signature')
        
        # Log parameters for debugging
        logger.info(f"Received auth parameters: user_id={user_id}, user_name={user_name}, timestamp={timestamp}")
        
        # Verify all required parameters are present
        if not all([user_id, user_name, timestamp, signature]):
            logger.warning("Missing required parameters")
            return redirect(url_for('main.access_denied'))
        
        # Check if link has expired (30 minutes)
        now = int(time.time())
        if now - int(timestamp) > 1800:  # 30 minutes expiration
            logger.warning(f"Link expired. Current time: {now}, Timestamp: {timestamp}")
            return redirect(url_for('main.access_denied', reason='expired'))
        
        # Rebuild the query string for verification - MUST match the bot's approach exactly
        data = {
            'user_id': user_id,
            'user_name': user_name,
            'timestamp': timestamp
        }
        
        # Create query string in the exact same order as the bot
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
        
        # Log signatures for debugging
        logger.info(f"Query string used for verification: {query_string}")
        logger.info(f"Expected signature: {expected_signature}")
        logger.info(f"Received signature: {signature}")
        
        # Compare signatures using constant-time comparison
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid signature")
            return redirect(url_for('main.access_denied', reason='invalid'))
        
        # Store validated user info in Flask g object for the view function
        g.telegram_user_id = user_id
        g.telegram_user_name = user_name
        
        logger.info(f"Authentication successful for user: {user_name}")
        return f(*args, **kwargs)
    return decorated_function