from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
import io
import csv
from datetime import datetime
import xlsxwriter

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
    # Create an in-memory bytes buffer for Excel
    output = io.BytesIO()
    
    # Create Excel workbook and add worksheets
    workbook = xlsxwriter.Workbook(output)
    
    # Add formatting
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    subheader_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D9E1F2',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    instructions_format = workbook.add_format({
        'font_color': '#525252',
        'text_wrap': True,
        'valign': 'vcenter'
    })
    
    data_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })
    
    # Create Users worksheet
    users_sheet = workbook.add_worksheet('Users')
    
    # Set column widths
    users_sheet.set_column('A:A', 18)  # unique_userid
    users_sheet.set_column('B:B', 15)  # user_id
    users_sheet.set_column('C:C', 20)  # user_name
    users_sheet.set_column('D:D', 20)  # location
    users_sheet.set_column('E:E', 8)   # activation_status
    users_sheet.set_column('F:F', 15)  # expiry_date
    users_sheet.set_column('G:G', 12)  # fixed_lat
    users_sheet.set_column('H:H', 12)  # fixed_lon
    users_sheet.set_column('I:I', 15)  # password
    users_sheet.set_column('J:J', 8)   # mode_only_preferred
    users_sheet.set_column('K:K', 8)   # non_good_deals
    users_sheet.set_column('L:L', 8)   # good_deals
    users_sheet.set_column('M:M', 8)   # near_good_deals
    
    # Title row
    users_sheet.merge_range('A1:M1', f'iPhone Flippers - User Data Export - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', title_format)
    
    # Instructions row
    users_sheet.merge_range('A2:M2', 'Instructions: Edit user data in this sheet. For products, use the Products sheet.', instructions_format)
    
    # Header sections
    users_sheet.merge_range('A3:I3', 'USER INFORMATION', subheader_format)
    users_sheet.merge_range('J3:M3', 'NOTIFICATION MODES', subheader_format)
    
    # User headers row
    users_headers = [
        'unique_userid',
        'user_id',
        'user_name',
        'location',
        'activation_status',
        'expiry_date',
        'fixed_lat',
        'fixed_lon',
        'password',
        'mode_only_preferred',
        'non_good_deals',
        'good_deals',
        'near_good_deals'
    ]
    
    for col, header in enumerate(users_headers):
        users_sheet.write(3, col, header, header_format)
    
    # Query all preferences
    preferences = Preference.query.all()
    
    # Write user data rows
    row = 4
    for pref in preferences:
        # Generate a unique ID for this user
        unique_userid = f"user_{pref.id}"
        
        # Set default mode values based on notification_mode
        mode_only_preferred = 1 if pref.notification_mode == 'only_preferred' else 0
        non_good_deals = 1 if pref.notification_mode == 'all' else 0
        good_deals = 1 if pref.notification_mode == 'good_deal' else 0
        near_good_deals = 1 if pref.notification_mode == 'near_good_deal' else 0
        
        # Create row with available data and empty fields for the rest
        users_sheet.write(row, 0, unique_userid, data_format)        # unique_userid
        users_sheet.write(row, 1, "", data_format)                   # user_id
        users_sheet.write(row, 2, "", data_format)                   # user_name
        users_sheet.write(row, 3, pref.location, data_format)        # location
        users_sheet.write(row, 4, 1, data_format)                    # activation_status
        users_sheet.write(row, 5, "", data_format)                   # expiry_date
        users_sheet.write(row, 6, "", data_format)                   # fixed_lat
        users_sheet.write(row, 7, "", data_format)                   # fixed_lon
        users_sheet.write(row, 8, "", data_format)                   # password
        users_sheet.write(row, 9, mode_only_preferred, data_format)  # mode_only_preferred
        users_sheet.write(row, 10, non_good_deals, data_format)      # non_good_deals
        users_sheet.write(row, 11, good_deals, data_format)          # good_deals
        users_sheet.write(row, 12, near_good_deals, data_format)     # near_good_deals
        
        row += 1
    
    # Create Products worksheet
    products_sheet = workbook.add_worksheet('Products')
    
    # Set column widths
    products_sheet.set_column('A:A', 18)  # unique_userid
    products_sheet.set_column('B:B', 25)  # name
    products_sheet.set_column('C:C', 12)  # min_price
    products_sheet.set_column('D:D', 12)  # max_price
    products_sheet.set_column('E:E', 12)  # preferred
    
    # Title row
    products_sheet.merge_range('A1:E1', 'Product Preferences', title_format)
    
    # Instructions row
    products_sheet.merge_range('A2:E2', 'Match unique_userid with the Users sheet. Set preferred to 1 for yes, 0 for no.', instructions_format)
    
    # Product headers row
    product_headers = [
        'unique_userid',
        'name',
        'min_price',
        'max_price',
        'preferred'
    ]
    
    for col, header in enumerate(product_headers):
        products_sheet.write(3, col, header, header_format)
    
    # Write product data rows
    row = 4
    for pref in preferences:
        unique_userid = f"user_{pref.id}"
        
        for product in pref.products:
            products_sheet.write(row, 0, unique_userid, data_format)             # unique_userid
            products_sheet.write(row, 1, product.product_name, data_format)      # name
            products_sheet.write(row, 2, 100, data_format)                       # min_price (set to 100 as requested)
            products_sheet.write(row, 3, product.max_price, data_format)         # max_price
            products_sheet.write(row, 4, 1 if product.is_preferred else 0, data_format)  # preferred
            
            row += 1
    
    # Create a Keywords worksheet (empty template)
    keywords_sheet = workbook.add_worksheet('Keywords')
    
    # Set column widths
    keywords_sheet.set_column('A:A', 18)  # unique_userid
    keywords_sheet.set_column('B:B', 30)  # keyword
    
    # Title row
    keywords_sheet.merge_range('A1:B1', 'Keywords', title_format)
    
    # Instructions row
    keywords_sheet.merge_range('A2:B2', 'Add search keywords. Match unique_userid with the Users sheet.', instructions_format)
    
    # Keywords headers
    keywords_headers = [
        'unique_userid',
        'keyword'
    ]
    
    for col, header in enumerate(keywords_headers):
        keywords_sheet.write(3, col, header, header_format)
    
    # Create an Excluded Words worksheet (empty template)
    excluded_sheet = workbook.add_worksheet('Excluded Words')
    
    # Set column widths
    excluded_sheet.set_column('A:A', 18)  # unique_userid
    excluded_sheet.set_column('B:B', 30)  # excluded_word
    
    # Title row
    excluded_sheet.merge_range('A1:B1', 'Excluded Words', title_format)
    
    # Instructions row
    excluded_sheet.merge_range('A2:B2', 'Add words to exclude from search. Match unique_userid with the Users sheet.', instructions_format)
    
    # Excluded words headers
    excluded_headers = [
        'unique_userid',
        'excluded_word'
    ]
    
    for col, header in enumerate(excluded_headers):
        excluded_sheet.write(3, col, header, header_format)
    
    # Create a Resellers worksheet (empty template)
    resellers_sheet = workbook.add_worksheet('Resellers')
    
    # Set column widths
    resellers_sheet.set_column('A:A', 18)  # unique_userid
    resellers_sheet.set_column('B:B', 30)  # reseller_name
    
    # Title row
    resellers_sheet.merge_range('A1:B1', 'Resellers', title_format)
    
    # Instructions row
    resellers_sheet.merge_range('A2:B2', 'Add preferred resellers. Match unique_userid with the Users sheet.', instructions_format)
    
    # Resellers headers
    resellers_headers = [
        'unique_userid',
        'reseller_name'
    ]
    
    for col, header in enumerate(resellers_headers):
        resellers_sheet.write(3, col, header, header_format)
    
    # Create Instructions sheet
    instructions_sheet = workbook.add_worksheet('Instructions')
    
    # Set column widths
    instructions_sheet.set_column('A:A', 100)
    
    # Add instructions
    instructions = [
        "IPHONE FLIPPERS - DATA IMPORT/EXPORT INSTRUCTIONS",
        "",
        "This Excel file contains multiple sheets for managing user data and preferences:",
        "",
        "1. USERS SHEET",
        "   • Contains basic user information and notification settings",
        "   • Required fields: unique_userid, location",
        "   • For notification modes, set exactly ONE to 1 (Yes) and the rest to 0 (No)",
        "",
        "2. PRODUCTS SHEET",
        "   • Contains product preferences for each user",
        "   • Each row represents one product preference for one user",
        "   • The unique_userid must match a user in the Users sheet",
        "   • min_price is the minimum price you'd accept (default: 100)",
        "   • max_price is the maximum price you'd be willing to pay",
        "   • preferred should be 1 (Yes) or 0 (No)",
        "",
        "3. KEYWORDS SHEET",
        "   • Add search keywords for users",
        "   • Each row is one keyword for one user",
        "",
        "4. EXCLUDED WORDS SHEET",
        "   • Add words to exclude from search results",
        "   • Each row is one excluded word for one user",
        "",
        "5. RESELLERS SHEET",
        "   • Add preferred resellers",
        "   • Each row is one reseller for one user",
        "",
        "IMPORTANT NOTES:",
        "• When importing, make sure all your unique_userid values in dependent sheets match the Users sheet",
        "• Do not modify the header rows or sheet structure",
        "• For importing, save as Excel (.xlsx) format",
        "• If you're unsure about a field, leave it as is"
    ]
    
    row = 0
    for line in instructions:
        if not line:
            # Empty line
            instructions_sheet.write(row, 0, '')
        elif line.startswith("IPHONE FLIPPERS"):
            # Title
            instructions_sheet.write(row, 0, line, title_format)
        elif line.strip().endswith(":") or line.startswith("IMPORTANT"):
            # Section header
            section_format = workbook.add_format({'bold': True, 'font_size': 12})
            instructions_sheet.write(row, 0, line, section_format)
        else:
            # Regular text
            instructions_sheet.write(row, 0, line, instructions_format)
        row += 1
    
    # Close the workbook
    workbook.close()
    
    # Seek to the beginning of the file
    output.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'iphone_flippers_data_{timestamp}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
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
        
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            # TODO: Implement Excel import logic here using pandas or openpyxl
            # This would read the excel file and process each sheet accordingly
            
            # For now, just show a placeholder message
            flash('Excel import not yet implemented', 'warning')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Please upload an Excel (.xlsx) or CSV file', 'danger')
            return redirect(request.url)
    
    # GET request - show upload form
    return render_template('admin/import.html')