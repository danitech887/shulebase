from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404

from django.contrib import messages
from ..forms import RegisterTeacherForm
from ..models import TeacherInfo,Users,GradeStream
from django.db import models
from fpdf import FPDF
from django.db.models import Sum, Q

from django.utils.timezone import now
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import zipfile, io
import io
import zipfile
from collections import defaultdict

from decimal import Decimal
from django.db import connection, transaction, IntegrityError
from django.shortcuts import render, redirect
from ..forms import SchoolRegistrationForm


import pymysql
import os

import os
import pymysql






from django.contrib.auth.models import User
from ..models import LoginDetails, TeacherInfo
from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from ..forms import RegisterTeacherForm
from ..models import TeacherInfo, LoginDetails


from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth import get_user_model

from Students.forms import RegisterTeacherForm
from Students.models import TeacherInfo
from Students.utils.per_school_db_utils import get_school_db_alias_from_session


from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth.hashers import make_password

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.db import transaction

from ..forms import RegisterTeacherForm

from ..models import *
from ..utils.per_school_db_utils import get_school_db_alias_from_session


def teacher_reg_config(request):

    school_id = request.session.get('school_ic')
    school_instance = MasterSchool.objects.get(id = school_id)
    if request.method == 'POST':
        reg_format = request.POST.get('reg_format')
        if '/' in reg_format:
            messages.error(request,f'Invalid registration format use (-) instead')

        else:
            RegConfig.objects.update_or_create(
                school = school_instance,
                reg_format = reg_format,
                target_type = 'teacher'
            )
            messaages.success(request,f'teacher registration format: {reg_format} updated')
            return redirect('register_teacher')



def register_teacher(request):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get('school_id')
    alias = get_school_db_alias_from_session(request)

    # Preload existing teachers
    registered_teachers = TeacherInfo.objects.filter(school_id=school_id)
    existing_regnos = set(registered_teachers.values_list('registration_no', flat=True))

    # Generate the next available registration number (auto-fill)
    def get_next_registration_number(existing_regnos):
        reg_format = RegConfig.objects.filter(school_id = school_id,target_type = 'teacher').first()
        formt = reg_format.reg_format.upper() if reg_format != None else ''
        for i in range (1,500):
            reg_no = f'{formt}{i:02d}'

            if reg_no not in existing_regnos:
                return reg_no
            return None
            


    suggested_regno = get_next_registration_no(existing_regnos)

    today = timezone.now().date()

    if request.method == 'POST':
        form = RegisterTeacherForm(request.POST)

        if form.is_valid():
            username = request.POST.get('username')
            password = request.POST.get('password')
            email = request.POST.get('email')
            regno = form.cleaned_data.get('registration_no') or suggested_regno
            type_of_user = 'Teacher'

            # Uniqueness checks
            if Users.objects.filter(school_id=school_id, username=username).exists():
                messages.error(request, "❌ Username already exists. Please choose another.")
            elif TeacherInfo.objects.filter(school_id=school_id, registration_no=regno).exists():
                messages.error(request, f"❌ Teacher with registration no {regno} already exists.")
            else:
                try:
                    school_instance = MasterSchool.objects.get(id = school_id)
                    with transaction.atomic():
                        # Save teacher info
                        teacher = form.save(commit=False)
                        teacher.school = school_instance
                        
                        # Enforce phone number format
                        s_phone = str(teacher.phone)
                        if s_phone.startswith('0'):
                            s_phone = '254' + s_phone[1:]
                        elif not s_phone.startswith('254'):
                            s_phone = '254' + s_phone
                        teacher.phone = s_phone[:12]
                        
                        teacher.registration_no = regno
                        teacher.date_of_registration = today
                        teacher.save()

                        # Save corresponding user
                        Users.objects.create(
                            school=school_instance,
                            username=username,
                            school_name=alias,
                            role=type_of_user,
                            password=make_password(password),
                            email=email,
                            registration_no=regno,
                        )
                        messages.success(
                            request,
                            f"✅ Teacher {username} registered successfully with ID {regno}"
                        )
                        return redirect("register_teacher")

                except Exception as e:
                    messages.error(request, f"⚠️ Failed to register teacher: {str(e)}")
        else:
            messages.error(request, "❌ Invalid form submission. Please check inputs.")
    else:
        # Prefill the form with the next reg no
        form = RegisterTeacherForm(initial={'registration_no': suggested_regno})

    teachers = TeacherInfo.objects.filter(school_id=school_id)

    reg_format = RegConfig.objects.filter(school_id = school_id,target_type = 'teacher').first()

    
    formt = reg_format.reg_format.upper() if reg_format != None else ''
    return render(
        request,
        "teacher/register_teacher.html",
        {
            'form': form,
            'teachers': teachers,
            'suggested_regno': suggested_regno,
            'reg_format': formt
        },
    )


    
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..models import TeacherInfo, TeacherAttendance, TeachersRole


from ..forms import TeacherAttendanceForm
from django.utils import timezone

@login_required

def teacher_attendance(request):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get("school_id")
    school_instance = MasterSchool.objects.get(id = school_id)
    today = timezone.localdate()

    # --- Filtering inputs (for bottom table) ---
    term = request.GET.get("term", "").strip()
    filter_date = request.GET.get("date", "").strip()

    teachers = TeacherInfo.objects.filter(school_id=school_id)

    # Attendance for today (used in top form)
    today_records = TeacherAttendance.objects.filter(
        school=school_id, date_of_attendance=today
    )
    attendance_map = {att.registration_no_id: att for att in today_records}

    # --- Saving attendance (top form) ---
    if request.method == "POST":
        from datetime import date

        saved_count, skipped_count = 0, 0
        term_val = request.POST.get("term")
        date_val = request.POST.get('date_of_attendance')

        if not term_val:
            messages.error(request, "⚠️ Please select a valid term")
        else:
            for teacher in teachers:
                reg_no = teacher.registration_no
                status = request.POST.get(f"status_{reg_no}")
                 
                time_in = request.POST.get(f"time_in_{reg_no}")

                # Skip incomplete submissions
                if not (status and date_val):
                    continue

                # Prevent duplicates
                if reg_no in attendance_map:
                    skipped_count += 1
                    continue

                # Normalize fields
                att_date = date.fromisoformat(date_val)
                if status == "Absent":
                    time_in = None

                TeacherAttendance.objects.create(
                    school=school_instance,
                    registration_no=teacher,
                    status=status,
                    date_of_attendance=att_date,
                    time_in=time_in,
                    term=term_val,
                )
                saved_count += 1

            messages.success(
                request,
                f"✅ Attendance saved for {saved_count} teacher(s). ⏭️ {skipped_count} already recorded.",
            )
            return redirect("teacher_attendance")

    # --- Records for bottom table ---
    records = TeacherAttendance.objects.filter(school_id=school_id).select_related(
        "registration_no"
    )

    if filter_date == "today":
        records = records.filter(date_of_attendance=today)
    if term:
        records = records.filter(term=term)

    records = records.order_by("-date_of_attendance", "registration_no__first_name")

    # --- Context ---
    teacher_list = [
        {"teacher": teacher, "attendance": attendance_map.get(teacher.registration_no)}
        for teacher in teachers
    ]

    return render(
        request,
        "teacher/teacher_attendance.html",
        {
            "teacher_list": teacher_list,
            "today": today,
            "now": timezone.localtime(),
            "records": records,
            "term": term,
            "filter_date": filter_date,
        },
    )

from django.shortcuts import render
from django.utils import timezone
from ..models import TeachingProgress  # assuming this is your model

from django.shortcuts import render
from django.utils import timezone

@login_required
def delete_teacher(request, reg_no):
    alias = get_school_db_alias_from_session(request)
    school_id = request.session.get('school_id')

    teacher = get_object_or_404(TeacherInfo.objects.filter(school_id=school_id), registration_no=reg_no)

    if request.method == 'POST':
        teacher.delete()
        messages.success(request, "teacher deleted successfully")
        return redirect('register_teacher')

    return render(request, 'teacher/delete_teacher.html', {'teacher': teacher})

def teacher_dashboard(request):
    today = timezone.now().date()
    for _ in messages.get_messages(request):
        pass
    alias = get_school_db_alias_from_session(request)
    school_id = request.session.get('school_id')

    total_teachers = TeacherInfo.objects.filter(school_id = school_id).count()
    present_today = TeacherAttendance.objects.filter(school_id = school_id,date_of_attendance=now().date(), status='Present').count()
    on_leave = TeacherAttendance.objects.filter(school_id = school_id,date_of_attendance=now().date(), status='Absent').count()

    # --- Filters (GET) ---
    grade   = (request.GET.get("grade") or "").strip()
    stream  = (request.GET.get("stream") or "").strip()
    subject = (request.GET.get("subject") or "").strip()
    status  = (request.GET.get("status") or "").strip()

    # Base queryset
    qs = TeachingProgress.objects.filter(school_id = school_id).all().order_by("-grade")

    # Apply case-insensitive filters (more forgiving)
    if grade:
        qs = qs.filter(grade__iexact=grade)
    if stream:
        qs = qs.filter(stream__iexact=stream)
    if subject:
        qs = qs.filter(subject__iexact=subject)
    if status:
        qs = qs.filter(status__iexact=status)

    # Filter options (exclude empty/nulls)
    def distinct_nonempty(field):
        return (
            TeachingProgress.objects
            .filter(school_id = school_id)
            .exclude(**{f"{field}__isnull": True})
            .exclude(**{f"{field}__exact": ""})
            .values_list(field, flat=True)
            .distinct()
            .order_by(field)
        )

    grades   = distinct_nonempty("grade")
    streams  = distinct_nonempty("stream")
    subjects = distinct_nonempty("subject")
    statuses = distinct_nonempty("status")


    return render(request, "teacher/teacher_dashboard.html", {
        # existing dashboard context can still be added here
        "progress_list": qs,
        "grades": grades,
        "streams": streams,
        "subjects": subjects,
        "statuses": statuses,
        "filter_grade": grade,
        "filter_stream": stream,
        "filter_subject": subject,
        "filter_status": status,
        "total_teachers": total_teachers,
        "present_today": present_today,
        "on_leave": on_leave,
    })


from ..models import LearningArea


# LOWER_SUBJECTS = [
#     'Mathematics', 'English', 'Kiswahili', 'Environmental Activities', 'Integrated Creative','Cre'
# ] 

UPPER_SUBJECTS = [
    'Mathematics', 'English', 'Kiswahili', 'Science & Technology', 'Cre', 'Agriculture & Nutrition', 'Creative Arts','Social Studies'
]
JUNIOR_SUBJECTS = [
    'Mathematics', 'English', 'Kiswahili', 'Cre', 'Agriculture & Nutrition', 'Creative Arts', 'Pretech/Bs/Comps', 'Integrated Science','Social Studies'
]
LOWER_GRADES = ['PP1', 'PP2', 'Grade 1', 'Grade 2', 'Grade 3']
UPPER_GRADES = ['Grade 4', 'Grade 5', 'Grade 6']
JUNIOR_GRADES = ['Grade 7', 'Grade 8', 'Grade 9']
STREAMS = ['Stream 1', 'Stream 2', 'Stream 3', 'Stream 4']


from django.views.decorators.http import require_POST
from django.http import JsonResponse

import json 
@login_required

def manage_learning_areas(request):
    school_id = request.session.get('school_id')
    
    if request.method == "POST":
        action = request.POST.get('action')
        combat_data_json = request.POST.get('combat_data')

        # --- Handle Edit ---
        if action == 'edit':
            area_id = request.POST.get('id')
            name = request.POST.get('name')
            grade_level = request.POST.get('grade_level')
            category = request.POST.get('category')
            
            if not (area_id and name and grade_level):
                return JsonResponse({'success': False, 'message': 'Missing fields'}, status=400)

            try:
                area = get_object_or_404(LearningArea, id=area_id, school_id=school_id)
                area.name = name
                area.grade_level = grade_level
                area.category = category
                area.save()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)

        # --- Handle Delete ---
        elif action == 'delete':
            area_id = request.POST.get('id')
            if not area_id:
                return JsonResponse({'success': False, 'message': 'Missing ID'}, status=400)
            
            try:
                area = get_object_or_404(LearningArea, id=area_id, school_id=school_id)
                area.delete()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
        
        # --- Handle Bulk Add ---
        elif combat_data_json:
            try:
                # Convert JSON string back to a Python List
                combat_data = json.loads(combat_data_json)
                
                with transaction.atomic():
                    for item in combat_data:
                        # We use .get() and provide a fallback string to prevent 'NoneType' errors
                        name = item.get('name', '').strip()
                        grade_level = item.get('level', '').strip()
                        category = item.get('category', 'General').strip()

                        if name and grade_level:
                            # Logic to create or update
                            LearningArea.objects.update_or_create(
                                school_id=school_id,
                                name=name,
                                grade_level=grade_level,
                                defaults={
                                    'category': category,
                                    
                                }
                            )
                
                messages.success(request, "Learning Area Combat configured successfully!")
                
            except Exception as e:
                messages.error(request, f"System Error: {str(e)}")
        else:
             messages.error(request, "No data received. Please add subjects to the list first.")

    return redirect('role_management')


@login_required
def role_management(request):
    school_id = request.session.get('school_id')
    
    for _ in messages.get_messages(request):
        pass
    alias = get_school_db_alias_from_session(request)
    
    # --- Filter Logic ---
    approved_roles_qs = TeachersRole.objects.filter(school_id=school_id).select_related('registration_no')

    t_name = request.GET.get('teacher_name', '').strip()
    grade_filter = request.GET.get('grade', '').strip()
    stream_filter = request.GET.get('stream', '').strip()
    subj_filter = request.GET.get('subject', '').strip()

    if t_name:
        approved_roles_qs = approved_roles_qs.filter(
            Q(registration_no__first_name__icontains=t_name) | 
            Q(registration_no__surname__icontains=t_name)
        )
    if grade_filter:
        approved_roles_qs = approved_roles_qs.filter(grade=grade_filter)
    if stream_filter:
        approved_roles_qs = approved_roles_qs.filter(stream=stream_filter)
    if subj_filter:
        approved_roles_qs = approved_roles_qs.filter(subject__icontains=subj_filter)

    approved_roles = approved_roles_qs.order_by('grade', 'stream')
    teachers = TeacherInfo.objects.filter(school_id = school_id).all()

    # Prepare roles with subjects as a list
    roles_with_subjects = []

    for role in approved_roles:
        roles_with_subjects.append({
            'id': role.id,
            'teacher': role.registration_no,
            'grade': role.grade,
            'stream': role.stream,
            'type_of_teacher': role.type_of_teacher,
            'subjects': role.subject.split(", ") if role.subject else []
        })

    try:
        grades = list(GradeStream.objects.filter(school_id = school_id).values_list('grade', flat=True).distinct().order_by('grade'))
    except Exception:
        grades = []

    LOWER_SUBJECTS = list(LearningArea.objects.filter(school_id = school_id,grade_level = 'Lower Primary').values_list('name',flat=True).distinct())
    UPPER_SUBJECTS = list(LearningArea.objects.filter(school_id = school_id,grade_level = 'Upper Primary').values_list('name',flat=True).distinct())
    JUNIOR_SUBJECTS = list(LearningArea.objects.filter(school_id = school_id,grade_level = 'Junior Secondary').values_list('name',flat=True).distinct())
    CATEGORY_CHOICES = ['Languages','Sciences','Humanities','Technical / Applied','Creative Arts & Sports',
    ]
    REQUIRED_LEVELS = ['Lower Primary', 'Upper Primary', 'Junior Secondary']
    learning_areas = LearningArea.objects.filter(school_id = school_id)



    context = {
        'teachers': teachers,
        'approved_roles': roles_with_subjects,
        'grades': grades,
        'lower_subjects': LOWER_SUBJECTS,
        'upper_subjects': UPPER_SUBJECTS,
        'junior_subjects': JUNIOR_SUBJECTS,
        'lower_grades': LOWER_GRADES,
        'upper_grades': UPPER_GRADES,
        'junior_grades': JUNIOR_GRADES,
        'streams': STREAMS, 
        'categories': CATEGORY_CHOICES,
        'grade_levels': REQUIRED_LEVELS,
        'learning_areas': learning_areas,
    }
    return render(request, 'teacher/role_management.html', context)

from django.views.decorators.http import require_POST
from django.db import transaction

@login_required

@require_POST
def approve_role(request):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get("school_id")
    alias = get_school_db_alias_from_session(request)
    school_instance = MasterSchool.objects.get(id = school_id)

    role_id = request.POST.get("role_id")
    reg_no = request.POST.get("registration_no")
    grade = request.POST.get("grade")
    stream = request.POST.get("stream")
    type_of_teacher = request.POST.get("type_of_teacher")
    subjects = request.POST.getlist("subjects[]")  # JS sends as array

    # --- Validation ---
    if not (reg_no and grade and stream and type_of_teacher):
        return JsonResponse(
            {"success": False, "message": "⚠️ Missing required fields."}, status=400
        )
    if not subjects and type_of_teacher != "Class Teacher":
        return JsonResponse(
            {"success": False, "message": "⚠️ Please select at least one subject."},
            status=400,
        )

    try:
        with transaction.atomic():
            # Restrict: Only one class teacher per grade+stream
            ct_query = TeachersRole.objects.filter(
                school=school_instance,
                grade=grade,
                stream=stream,
                type_of_teacher="Class Teacher",
            )
            if role_id:
                ct_query = ct_query.exclude(id=role_id)

            if (
                type_of_teacher == "Class Teacher"
                and ct_query.exists()
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"🚫 A class teacher is already assigned for {grade}-{stream}.",
                    },
                    status=409,
                )

            # Restrict: Only one teacher per subject per grade+stream+type
            for subject in subjects:
                st_query = TeachersRole.objects.filter(
                    school=school_id,
                    grade=grade,
                    stream=stream,
                    subject=subject,
                    type_of_teacher=type_of_teacher,
                )
                if role_id:
                    st_query = st_query.exclude(id=role_id)

                if st_query.exists():
                    return JsonResponse(
                        {
                            "success": False,
                            "message": f"🚫 {subject} already assigned for {grade}-{stream}.",
                        },
                        status=409,
                    )

            if role_id:
                # Update existing role
                role = get_object_or_404(TeachersRole, id=role_id, school=school_instance)
                role.registration_no_id = reg_no
                role.grade = grade
                role.stream = stream
                role.type_of_teacher = type_of_teacher
                role.subject = ",".join(subjects) if subjects else None
                role.save()
                message = "✅ Role updated successfully!"
            else:
                # Create new role
                TeachersRole.objects.create(
                    school=school_instance,
                    registration_no_id=reg_no,
                    grade=grade,
                    stream=stream,
                    type_of_teacher=type_of_teacher,
                    subject=",".join(subjects) if subjects else None,
                )
                message = "✅ Role approved successfully!"

        return JsonResponse(
            {"success": True, "message": message}
        )

    except Exception as e:
        print('error', e)
        return JsonResponse(
            {"success": False, "message": f"⚠️ Failed to approve role: {str(e)}"},
            status=500,
        )

@require_POST
@login_required
def remove_role(request):

    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    role_id = request.POST.get('role_id')
    alias = get_school_db_alias_from_session(request)
    try:
        role = TeachersRole.objects.get(school_id = school_id,id=role_id)
        role.delete()
        return JsonResponse({'success': True, 'message': 'Role removed successfully.'})
    except TeachersRole.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Role not found.'})
