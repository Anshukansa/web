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
    
    # Write header row for the new database schema
    header = [
        # Users table
        'unique_userid', 'user_id', 'user_name', 'location', 'activation_status', 
        'expiry_date', 'fixed_lat', 'fixed_lon', 'password',
        
        # Product prices (semicolon separated format: "name:min_price:max_price:preferred;")
        'products',
        
        # Keywords (semicolon separated)
        'keywords',
        
        # Excluded words (semicolon separated)
        'excluded_words',
        
        # Resellers (semicolon separated)
        'resellers',
        
        # User modes
        'mode_only_preferred', 'non_good_deals', 'good_deals', 'near_good_deals'
    ]
    
    writer.writerow(header)
    
    # Query all preferences
    preferences = Preference.query.all()
    
    # Write data rows
    for pref in preferences:
        # Generate a unique ID for this user (using original ID with a prefix)
        unique_userid = f"user_{pref.id}"
        
        # Set default mode values based on notification_mode
        mode_only_preferred = 1 if pref.notification_mode == 'only_preferred' else 0
        non_good_deals = 1 if pref.notification_mode == 'all' else 0
        good_deals = 1 if pref.notification_mode == 'good_deal' else 0
        near_good_deals = 1 if pref.notification_mode == 'near_good_deal' else 0
        
        # Extract products
        products_list = []
        for product in pref.products:
            if product.is_preferred:
                # Format: name:min_price:max_price:preferred
                # Using 0 as min_price since it's not in the original schema
                products_list.append(f"{product.product_name}:0:{product.max_price}:1")
            else:
                products_list.append(f"{product.product_name}:0:{product.max_price}:0")
        
        products_str = ";".join(products_list)
        
        # Create row with available data and empty fields for the rest
        row = [
            unique_userid,               # unique_userid
            "",                          # user_id (not in original schema)
            "",                          # user_name (not in original schema)
            pref.location,               # location
            1,                           # activation_status (default to active)
            "",                          # expiry_date (not in original schema)
            "",                          # fixed_lat (not in original schema)
            "",                          # fixed_lon (not in original schema)
            "",                          # password (not in original schema)
            products_str,                # products
            "",                          # keywords (not in original schema)
            "",                          # excluded_words (not in original schema)
            "",                          # resellers (not in original schema)
            mode_only_preferred,         # mode_only_preferred
            non_good_deals,              # non_good_deals
            good_deals,                  # good_deals
            near_good_deals              # near_good_deals
        ]
        
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
        download_name=f'user_data_export_{timestamp}.csv',
        mimetype='text/csv'
    )

@admin_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            # Process the CSV file
            stream = io.StringIO(file.stream.read().decode("UTF-8-sig"))
            csv_reader = csv.DictReader(stream)
            
            # Counters for statistics
            added = 0
            updated = 0
            errors = 0
            
            try:
                for row in csv_reader:
                    try:
                        # Find or create a new preference entry based on unique_userid
                        unique_userid = row['unique_userid']
                        
                        # Extract location from the CSV
                        location = row['location']
                        
                        # Create notification mode from mode flags
                        if int(row.get('good_deals', 0)) == 1:
                            notification_mode = 'good_deal'
                        elif int(row.get('near_good_deals', 0)) == 1:
                            notification_mode = 'near_good_deal'
                        elif int(row.get('mode_only_preferred', 0)) == 1:
                            notification_mode = 'only_preferred'
                        else:
                            notification_mode = 'all'
                        
                        # Look up by unique_userid in the format "user_X"
                        if unique_userid.startswith('user_'):
                            try:
                                pref_id = int(unique_userid.split('_')[1])
                                preference = Preference.query.get(pref_id)
                            except:
                                preference = None
                        else:
                            preference = None
                            
                        if preference:
                            # Update existing preference
                            preference.location = location
                            preference.suburb = row.get('suburb', '')  # Assuming suburb might be in the CSV
                            preference.notification_mode = notification_mode
                            updated += 1
                        else:
                            # Create new preference
                            preference = Preference(
                                location=location,
                                suburb=row.get('suburb', ''),
                                notification_mode=notification_mode
                            )
                            db.session.add(preference)
                            db.session.flush()  # Get ID without committing
                            added += 1
                        
                        # Process products
                        # First, delete existing products
                        for product in preference.products:
                            db.session.delete(product)
                        
                        # Add new products from CSV
                        if 'products' in row and row['products']:
                            for product_data in row['products'].split(';'):
                                if product_data:
                                    parts = product_data.split(':')
                                    if len(parts) >= 4:
                                        name, min_price, max_price, preferred = parts
                                        product_pref = ProductPreference(
                                            preference_id=preference.id,
                                            product_name=name,
                                            max_price=int(float(max_price)),
                                            is_preferred=(int(preferred) == 1)
                                        )
                                        db.session.add(product_pref)
                        
                        db.session.commit()
                        
                    except Exception as e:
                        db.session.rollback()
                        errors += 1
                        print(f"Error processing row: {e}")
                
                flash(f'Import completed. Added: {added}, Updated: {updated}, Errors: {errors}', 'success')
            except Exception as e:
                flash(f'Error processing CSV: {str(e)}', 'danger')
            
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Please upload a CSV file', 'danger')
            return redirect(request.url)
    
    # GET request - show upload form
    return render_template('admin/import.html')