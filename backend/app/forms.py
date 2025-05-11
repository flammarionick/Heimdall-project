# backend/app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Length(min=6, max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    is_admin = BooleanField('Admin?')
    submit = SubmitField('Save')


class InmateForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    inmate_id = StringField('Inmate ID', validators=[DataRequired()])
    crime = StringField('Crime', validators=[DataRequired()])
    photo_url = StringField('Photo URL')
    submit = SubmitField('Register')


class UploadFaceForm(FlaskForm):
    file = FileField('Upload Image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Submit')
