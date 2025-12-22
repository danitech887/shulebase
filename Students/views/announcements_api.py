from ..models import Announcement
def get_announcements(role,school_id):
    announcement_qs = Announcement.objects.filter(school_id = school_id)

    if role == 'student':
        announcement_qs = announcement_qs.filter(target_audience = 'STUDENTS')
    elif role== 'teacher':
        announcement_qs = announcement_qs.filter(target_audience = 'TEACHERS')
    elif role== 'parent':
        announcement_qs = announcement_qs.filter(target_audience = 'PARENTS')

    no_of_announcements = announcement_qs.count()
    return no_of_announcements
