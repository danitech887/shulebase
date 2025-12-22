from ..models import Announcement   
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q

from .announcements_api import get_announcements

@login_required
def announcement_list(request):
    school_id = request.session.get('school_id')
    announcements = Announcement.objects.filter(school_id=school_id).order_by('-created_at')

    # Search functionality
    query = request.GET.get('q')
    if query:
        announcements = announcements.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )

    # Pagination
    paginator = Paginator(announcements, 10)  # Show 10 announcements per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'announcements': page_obj,
        'query': query,
    }
    return render(request, 'students/pages/announcements.html', context)

@login_required
def create_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        school_id = request.session.get('school_id')
        target_audience = request.POST.get('target_audience')

        Announcement.objects.create(
            school_id=school_id,
            title=title,
            content=content,
            target_audience=target_audience,
            created_at=timezone.now()
        )
        request.session['announcements'] = Announcement.objects.filter(school_id = school_id,target_audience = target_audience).count()
        messages.success(request, 'Announcement created successfully.')
        return redirect('announcement_list')


@login_required
def edit_announcement(request, id):
    announcement = get_object_or_404(Announcement, id=id)
    if request.method == 'POST':
        announcement.title = request.POST.get('title')
        announcement.content = request.POST.get('content')
        announcement.target_audience = request.POST.get('target_audience')
        announcement.save()
        messages.success(request, 'Announcement updated successfully!')
    return redirect('announcements')

@login_required
def delete_announcement(request, id):
    announcement = get_object_or_404(Announcement, id=id)
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully!')
    return redirect('announcements')