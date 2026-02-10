from functools import wraps
from flask_login import current_user
from app.utils.jwt_required import jwt_required  # adjust path if needed

def login_or_jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        return jwt_required(f)(*args, **kwargs)
    return decorated_function