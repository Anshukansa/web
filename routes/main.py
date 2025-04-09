from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify, g, session
from models import db, Preference, ProductPreference, IPHONE_MODELS, DEFAULT_PRICES
from forms import PreferenceForm
from telegram_auth import verify_telegram_auth
import logging

# Configure logging
logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Public index page - redirects to access denied"""
    return redirect(url_for('main.access_denied'))

@main_bp.route('/access-denied')
def access_denied():
    """Access denied page for unauthorized access attempts"""
    reason = request.args.get('reason', 'unauthorized')
    return render_template('access_denied.html', reason=reason)

@main_bp.route('/telegram-form', methods=['GET', 'POST'])
@verify_telegram_auth
def telegram_form():
    """Form accessible only through Telegram authentication"""
    # Get Telegram user info from the auth decorator
    user_id = g.telegram_user_id
    user_name = g.telegram_user_name
    
    logger.info(f"Processing telegram-form for user_id={user_id}, user_name={user_name}")
    
    # Check if user already has a preference record
    preference = Preference.query.filter_by(user_id=user_id).first()
    
    # If user exists, redirect to edit their data
    if preference:
        logger.info(f"User {user_id} already has preferences, redirecting to edit page")
        return redirect(url_for('main.edit_telegram_preference'))
    
    # Otherwise, show the new form
    form = PreferenceForm()
    
    if form.validate_on_submit():
        logger.info(f"Form submitted for new user {user_id}")
        # Create new preference with Telegram user info
        preference = Preference(
            location=form.location.data,
            suburb=form.suburb.data,
            notification_mode=form.notification_mode.data,
            user_id=user_id,  # Set Telegram ID as user_id
            user_name=user_name,  # Set Telegram name as user_name
            activation_status=True
        )
        db.session.add(preference)
        db.session.flush()  # Get the ID without committing
        
        # Set unique_userid based on the ID
        preference.unique_userid = f"telegram_{preference.id}"
        
        # Process product preferences
        for model in IPHONE_MODELS:
            # Check if the product was included in the form
            max_price = request.form.get(f'max_price_{model.replace(" ", "_")}')
            is_preferred = request.form.get(f'is_preferred_{model.replace(" ", "_")}')
            
            if max_price:
                product_pref = ProductPreference(
                    preference_id=preference.id,
                    product_name=model,
                    max_price=int(max_price),
                    is_preferred=is_preferred == 'on'  # Checkbox returns 'on' if checked
                )
                db.session.add(product_pref)
        
        db.session.commit()
        logger.info(f"Created new preference for Telegram user ID {user_id}")
        
        # Redirect to thank you page with session-based auth
        return redirect(url_for('main.telegram_thank_you'))
    
    # Pre-fill the form with default values
    return render_template('telegram_form.html', 
                          form=form, 
                          iphone_models=IPHONE_MODELS,
                          default_prices=DEFAULT_PRICES,
                          telegram_user_name=user_name)

@main_bp.route('/edit-telegram', methods=['GET', 'POST'])
@verify_telegram_auth
def edit_telegram_preference():
    """Edit preference for Telegram users"""
    # Get Telegram user info from the auth decorator
    user_id = g.telegram_user_id
    user_name = g.telegram_user_name
    
    logger.info(f"Processing edit form for user_id={user_id}, user_name={user_name}")
    
    # Get the preference by Telegram user_id
    preference = Preference.query.filter_by(user_id=user_id).first()
    
    # If no preference exists yet, redirect to the creation form
    if not preference:
        logger.info(f"No preference found for user {user_id}, redirecting to creation form")
        return redirect(url_for('main.telegram_form'))
    
    form = PreferenceForm()
    
    if form.validate_on_submit():
        logger.info(f"Form submitted for editing user {user_id}")
        # Update the preference
        preference.location = form.location.data
        preference.suburb = form.suburb.data
        preference.notification_mode = form.notification_mode.data
        preference.user_name = user_name  # Update name in case it changed
        
        # Process product preferences
        # First, delete existing preferences
        for product in preference.products:
            db.session.delete(product)
        
        # Then create new ones
        for model in IPHONE_MODELS:
            # Check if the product was included in the form
            max_price = request.form.get(f'max_price_{model.replace(" ", "_")}')
            is_preferred = request.form.get(f'is_preferred_{model.replace(" ", "_")}')
            
            if max_price:
                product_pref = ProductPreference(
                    preference_id=preference.id,
                    product_name=model,
                    max_price=int(max_price),
                    is_preferred=is_preferred == 'on'  # Checkbox returns 'on' if checked
                )
                db.session.add(product_pref)
        
        db.session.commit()
        logger.info(f"Updated preference for Telegram user ID {user_id}")
        flash('Your preferences have been updated successfully!', 'success')
        return redirect(url_for('main.telegram_thank_you'))
    
    # Pre-fill the form with existing values
    form.location.data = preference.location
    form.suburb.data = preference.suburb
    form.notification_mode.data = preference.notification_mode
    
    # Create a dict of existing product preferences for pre-filling the form
    product_prefs = {}
    for product in preference.products:
        product_prefs[product.product_name] = {
            'max_price': product.max_price,
            'is_preferred': product.is_preferred
        }
    
    return render_template('telegram_edit_form.html',
                          form=form,
                          iphone_models=IPHONE_MODELS,
                          default_prices=DEFAULT_PRICES,
                          product_prefs=product_prefs,
                          preference=preference,
                          telegram_user_name=user_name)

@main_bp.route('/telegram-thank-you')
@verify_telegram_auth
def telegram_thank_you():
    """Thank you page for Telegram users"""
    # Get Telegram user info from the auth decorator
    user_id = g.telegram_user_id
    user_name = g.telegram_user_name
    
    logger.info(f"Showing thank you page for user_id={user_id}, user_name={user_name}")
    
    # Get the preference to display a summary
    preference = Preference.query.filter_by(user_id=user_id).first_or_404()
    
    return render_template('telegram_thank_you.html', 
                          preference=preference,
                          telegram_user_name=user_name)

# Disable direct access to old routes
@main_bp.route('/thank-you/<token>')
def thank_you(token):
    """Legacy thank you page - disabled"""
    return redirect(url_for('main.access_denied'))

@main_bp.route('/edit/<token>', methods=['GET', 'POST'])
def edit_preference(token):
    """Legacy edit page - disabled"""
    return redirect(url_for('main.access_denied'))