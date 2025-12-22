from django.shortcuts import render
from ..forms import ContactForm
from ..models import Testimonial

def home(request):
    form = ContactForm()
    # Fetch only approved testimonials to show on the page
    approved_reviews = Testimonial.objects.filter(is_approved=True).order_by('-created_at')
    
    return render(request, 'home/home.html', {'form': form,'approved_reviews': approved_reviews})

