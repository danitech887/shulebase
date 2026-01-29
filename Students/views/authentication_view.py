from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
import random, time
import smtplib
import ssl
 
from ..models import Users, MasterSchool, StudentInfo, Announcement, TeachersRole
from django.shortcuts import get_object_or_404

from .announcements_api import get_announcements





# -------------------------
# Password reset (email based)
# -------------------------

from django.core.mail import send_mail

def send_reset_email(to_email, reset_code):
    subject = "Password Reset Code"
    message = f"Your password reset code is: {reset_code}\n\nThis code will expire in 10 minutes."
    
    # Using the "No-reply" format we discussed
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    
    try:
        send_mail(
            subject, 
            message, 
            from_email, 
            [to_email], 
            fail_silently=False
        )
    except Exception as e:
        # Handle SSL Certificate Verify Failed error (common in dev/local envs)
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            try:
                # Create an unverified SSL context
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    if settings.EMAIL_USE_TLS:
                        server.starttls(context=context)
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    email_msg = f"Subject: {subject}\nFrom: {from_email}\nTo: {to_email}\n\n{message}"
                    server.sendmail(from_email, [to_email], email_msg)
            except Exception as fallback_e:
                raise e
        else:
            raise e

def reset_password(request):
    """
    Two-step reset:
    1. Enter email -> send code
    2. Enter code + new password -> reset password
    """
    for _ in messages.get_messages(request):
        pass
    if request.method == "POST":
        step = request.POST.get("step")

        # STEP 1: Enter email
        if step == "email":
            email = request.POST.get("email")
            try:
                user = Users.objects.get(email=email)
                reset_code = str(random.randint(100000, 999999))
                request.session["reset_email"] = email
                request.session["reset_code"] = reset_code
                request.session["reset_code_expiry"] = int(time.time()) + 600
                send_reset_email(email, reset_code)
                messages.success(request, "A reset code has been sent to your email.")
                return redirect("reset_password")
            except Users.DoesNotExist:
                messages.error(request, "No user with that email was found.")

        # STEP 2: Confirm reset
        elif step == "confirm":
            code = request.POST.get("code")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            saved_code = request.session.get("reset_code")
            expiry = request.session.get("reset_code_expiry")
            email = request.session.get("reset_email")

            if not (saved_code and expiry and email):
                messages.error(request, "Reset session expired. Please try again.")
                return redirect("reset_password")

            if int(time.time()) > expiry:
                messages.error(request, "Reset code expired. Please request again.")
                request.session.flush()
                return redirect("reset_password")

            if code != saved_code:
                messages.error(request, "Invalid reset code.")
                return redirect("reset_password")

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect("reset_password")

            try:
                user = Users.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                request.session.flush()
                messages.success(request, "Password reset successful. Please login.")
                return redirect("login")
            except Users.DoesNotExist:
                messages.error(request, "Something went wrong.")

    return render(request, "user/password_reset.html")


# -------------------------
# Login / Logout
# -------------------------

def _perform_login(request, user):
    """Helper to handle session setup after authentication."""
    login(request, user)
    school = MasterSchool.objects.filter(id=user.school.id).first()
    status = school.status
    
    if status == 'Approved':
        announcements = get_announcements(user.role.lower(), school.id)
        # Store basic info in session
        request.session["role"] = user.role.lower()
        request.session["school_id"] = user.school.id
        request.session["school_name"] = user.school.school_name
        request.session["address"] = user.school.address
        request.session["contact"] = user.school.contact
        request.session["email"] = user.email
        request.session["motto"] = user.school.motto
        request.session["logo_path"] = str(user.school.logo_path.url) if user.school.logo_path else None
        request.session['username'] = user.username
        request.session['announcements'] = announcements

        # Role specific session data
        if user.role.lower() == "teacher":
            request.session["registration_no"] = user.registration_no
            
            # Check if class teacher and store in session
            is_class_teacher = TeachersRole.objects.filter(
                registration_no=user.registration_no,
                school_id=user.school.id,
                type_of_teacher='Class Teacher'
            ).exists()
            request.session["is_class_teacher"] = is_class_teacher
        elif user.role.lower() == "student":
            request.session["registration_no"] = user.registration_no
            student = get_object_or_404(StudentInfo, school_id=user.school.id, registration_no=user.registration_no)
            request.session["student_name"] = f"{student.surname}, {student.first_name} {student.second_name}"
        elif user.role.lower() == "parent":
            request.session["parent_name"] = user.username
            parent = StudentInfo.objects.filter(phone=user.username).first()
            if parent:
                request.session["parent_name"] = parent.parent_name
        
        return True
    return False

def student_login(request):
    for _ in messages.get_messages(request): pass
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user:
            if user.role.lower() != 'student':
                messages.error(request, "❌ This login is for Students only.")
            elif _perform_login(request, user):
                return redirect('student_portal_dashboard')
            else:
                return redirect('waiting_page')
        else:
            messages.error(request, "❌ Invalid username or password")
    return render(request, "user/student_login.html")

def teacher_login(request):
    for _ in messages.get_messages(request): pass
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user:
            if user.role.lower() != 'teacher':
                messages.error(request, "❌ This login is for Teachers only.")
            elif _perform_login(request, user):
                return redirect('teacher_portal')
            else:
                return redirect('waiting_page')
        else:
            messages.error(request, "❌ Invalid username or password")
    return render(request, "user/teacher_login.html")

def parent_login(request):
    for _ in messages.get_messages(request): pass
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user:
            if user.role.lower() != 'parent':
                messages.error(request, "❌ This login is for Parents only.")
            elif _perform_login(request, user):
                return redirect('parent_portal_dashboard')
            else:
                return redirect('waiting_page')
        else:
            messages.error(request, "❌ Invalid username or password")
    return render(request, "user/parent_login.html")

def admin_login(request):
    # Reusing unified_login logic or creating specific one. 
    # For now, let's redirect to unified_login or create a specific one if needed.
    # But based on request, let's make a specific one.
    for _ in messages.get_messages(request): pass
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user:
            if user.role.lower() not in ['admin', 'systemowner']: # Assuming Admin/SystemOwner
                messages.error(request, "❌ This login is for Administrators only.")
            elif _perform_login(request, user):
                return redirect('dashboard')
            else:
                return redirect('waiting_page')
        else:
            messages.error(request, "❌ Invalid username or password")
    return render(request, "user/admin_login.html")

def unified_login(request):
    for _ in messages.get_messages(request):
        pass
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            school = MasterSchool.objects.filter(id = user.school.id).first()
            status = school.status
            if status == 'Approved':
                target_audiences = ['TEACHERS','STUDENTS','PARENTS']
                announcements = get_announcements(user.role.lower(),school.id)
                # Store basic info in session
                request.session["role"] = user.role.lower()
                request.session["school_id"] = user.school.id 
                request.session["school_name"] = user.school.school_name
                request.session["address"] = user.school.address
                request.session["contact"] = user.school.contact
                request.session["email"] = user.email
                request.session["motto"] = user.school.motto
                request.session["logo_path"] = str(user.school.logo_path.url) if user.school.logo_path else None

                request.session['username'] = username

                request.session['announcements'] = announcements
                

                # Redirect by role
                if user.role.lower() == "admin":
                    next_url = request.GET.get('next', 'dashboard')
                    return redirect(next_url)
                elif user.role.lower() == "teacher":
                    request.session["registration_no"] = user.registration_no 
                    next_url = request.GET.get('next', 'teacher_portal')
                    return redirect(next_url)
                elif user.role.lower() == "student":
                    request.session["registration_no"] = user.registration_no 
                    student = get_object_or_404(StudentInfo, school_id=user.school.id, registration_no=user.registration_no)
                    request.session["student_name"] = f"{student.surname}, {student.first_name} {student.second_name}"
                    print("Student Name in Session:", request.session["student_name"])
                    next_url = request.GET.get('next', 'student_portal_dashboard')
                    return redirect(next_url)
                elif user.role.lower() == "parent":
                    
                    request.session["parent_name"] = username
                    parent = StudentInfo.objects.filter(phone = username).first()
                    if parent:
                        parent_name = parent.parent_name
                        request.session["parent_name"] = parent_name
                        print('Parent Name in Session:', parent_name)
                    else:
                        messages.error(request,"❌ Invalid parent data")

                    next_url = request.GET.get('next', 'parent_portal_dashboard')
                    return redirect(next_url)
            else:
                return redirect('waiting_page')
        else:
            messages.error(request, "❌ Invalid username or password")

    # Determine image source based on user type
    image_source = "static/images/default_user.png"  # Default image
    if request.method == 'GET':
        if request.GET.get('next') == 'teacher_portal':
            image_source = "static/images/teacher.png"
        elif request.GET.get('next') == 'student_portal_dashboard':
            image_source = "static/images/student.png"
        elif request.GET.get('next') == 'parent_portal_dashboard':
            image_source = "static/images/parent.png"
        elif request.GET.get('next') == 'dashboard':
            image_source = "static/images/admin.png"

    return render(request, "user/login.html", {'image_source': image_source})

    
@login_required
def change_user_password(request):
    for _ in messages.get_messages(request):
        pass
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("change_password")

        user = request.user
        if not user.check_password(old_password):
            messages.error(request, "Old password is incorrect.")
            return redirect("change_password")

        user.set_password(new_password)
        user.save()
        messages.success(request, "Password updated successfully.")
        
        # Redirect to the correct account page based on user role
        role = request.user.role.lower()
        if role == 'teacher':
            return redirect('teacher_account')
        elif role in ['admin', 'systemowner']:
            return redirect('account')
        
        return redirect('login') # Fallback

    return render(request, "user/change_password.html")

@login_required
def change_username(request):
    for _ in messages.get_messages(request):
        pass
    if request.method == "POST":
        new_username = request.POST.get("new_username")
        password = request.POST.get("password")

        user = request.user
        
        if not user.check_password(password):
            messages.error(request, "❌ Incorrect password. Username not changed.")
            return redirect("change_password")

        if Users.objects.filter(username=new_username).exclude(id=user.id).exists():
            messages.error(request, "❌ Username is already taken.")
            return redirect("change_password")

        user.username = new_username
        user.save()
        messages.success(request, "✅ Username updated successfully.")

        # Redirect to the correct account page based on user role
        role = request.user.role.lower()
        if role == 'teacher':
            return redirect('teacher_account')
        elif role in ['admin', 'systemowner']:
            return redirect('account')

    # On GET or if POST fails validation checks above, redirect back to the form page
    return redirect("change_password")

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

def student_logout_view(request):
    
    logout(request)
    messages.success(request, "You have been logged out.")
    
    return redirect("student_login")

def teacher_logout_view(request):
    
    logout(request)
    messages.success(request, "You have been logged out.")
    
    return redirect("teacher_login")

def parent_logout_view(request):
    
    logout(request)
    messages.success(request, "You have been logged out.")
    
    return redirect("parent_login")

def admin_logout_view(request):
    
    logout(request)
    messages.success(request, "You have been logged out.")
    
    return redirect("admin_login")
    
    
    
    
