import os
from flask import current_app, redirect, url_for, request, flash, render_template, abort, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from modules.models.entities import User
from flask import Blueprint
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from flask_jwt_extended import create_access_token, jwt_required
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash


auth_bp = Blueprint('auth', __name__)

login_manager = LoginManager()
csrf = CSRFProtect()

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if "/api/" in request.path:
        return abort(401)
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('routes.index'))
        else:
            flash("Credenciales no válidas. Intente nuevamente.", 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))

    form = SignupForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Verificar si el usuario ya existe en la base de datos
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("El nombre de usuario ya existe. Por favor, elige otro.", 'danger')
        else:
            # Crear un nuevo usuario y guardarlo en la base de datos
            new_user = User(username=username, password=password)
            new_user.set_password(password)  # Configura la contraseña de forma segura
            new_user.guardar()
            flash("Registro exitoso. Inicia sesión con tu nueva cuenta.", 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('signup.html', form=form)


@auth_bp.route('/login-jwt', methods=['POST']) 
@csrf.exempt
def login_jwt():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    else:
        return jsonify({"msg":"Credenciales inválidas"}),401

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

def jwt_or_login_required():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                jwt_required()(lambda: None)()
            except:
                if current_user.is_authenticated:
                    return f(*args, **kwargs)
                return {"message": "Acceso no autorizado"}, 401
            return f(*args, **kwargs)

        return decorated_function
    return decorator
