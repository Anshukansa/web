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
    
    # First row: Main header with application name and export date
    writer.writerow([f"iPhone Flippers Data Export - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    
    # Second row: Section headers to group columns
    writer.writerow(["--- USER INFORMATION ---", "", "", "", "", "", "", "", "--- PRODUCT & PREFERENCE DATA ---", "", "", "", "--- NOTIFICATION MODES ---", "", "", "", ""])
    
    # Third row: Detailed header descriptions
    descriptions = [
        "Unique User ID (Required)",
        "User ID (Optional)",
        "User Name (Optional)",
        "Location (Required)",
        "Active? (1=Yes, 0=No)",
        "Expiry Date (YYYY-MM-DD)",
        "Latitude (Optional)",
        "Longitude (Optional)",
        "Password (Optional)",
        "Products (Format below)",
        "Keywords (Leave empty)",
        "Excluded Words (Leave empty)",
        "Resellers (Leave empty)",
        "Only Preferred (1=Yes, 0=No)",
        "All Listings (1=Yes, 0=No)",
        "Good Deals (1=Yes, 0=No)",
        "Near Good Deals (1=Yes, 0=No)"
    ]
    writer.writerow(descriptions)
    
    # Fourth row: Column names (actual data headers)
    header = [
        'unique_userid', 'user_id', 'user_name', 'location', 'activation_status', 
        'expiry_date', 'fixed_lat', 'fixed_lon', 'password',
        'products', 'keywords', 'excluded_words', 'resellers',
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
        
        # Extract products with better human-readable formatting
        products_list = []
        for product in pref.products:
            # Format: [Product=iPhone 16 Pro Max|MaxPrice=900|Preferred=Yes]
            is_preferred = "Yes" if product.is_preferred else "No"
            products_list.append(f"[Product={product.product_name}|MaxPrice={product.max_price}|Preferred={is_preferred}]")
        
        products_str = "".join(products_list)
        
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
            products_str,                # products (human-readable format)
            "",                          # keywords (left empty as requested)
            "",                          # excluded_words (left empty as requested)
            "",                          # resellers (left empty as requested)
            mode_only_preferred,         # mode_only_preferred
            non_good_deals,              # non_good_deals
            good_deals,                  # good_deals
            near_good_deals              # near_good_deals
        ]
        
        writer.writerow(row)
    
    # Add a footer with instructions
    writer.writerow([])
    writer.writerow(["--- INSTRUCTIONS ---", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    writer.writerow(["1. Do not modify the column headers (row 4)", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    writer.writerow(["2. Each row represents one user", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    writer.writerow(["3. Product format explanation:", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    writer.writerow(["   [Product=iPhone 16 Pro Max|MaxPrice=900|Preferred=Yes]", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    writer.writerow(["   You can add multiple products by connecting them: [Product=iPhone 16|MaxPrice=650|Preferred=Yes][Product=iPhone 15|MaxPrice=500|Preferred=No]", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    writer.writerow(["4. For modes, only ONE should be set to 1, the rest should be 0", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    writer.writerow(["5. When importing, the unique_userid is used to match existing users", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    
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
        download_name=f'iphone_flippers_users_{timestamp}.csv',
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
            try:
                # Read file into memory 
                stream = io.StringIO(file.stream.read().decode("UTF-8-sig"))
                # Skip header rows (if they exist)
                for _ in range(3):  # Skip potential header/description rows
                    line = stream.readline()
                    if not line or 'unique_userid' in line:
                        # We've reached the actual header row or there are no header rows
                        break

                # Reset to start of file if we didn't find the header
                if 'unique_userid' not in line:
                    stream.seek(0)
                
                # Read CSV into a list of dictionaries
                csv_reader = csv.DictReader(stream)
                
                # Counters for statistics
                added = 0
                updated = 0
                errors = 0
                
                for row in csv_reader:
                    try:
                        # Skip rows that are likely comments or instructions
                        if not row.get('unique_userid') or row.get('unique_userid').startswith('---'):
                            continue
                            
                        # Find or create a new preference entry based on unique_userid
                        unique_userid = row['unique_userid'].strip()
                        
                        # Extract location from the CSV
                        location = row['location'].strip() if row.get('location') else ''
                        if not location:
                            raise ValueError("Location is required but was empty")
                            
                        # Determine notification mode from mode flags
                        notification_mode = 'all'  # Default
                        
                        if row.get('mode_only_preferred') and int(row.get('mode_only_preferred', 0)) == 1:
                            notification_mode = 'only_preferred'
                        elif row.get('good_deals') and int(row.get('good_deals', 0)) == 1:
                            notification_mode = 'good_deal'
                        elif row.get('near_good_deals') and int(row.get('near_good_deals', 0)) == 1:
                            notification_mode = 'near_good_deal'
                        elif row.get('non_good_deals') and int(row.get('non_good_deals', 0)) == 1:
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
                            preference.suburb = row.get('suburb', '').strip() if row.get('suburb') else ''
                            preference.notification_mode = notification_mode
                            updated += 1
                        else:
                            # Create new preference
                            preference = Preference(
                                location=location,
                                suburb='',  # Not in our import format but required in model
                                notification_mode=notification_mode
                            )
                            db.session.add(preference)
                            db.session.flush()  # Get ID without committing
                            added += 1
                        
                        # Process products
                        # First, delete existing products
                        for product in preference.products:
                            db.session.delete(product)
                        
                        # Add new products from CSV using the new human-readable format
                        products_data = row.get('products', '')
                        if products_data:
                            # Parse products in the format [Product=X|MaxPrice=Y|Preferred=Z]
                            import re
                            
                            # Find all product entries using regex
                            product_matches = re.findall(r'\[(Product=([^|]+)\|MaxPrice=([^|]+)\|Preferred=([^]]+))\]', products_data)
                            
                            for _, name, max_price, preferred in product_matches:
                                name = name.strip()
                                
                                # Convert max_price to integer
                                try:
                                    max_price = int(float(max_price.strip()))
                                except:
                                    max_price = 0
                                
                                # Convert preferred to boolean (Yes/No or 1/0)
                                preferred_value = preferred.strip().lower()
                                is_preferred = (preferred_value == 'yes' or preferred_value == '1' or preferred_value == 'true')
                                
                                # Validate the product name is in our list
                                if name in IPHONE_MODELS:
                                    product_pref = ProductPreference(
                                        preference_id=preference.id,
                                        product_name=name,
                                        max_price=max_price,
                                        is_preferred=is_preferred
                                    )
                                    db.session.add(product_pref)
                                else:
                                    print(f"Warning: Skipping unknown product name: {name}")
                        
                        db.session.commit()
                        
                    except Exception as e:
                        db.session.rollback()
                        errors += 1
                        print(f"Error processing row: {e}")
                
                message = f'Import completed. Added: {added}, Updated: {updated}'
                if errors > 0:
                    message += f', Errors: {errors}'
                    flash(message, 'warning')
                else:
                    flash(message, 'success')
                    
            except Exception as e:
                flash(f'Error processing CSV: {str(e)}', 'danger')
            
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Please upload a CSV file', 'danger')
            return redirect(request.url)
    
    # GET request - show upload form
    return render_template('admin/import.html')