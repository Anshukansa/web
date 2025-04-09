from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class PreferenceForm(FlaskForm):
    location = StringField('Location (City)', validators=[DataRequired()])
    suburb = StringField('Suburb', validators=[Optional()])
    
    notification_mode = RadioField(
        'Mode',
        choices=[
            ('all', 'All: You\'ll receive notifications about every listing, regardless of your preferences.'),
            ('only_preferred', 'Only Preferred: You\'ll only receive notifications about the specific models you\'re interested in.'),
            ('near_good_deal', 'Near Good Deal: You\'ll receive notifications about your preferred models when they\'re priced within $100 above your maximum budget.'),
            ('good_deal', 'Good Deal: You\'ll only receive notifications about your preferred models when they\'re priced below your maximum budget.')
        ],
        validators=[DataRequired()],
        default='near_good_deal'
    )
    
    # Product preferences will be handled dynamically in the view function
    # since we have a variable number of products
    
    submit = SubmitField('Submit Preferences')

# For admin filtering and searching
class FilterForm(FlaskForm):
    location = StringField('Location')
    notification_mode = RadioField(
        'Notification Mode',
        choices=[
            ('', 'All'),
            ('all', 'All Listings'),
            ('only_preferred', 'Only Preferred'),
            ('near_good_deal', 'Near Good Deal'),
            ('good_deal', 'Good Deal')
        ],
        default=''
    )
    submit = SubmitField('Filter')