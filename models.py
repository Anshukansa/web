from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Preference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    suburb = db.Column(db.String(100), nullable=True)
    notification_mode = db.Column(db.String(20), nullable=False)
    
    # New admin-editable fields
    user_id = db.Column(db.String(64), nullable=True)
    user_name = db.Column(db.String(100), nullable=True)
    activation_status = db.Column(db.Boolean, default=True)
    expiry_date = db.Column(db.Date, nullable=True)
    fixed_lat = db.Column(db.String(20), nullable=True)
    fixed_lon = db.Column(db.String(20), nullable=True)
    
    # Relationship with product preferences
    products = db.relationship('ProductPreference', backref='preference', lazy=True, cascade="all, delete-orphan")
    
    # Edit token for non-authenticated edits
    edit_token = db.Column(db.String(64), unique=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(Preference, self).__init__(**kwargs)
        self.edit_token = secrets.token_urlsafe(32)
    
    def as_dict(self):
        return {
            'id': self.id,
            'location': self.location,
            'suburb': self.suburb,
            'notification_mode': self.notification_mode,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'activation_status': self.activation_status,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'fixed_lat': self.fixed_lat,
            'fixed_lon': self.fixed_lon,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'products': [product.as_dict() for product in self.products]
        }

class ProductPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    preference_id = db.Column(db.Integer, db.ForeignKey('preference.id'), nullable=False)
    
    # Product information
    product_name = db.Column(db.String(100), nullable=False)
    max_price = db.Column(db.Integer, nullable=False)
    is_preferred = db.Column(db.Boolean, default=True)
    
    def as_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'max_price': self.max_price,
            'is_preferred': self.is_preferred
        }

# Predefined list of iPhone models
IPHONE_MODELS = [
    "iPhone 16 Pro Max", "iPhone 16 Pro", "iPhone 16 Plus", "iPhone 16",
    "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15 Plus", "iPhone 15",
    "iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14 Plus", "iPhone 14",
    "iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13", "iPhone 13 Mini",
    "iPhone 12 Pro Max", "iPhone 12 Pro", "iPhone 12", "iPhone 12 Mini",
    "iPhone 11 Pro Max", "iPhone 11 Pro", "iPhone 11",
    "iPhone XS Max", "iPhone XS", "iPhone XR", "iPhone X",
    "iPhone SE (2022)", "iPhone SE (2020)"
]

# Default max prices (matched with the Excel file)
DEFAULT_PRICES = {
    "iPhone 16 Pro Max": 900, "iPhone 16 Pro": 800, "iPhone 16 Plus": 700, "iPhone 16": 650,
    "iPhone 15 Pro Max": 900, "iPhone 15 Pro": 800, "iPhone 15 Plus": 700, "iPhone 15": 650,
    "iPhone 14 Pro Max": 750, "iPhone 14 Pro": 650, "iPhone 14 Plus": 550, "iPhone 14": 500,
    "iPhone 13 Pro Max": 600, "iPhone 13 Pro": 550, "iPhone 13": 450, "iPhone 13 Mini": 400,
    "iPhone 12 Pro Max": 500, "iPhone 12 Pro": 450, "iPhone 12": 350, "iPhone 12 Mini": 300,
    "iPhone 11 Pro Max": 400, "iPhone 11 Pro": 350, "iPhone 11": 250,
    "iPhone XS Max": 300, "iPhone XS": 250, "iPhone XR": 200, "iPhone X": 200,
    "iPhone SE (2022)": 150, "iPhone SE (2020)": 100
}

# Default keywords and excluded words
DEFAULT_KEYWORDS = ["iphone"]
DEFAULT_EXCLUDED_WORDS = ['warranty', 'controller', 'for', 'stand', 'car', 'names', 'stereo', 'LCD', 'C@$h', 'Ca$h', 'shop']