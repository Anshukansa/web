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
    
    # Create two CSVs - one for users and one for products
    # First, write the main user data
    
    # Column headers for users file
    user_headers = [
        'unique_userid', 'user_id', 'user_name', 'location', 'activation_status', 
        'expiry_date', 'fixed_lat', 'fixed_lon', 'password',
        'mode_only_preferred', 'non_good_deals', 'good_deals', 'near_good_deals'
    ]
    
    writer.writerow(user_headers)
    
    # Now create a second CSV output for products
    product_output = io.StringIO()
    product_writer = csv.writer(product_output)
    
    # Column headers for products file
    product_headers = [
        'unique_userid', 'name', 'min_price', 'max_price', 'preferred'
    ]
    
    product_writer.writerow(product_headers)
    
    # Create outputs for keywords, excluded words, and resellers
    keyword_output = io.StringIO()
    keyword_writer = csv.writer(keyword_output)
    keyword_writer.writerow(['unique_userid', 'keyword'])
    
    excluded_output = io.StringIO()
    excluded_writer = csv.writer(excluded_output)
    excluded_writer.writerow(['unique_userid', 'excluded_word'])
    
    reseller_output = io.StringIO()
    reseller_writer = csv.writer(reseller_output)
    reseller_writer.writerow(['unique_userid', 'reseller_name'])
    
    # Query all preferences
    preferences = Preference.query.all()
    
    # Write data rows for users
    for pref in preferences:
        # Generate a unique ID for this user
        unique_userid = f"user_{pref.id}"
        
        # Set default mode values based on notification_mode
        mode_only_preferred = 1 if pref.notification_mode == 'only_preferred' else 0
        non_good_deals = 1 if pref.notification_mode == 'all' else 0
        good_deals = 1 if pref.notification_mode == 'good_deal' else 0
        near_good_deals = 1 if pref.notification_mode == 'near_good_deal' else 0
        
        # Create row with available data and empty fields for the rest
        user_row = [
            unique_userid,               # unique_userid
            "",                          # user_id (not in original schema)
            "",                          # user_name (not in original schema)
            pref.location,               # location
            1,                           # activation_status (default to active)
            "",                          # expiry_date (not in original schema)
            "",                          # fixed_lat (not in original schema)
            "",                          # fixed_lon (not in original schema)
            "",                          # password (not in original schema)
            mode_only_preferred,         # mode_only_preferred
            non_good_deals,              # non_good_deals
            good_deals,                  # good_deals
            near_good_deals              # near_good_deals
        ]
        
        writer.writerow(user_row)
        
        # Write product data rows
        for product in pref.products:
            product_row = [
                unique_userid,                             # unique_userid
                product.product_name,                      # name
                100,                                       # min_price (set to 100 as requested)
                product.max_price,                         # max_price
                1 if product.is_preferred else 0           # preferred
            ]
            
            product_writer.writerow(product_row)
    
    # Prepare the outputs for download as a ZIP file
    # Since we need to output multiple files, we'll create a ZIP file containing all CSVs
    import zipfile
    
    # Create an in-memory bytes buffer for the ZIP file
    zip_output = io.BytesIO()
    
    # Create a ZIP file
    with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add user data CSV
        zipf.writestr('users.csv', output.getvalue())
        
        # Add product data CSV
        zipf.writestr('products.csv', product_output.getvalue())
        
        # Add empty templates for other data
        zipf.writestr('keywords.csv', keyword_output.getvalue())
        zipf.writestr('excluded_words.csv', excluded_output.getvalue())
        zipf.writestr('resellers.csv', reseller_output.getvalue())
        
        # Add a README file
        readme_content = """iPhone Flippers Data Export

This ZIP file contains the following CSV files:

1. users.csv - Main user information and notification modes
2. products.csv - Product preferences (with min_price set to 100)
3. keywords.csv - Template for adding search keywords
4. excluded_words.csv - Template for adding excluded words
5. resellers.csv - Template for adding preferred resellers

For importing, make sure unique_userid values match across all files.
"""
        zipf.writestr('README.txt', readme_content)
    
    # Seek to the beginning of the file
    zip_output.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return send_file(
        zip_output,
        as_attachment=True,
        download_name=f'iphone_flippers_data_{timestamp}.zip',
        mimetype='application/zip'
    )

@admin_bp.route('/export_response/<int:id>')
@login_required
def export_single_response(id):
    # Retrieve the specific preference by ID
    preference = Preference.query.get_or_404(id)

    # Create the CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Define the header for the CSV file
    header = [
        'unique_userid', 'user_id', 'user_name', 'location', 'activation_status',
        'expiry_date', 'fixed_lat', 'fixed_lon', 'password',
        'mode_only_preferred', 'non_good_deals', 'good_deals', 'near_good_deals'
    ]
    writer.writerow(header)

    # Prepare data for the specific response
    unique_userid = f"user_{preference.id}"
    mode_only_preferred = 1 if preference.notification_mode == 'only_preferred' else 0
    non_good_deals = 1 if preference.notification_mode == 'all' else 0
    good_deals = 1 if preference.notification_mode == 'good_deal' else 0
    near_good_deals = 1 if preference.notification_mode == 'near_good_deal' else 0

    user_row = [
        unique_userid,
        "",  # user_id (not in original schema)
        "",  # user_name (not in original schema)
        preference.location,
        1,  # activation_status (default to active)
        "",  # expiry_date (not in original schema)
        "",  # fixed_lat (not in original schema)
        "",  # fixed_lon (not in original schema)
        "",  # password (not in original schema)
        mode_only_preferred,
        non_good_deals,
        good_deals,
        near_good_deals
    ]
    writer.writerow(user_row)

    # Prepare product data for this preference
    for product in preference.products:
        product_row = [
            unique_userid,
            product.product_name,
            100,  # min_price (set to 100 as requested)
            product.max_price,
            1 if product.is_preferred else 0
        ]
        writer.writerow(product_row)

    # Prepare the output for download
    output.seek(0)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    return send_file(
        output,
        as_attachment=True,
        download_name=f'iphone_flippers_response_{id}_{timestamp}.csv',
        mimetype='text/csv'
    )


@admin_bp.route('/export_csv')
@login_required
def export_csv():
    """Export single CSV file for backward compatibility"""
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Just the header row
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
        
        # Extract products with better formatting
        products_list = []
        for product in pref.products:
            # Format: name:min_price:max_price:preferred
            # Using 100 as min_price as requested
            is_preferred = 1 if product.is_preferred else 0
            products_list.append(f"{product.product_name}:100:{product.max_price}:{is_preferred}")
        
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
            "",                          # keywords (left empty as requested)
            "",                          # excluded_words (left empty as requested)
            "",                          # resellers (left empty as requested)
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
                        
                        # Add new products from CSV
                        if 'products' in row and row['products']:
                            for product_data in row['products'].split(';'):
                                if product_data and ':' in product_data:
                                    try:
                                        parts = product_data.split(':')
                                        if len(parts) >= 4:
                                            name = parts[0].strip()
                                            min_price = parts[1].strip() or '0'
                                            max_price = parts[2].strip() or '0'
                                            preferred = parts[3].strip() or '0'
                                            
                                            # Validate the product name is in our list
                                            if name in IPHONE_MODELS:
                                                product_pref = ProductPreference(
                                                    preference_id=preference.id,
                                                    product_name=name,
                                                    max_price=int(float(max_price)),
                                                    is_preferred=(int(preferred) == 1)
                                                )
                                                db.session.add(product_pref)
                                            else:
                                                print(f"Warning: Skipping unknown product name: {name}")
                                        else:
                                            print(f"Warning: Invalid product format: {product_data}")
                                    except Exception as product_error:
                                        print(f"Error processing product: {product_data}, Error: {product_error}")
                        
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