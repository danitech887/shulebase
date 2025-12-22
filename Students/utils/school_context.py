from threading import local

_school_context = local()

def set_current_school(school_id):
    _school_context.school_id = school_id

def get_current_school():
    return getattr(_school_context, "school_id", None)
