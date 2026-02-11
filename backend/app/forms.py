from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange
from flask_wtf.file import FileField, FileRequired, FileAllowed

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
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    prison_id = StringField('Prison ID / Reference Number', validators=[DataRequired(), Length(min=2, max=64)])
    face_image = FileField('Face Image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    duration_months = IntegerField('Duration (in months)', validators=[DataRequired(), NumberRange(min=1, max=1200)])
    submit = SubmitField('Register')

class UploadFaceForm(FlaskForm):
    file = FileField('Upload Image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Submit')