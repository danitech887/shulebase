from django.shortcuts import render, redirect
from ..models import Testimonial,MasterSchool
from django.contrib import messages

def testimonials_view(request):
    role = request.user.role
    if request.method == "POST":
        # Capture data from the form
        full_name = request.POST.get('full_name')
        location = request.POST.get('location')
        content = request.POST.get('content')
        school_id = request.session.get('school_id')
        school = MasterSchool.objects.get(id = school_id)
        
        # Save to database
        Testimonial.objects.create(
            full_name=full_name,
            user_type=role,
            school=school,
            location=location,
            content=content
        )
        messages.success(request, "Thank you! Your review has been submitted.")
        return redirect('reviews')

    # Fetch only approved reviews to show on the page
    approved_reviews = Testimonial.objects.filter(is_approved=True).order_by('-created_at')
    return render(request, 'reviews/reviews.html', {'reviews': approved_reviews})