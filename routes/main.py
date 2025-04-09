from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from models import db, Preference, ProductPreference, IPHONE_MODELS, DEFAULT_PRICES
from forms import PreferenceForm

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    form = PreferenceForm()
    
    if form.validate_on_submit():
        # Create a new preference entry
        preference = Preference(
            location=form.location.data,
            suburb=form.suburb.data,
            notification_mode=form.notification_mode.data
        )
        db.session.add(preference)
        db.session.flush()  # Get the ID without committing
        
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
        
        # Redirect to thank you page with the edit token
        return redirect(url_for('main.thank_you', token=preference.edit_token))
    
    # Pre-fill the form with default values
    return render_template('form.html', 
                           form=form, 
                           iphone_models=IPHONE_MODELS,
                           default_prices=DEFAULT_PRICES)

@main_bp.route('/thank-you/<token>')
def thank_you(token):
    # Get the preference to display a summary
    preference = Preference.query.filter_by(edit_token=token).first_or_404()
    
    # Create the edit URL
    edit_url = url_for('main.edit_preference', token=token, _external=True)
    
    return render_template('thank_you.html', 
                          preference=preference,
                          edit_url=edit_url)

@main_bp.route('/edit/<token>', methods=['GET', 'POST'])
def edit_preference(token):
    # Get the preference by token
    preference = Preference.query.filter_by(edit_token=token).first_or_404()
    
    form = PreferenceForm()
    
    if form.validate_on_submit():
        # Update the preference
        preference.location = form.location.data
        preference.suburb = form.suburb.data
        preference.notification_mode = form.notification_mode.data
        
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
        flash('Your preferences have been updated successfully!', 'success')
        return redirect(url_for('main.thank_you', token=preference.edit_token))
    
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
    
    return render_template('edit_form.html',
                          form=form,
                          iphone_models=IPHONE_MODELS,
                          default_prices=DEFAULT_PRICES,
                          product_prefs=product_prefs,
                          preference=preference)