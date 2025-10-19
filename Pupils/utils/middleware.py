# # Pupils/middleware.py
# from django.utils.deprecation import MiddlewareMixin
# from Pupils.models import MasterSchool
# from Pupils.utils.per_school_db_utils import get_school_db_alias_from_session

# class CurrentSchoolMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         alias = get_school_db_alias_from_session(request)
#         school_id = request.session.get("school_id")

#         if not school_id and alias:
#             try:
#                 school = MasterSchool.objects.using("default").get(db_name__iexact=alias)
#                 request.session["school_id"] = school.id
#                 request.school_id = school.id
#             except MasterSchool.DoesNotExist:
#                 request.school_id = None
#         else:
#             request.school_id = school_id
