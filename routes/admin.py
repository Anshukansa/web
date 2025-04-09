from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
import io
import csv
from datetime import datetime

from models import db, User, Preference, ProductPreference, IPHONE_MODELS
from forms import LoginForm, FilterForm
from config import Config

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('admin.login'))
        
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('admin.dashboard')
        return redirect(next_page)
    
    return render_template('admin/login.html', form=form)

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Count total submissions
    total_submissions = Preference.query.count()
    
    # Group submissions by notification mode
    mode_counts = db.session.query(
        Preference.notification_mode, 
        db.func.count(Preference.id)
    ).group_by(Preference.notification_mode).all()
    
    # Create a dictionary of mode counts
    mode_data = {
        'all': 0,
        'only_preferred': 0,
        'near_good_deal': 0,
        'good_deal': 0
    }
    
    mode_labels = {
        'all': 'All Listings',
        'only_preferred': 'Only Preferred',
        'near_good_deal': 'Near Good Deal',
        'good_deal': 'Good Deal'
    }
    
    for mode, count in mode_counts:
        mode_data[mode] = count
    
    # Get most popular iPhone models
    popular_models = db.session.query(
        ProductPreference.product_name,
        db.func.count(ProductPreference.id)
    ).filter(ProductPreference.is_preferred == True)\
     .group_by(ProductPreference.product_name)\
     .order_by(db.func.count(ProductPreference.id).desc())\
     .limit(5).all()
    
    # Recent submissions
    recent_submissions = Preference.query.order_by(Preference.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_submissions=total_submissions,
                         mode_data=mode_data,
                         mode_labels=mode_labels,
                         popular_models=popular_models,
                         recent_submissions=recent_submissions)

@admin_bp.route('/responses')
@login_required
def responses():
    # Get filter parameters
    location = request.args.get('location', '')
    notification_mode = request.args.get('notification_mode', '')
    
    # Create query with filters
    query = Preference.query
    
    if location:
        query = query.filter(Preference.location.ilike(f'%{location}%'))
    
    if notification_mode:
        query = query.filter(Preference.notification_mode == notification_mode)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Preference.created_at.desc()).paginate(
        page=page, per_page=Config.RESPONSES_PER_PAGE, error_out=False
    )
    
    # Create filter form
    filter_form = FilterForm(request.args)
    
    return render_template('admin/responses.html',
                         pagination=pagination,
                         filter_form=filter_form)

@admin_bp.route('/responses/<int:id>')
@login_required
def view_response(id):
    preference = Preference.query.get_or_404(id)
    
    # Create the edit URL for sharing with users
    edit_url = url_for('main.edit_preference', token=preference.edit_token, _external=True)
    
    return render_template('admin/view_response.html', 
                         preference=preference,
                         edit_url=edit_url)

@admin_bp.route('/responses/<int:id>/delete', methods=['POST'])
@login_required
def delete_response(id):
    preference = Preference.query.get_or_404(id)
    db.session.delete(preference)
    db.session.commit()
    
    flash('Response deleted successfully', 'success')
    return redirect(url_for('admin.responses'))

@admin_bp.route('/export')
@login_required
def export_data():
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    header = ['ID', 'Location', 'Suburb', 'Notification Mode', 'Created At', 'Updated At']
    
    # Add headers for each iPhone model (max price and preferred)
    for model in IPHONE_MODELS:
        header.extend([f'{model} - Max Price', f'{model} - Preferred'])
    
    writer.writerow(header)
    
    # Query all preferences
    preferences = Preference.query.all()
    
    # Write data rows
    for pref in preferences:
        # Start with basic info
        row = [
            pref.id, 
            pref.location, 
            pref.suburb, 
            pref.notification_mode,
            pref.created_at.strftime('%Y-%m-%d %H:%M:%S') if pref.created_at else '',
            pref.updated_at.strftime('%Y-%m-%d %H:%M:%S') if pref.updated_at else ''
        ]
        
        # Create dictionary of product preferences for easier lookup
        product_dict = {p.product_name: p for p in pref.products}
        
        # Add data for each iPhone model
        for model in IPHONE_MODELS:
            if model in product_dict:
                product = product_dict[model]
                row.extend([product.max_price, 'Yes' if product.is_preferred else 'No'])
            else:
                row.extend(['', ''])
        
        writer.writerow(row)
    
    # Prepare the output for download
    output.seek(0)
    
    # Create an in-memory bytes buffer
    bytes_output = io.BytesIO()
    bytes_output.write(output.getvalue().encode('utf-8-sig'))  # Use UTF-8 with BOM for Excel compatibility
    bytes_output.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return send_file(
        bytes_output,
        as_attachment=True,
        download_name=f'iphone_flippers_data_{timestamp}.csv',
        mimetype='text/csv'
    )