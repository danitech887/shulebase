from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.conf import settings
from ..models import MasterSchool,Users

from django.shortcuts import render, redirect
from ..forms import SchoolRegistrationForm
from django.db import connection

from django.core.mail import send_mail


from datetime import datetime
from django.contrib.auth.hashers import make_password
def school_registration(request):
    if request.method == 'POST':
        form = SchoolRegistrationForm(request.POST, request.FILES)
        for _ in messages.get_messages(request):
            pass
        if form.is_valid():
            email = form.cleaned_data.get('email_address')
            username = form.cleaned_data.get('username')
            # Prevent duplicate school emails
            if MasterSchool.objects.filter(email_address=email).exists():
                messages.error(request, "❌ Email is already registered to another school.")
            elif Users.objects.filter(username=username).exists():
                messages.error(request,"Username is already taken")
            else:
                    admin_username = request.POST.get('username')
                    admin_email = email
                    admin_password = request.POST.get("confirm_password") 
                
                    # Save the new school
                    school = form.save()

                    # Generate admin credentials for this school
                     # from your form
                    school_instance = MasterSchool.objects.get(id=school.id)
                    # Create school admin in Users table
                    Users.objects.create_user(
                        school=school_instance,
                        username=admin_username,
                        email=admin_email,
                        password=admin_password,  # UserManager will hash
                        role='Admin',
                        school_name=school.school_name,
                    )

                    messages.success(
                        request,
                        f"✅ School '{school.school_name}' registered successfully. "
                        f"Admin username: {admin_username}"
                    )
                    send_mail(
                        subject="School Registration Received",
                        message=(
                            f"Dear {school.school_name},\n\n"
                            "Thank you for registering your school with ShuleBase. "
                            "Your registration is currently under review. "
                            "We will notify you once your account has been approved.\n\n"
                            "Best regards,\n"
                            "The ShuleBase Team"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admin_email],
                        fail_silently=True,
                    )
                    return redirect('waiting_page')
    else:
        form = SchoolRegistrationForm()

    return render(request, 'school/school_registration.html', {'form': form})

@login_required
def update_school(request):
    for _ in messages.get_messages(request):
        pass
    school = get_object_or_404(MasterSchool, id = request.session['school_id'])

    if request.method == "POST":
        form = SchoolRegistrationForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
                form.save()
                messages.success(request, "School details updated successfully ✅")
                return redirect("dashboard")  # or redirect to dashboard
        else:
            messages.error(request, "Please correct the errors below ❌")
    else:
        form = SchoolRegistrationForm(instance=school)
    return render(request, "school/update_school.html", {"form": form, "school": school})

def school_account(request):
    return render(request,'school/account.html')
