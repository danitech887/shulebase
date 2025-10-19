def current_school(request):
    return {
        'school_id': request.session.get('school_id'),
        'school_name': request.session.get('school_name'),
        'motto': request.session.get('motto'),
        'vision': request.session.get('vision'),
        'logo_path': request.session.get('logo_path'),
        'address': request.session.get('address'),
        'email': request.session.get('email'),
        'contact': request.session.get('contact'),
    }
