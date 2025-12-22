def current_school(request):
    return {
        'school_id': request.session.get('school_id'),
        'school_name': request.session.get('school_name'),
        'student_name': request.session.get('student_name'),
        'motto': request.session.get('motto'),
        'vision': request.session.get('vision'),
        'logo_path': request.session.get('logo_path'),
        'address': request.session.get('address'),
        'email': request.session.get('email'),
        'contact': request.session.get('contact'),
        'announcements': request.session.get('announcements'),
        'parent_name': request.session.get('parent_name'),

    }
