from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
import os
import sys
import logging

from models import db, User
from forms import LoginForm
from routes.main import main_bp
from routes.admin import admin_bp
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config_class=config.Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Create database tables and admin user
    with app.app_context():
        try:
            # TEMPORARY: Just create the tables directly
            db.create_all()

            # Check and create admin user
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                try:
                    admin = User(username='admin')
                    admin.set_password(app.config['ADMIN_PASSWORD'])
                    db.session.add(admin)
                    db.session.commit()
                    logger.info("Admin user created successfully")
                except Exception as create_error:
                    logger.error(f"Error creating admin user: {create_error}")
                    db.session.rollback()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    return app

# Create app at module level for Gunicorn
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)