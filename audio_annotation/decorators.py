from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated_view(*args, **kwargs):
        # print(current_user.is_authenticated, current_user.is_admin())
        if current_user.is_anonymous != True:
            if current_user.is_authenticated and current_user.is_admin():
                return f(*args, **kwargs)
        return abort(401)

    return decorated_view


def annotator_required(f):
    @wraps(f)
    def decorated_view(*args, **kwargs):
        # print(current_user.is_authenticated, current_user.is_admin())
        if current_user.is_anonymous != True:
            if current_user.is_authenticated and current_user.is_annotator():
                return f(*args, **kwargs)
        return abort(401)

    return decorated_view