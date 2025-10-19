from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class PerSchoolDBBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            return None  # For compatibility with non-request auth
        alias = request.session.get('school_db_alias', 'default')
        UserModel = get_user_model()
        try:
            user = UserModel.objects.using(alias).get(username=username)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return None
