# Pupils/utils/manager.py
from django.db import models

class SchoolManager(models.Manager):
    def for_school(self, request):
        school_id = getattr(request, "school_id", None)
        if school_id:
            return self.get_queryset().filter(school=school_id)
        return self.get_queryset().none()
