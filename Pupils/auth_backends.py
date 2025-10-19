from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .utils.per_school_db_utils import get_school_db_alias_from_session

class PerSchoolDatabaseBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            return None
        alias = get_school_db_alias_from_session(request)
        UserModel = get_user_model()
        try:
            user = UserModel.objects.db_manager(alias).get(username=username)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        # WARNING: This version does not support multi-db user fetch for request.user automatically.
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
