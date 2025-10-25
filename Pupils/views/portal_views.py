import logging
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from ..utils.per_school_db_utils import get_school_db_alias_from_session
from ..models import (
    TeacherInfo,
    TeachersRole,
    Marks,
    TeachingProgress,
    PupilAttendance,
    StudentInfo,
    MasterSchool
)
from ..forms import TeachingProgressForm,RegisterTeacherForm

logger = logging.getLogger(__name__)


@login_required
def teacher_portal(request):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get('school_id')
    
    email = request.session.get("email")
    print(f"Session email: {email}")
    alias = get_school_db_alias_from_session(request)
    try:
        teacher = TeacherInfo.objects.filter(school_id = school_id).get(registration_no = request.session.get('teacher_no'))
    except TeacherInfo.DoesNotExist:
        teacher = None
    logger.debug(f"Logged in teacher: {teacher}")



    roles = (
        TeachersRole.objects.filter(school_id = school_id,registration_no=teacher)
        if teacher else []
    )

    subjects = set()
    for role in roles:
        if role.subject:
            for subj in role.subject.split(","):
                subj = subj.strip()
                if subj:
                    subjects.add(subj)


    completed = (
        TeachingProgress.objects
        .filter(school_id = school_id,registration_no=teacher, status="Completed")
        .count()
        if teacher else 0
    )
    ongoing = (
        TeachingProgress.objects
        .filter(school_id = school_id,registration_no=teacher, status="Ongoing")
        .count()
        if teacher else 0
    )

    class_teacher_roles = TeachersRole.objects.filter(school_id = school_id,type_of_teacher="Class Teacher")
    is_class_teacher = TeachersRole.objects.filter(
        school = school_id,
        registration_no=teacher, type_of_teacher="Class Teacher"
    ).exists()
    grade = class_teacher_roles.first().grade if class_teacher_roles else None
    stream = class_teacher_roles.first().stream if class_teacher_roles else None

    present_today = (
        PupilAttendance.objects
        .filter(
            school = school_id,
            registration_no__in=StudentInfo.objects
            .filter(school_id = school_id,grade=grade, stream=stream)
            .values_list("registration_no", flat=True),
            date_of_attendance=timezone.now().date(),
            status="Present",
        )
        .count()
        if grade and stream else 0
    )
    absent_today = (
        PupilAttendance.objects
        .filter(
            school_id = school_id,
            registration_no__in=StudentInfo.objects
            .filter(school_id = school_id,grade=grade, stream=stream)
            .values_list("registration_no", flat=True),
            date_of_attendance=timezone.now().date(),
            status="Absent",
        )
        .count()
        if grade and stream else 0
    )

    subject_roles = TeachersRole.objects.filter(school_id = school_id,type_of_teacher="Subject Teacher")

    context = {
        "teacher": teacher,
        "roles": roles,
        "is_class_teacher": is_class_teacher,
        "class_teacher_roles": class_teacher_roles,
        "subject_roles": subject_roles,
        "subjects": subjects,
        "present_today": present_today,
        "absent_today": absent_today,
        "completed": completed,
        "ongoing": ongoing,
    }
    return render(request, "teacher_portal/portal.html", context)

@login_required
def teacher_account(request):
    teacher_no = request.session.get('teacher_no')
    school_id = request.session.get('school_id')

    if not teacher_no or not school_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login')

    try:
        teacher = TeacherInfo.objects.get(registration_no=teacher_no, school_id=school_id)
    except TeacherInfo.DoesNotExist:
        messages.error(request, "Teacher record not found.")
        return redirect('login')
    school_instance = MasterSchool.objects.get(id = school_id)
    if request.method == "POST":
        form = RegisterTeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            # ✅ form.save() will update, not create
            obj = form.save(commit=False)
            obj.registration_no = teacher_no
            obj.date_of_registration = teacher.date_of_registration
            obj.school = school_instance
            obj.save()

            messages.success(request, "Details updated successfully.")
            return redirect("teacher_account")
        else:
            messages.error(request, "Error updating details. Please check the form fields.")
    else:
        form = RegisterTeacherForm(instance=teacher)

    return render(request, "teacher_portal/update_details.html", {
        "form": form,
        "teacher": teacher,
        "teacher_no": teacher_no,
    })



@login_required
def attendance(request):
    for _ in messages.get_messages(request):
        pass

    school_id = request.session.get('school_id')
    school_instance = MasterSchool.objects.get(id = school_id)

    today = timezone.now().date()
    time = timezone.now().strftime("%H:%M")
    year = today.year

    grade = request.GET.get("grade", "")
    stream = request.GET.get("stream", "")

    email = request.session.get("email")
    print(f"Session email: {email}")

    alias = get_school_db_alias_from_session(request)
    try:
        teacher = TeacherInfo.objects.get(school = school_instance,registration_no = request.session.get('teacher_no'))
    except TeacherInfo.DoesNotExist:
        teacher = None
    logger.debug(f"Teacher taking attendance: {teacher}")

    grades = TeachersRole.objects.filter(
        school_id = school_id,
        registration_no=teacher, type_of_teacher="Class Teacher"
    ).values_list("grade", flat=True).distinct()
    streams = TeachersRole.objects.filter(
        school_id = school_id,
        registration_no=teacher, type_of_teacher="Class Teacher"
    ).values_list("stream", flat=True).distinct()
    pupils = StudentInfo.objects.filter(school_id = school_id,grade=grade, stream=stream).order_by("registration_no")

    attendance_recorded = set(
        PupilAttendance.objects
        .filter(school_id = school_id,registration_no__grade=grade, registration_no__stream=stream, date_of_attendance=today)
        .values_list("registration_no", flat=True)
    )

    filter_date = request.GET.get("filter_date")
    filter_term = request.GET.get("filter_term")

    attendance_records = PupilAttendance.objects.filter(
        school_id = school_id,
        registration_no__grade=grade, registration_no__stream=stream
    ).order_by("-date_of_attendance")

    if filter_date:
        attendance_records = attendance_records.filter(date_of_attendance=filter_date)
    if filter_term:
        attendance_records = attendance_records.filter(term=filter_term)

    pupil_map = {p.registration_no: p for p in StudentInfo.objects.filter(school_id = school_id).all()}
    for rec in attendance_records:
        rec.pupil = pupil_map.get(rec.registration_no)

    if request.method == "POST":
        attendance_data = []
        for pupil in pupils:
            if pupil.registration_no in attendance_recorded:
                continue
            status = request.POST.get(f"status_{pupil.registration_no}")
            if status:
                attendance_data.append(
                    PupilAttendance(
                        school = school_instance,
                        registration_no=pupil,
                       
                        date_of_attendance=today,
                        year=year,
                        time=time,
                        status=status,
                        term=request.POST.get("term_select", ""),
                    )
                )
        if attendance_data:
            PupilAttendance.objects.bulk_create(attendance_data)
            messages.success(request, "Attendance recorded successfully!")
        else:
            messages.info(request, "No new attendance to record.")
        return redirect("attendance")

    term_choices = ["Term 1", "Term 2", "Term 3"]
    return render(
        request,
        "teacher_portal/attendance.html",
        {
            "pupils": pupils,
            "today": today,
            "grade": grade,
            "grades": grades,
            "streams": streams,
            "stream": stream,
            "term_choices": term_choices,
            "filter_date": filter_date,
            "filter_term": filter_term,
            "attendance_records": attendance_records,
            "attendance_recorded": attendance_recorded,
        },
    )

from  django.db import connections


lower_grades = ["PP 1", "PP 2", "Grade 1", "Grade 2", "Grade 3"]
upper_grades = ["Grade 4", "Grade 5", "Grade 6"]
junior_grades = ["Grade 7", "Grade 8", "Grade 9"]

lower_subject_map = {
    "Mathematics": "mathematics",
    "English": "english",
    "Kiswahili": "kiswahili",
    "Environmental Activities": "environmental_activities",
    "Integrated Creative": "integrated_creative",
    "Cre": 'cre'
}
upper_subject_map = {
    "Mathematics": "mathematics",
    "English": "english",
    "Kiswahili": "kiswahili",
    "Science & Technology": "science_technology",
    "SST/CRE": "sst_cre",
    "Agriculture & Nutrition": "agri_nutrition",
    "Creative Arts": "creative_arts",
    "Cre": 'cre',
    'Social Studies': 'social_studies'
}
junior_subject_map = {
    "Mathematics": "mathematics",
    "English": "english",
    "Kiswahili": "kiswahili",
    "SST/CRE": "sst_cre",
    "Agriculture & Nutrition": "agri_nutrition",
    "Creative Arts": "creative_arts",
    "Pretech/Bs/Comps": "pretech_bs_computer",
    "Integrated Science": "integrated_science",
    "Cre": 'cre',
    'Social Studies': 'social_studies'
}




@login_required
def record_marks(request):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get('school_id')
    school_instance =  MasterSchool.objects.get(id = school_id)

    email = request.session.get("email")
    print(f"Session email: {email}")
    

    alias = get_school_db_alias_from_session(request)
    try:
        teacher = TeacherInfo.objects.get(school = school_instance,registration_no = request.session.get('teacher_no'))
    except TeacherInfo.DoesNotExist:
        teacher = None
    logger.debug(f"Teacher recording marks: {teacher}")

    roles = TeachersRole.objects.filter(school_id = school_id,registration_no=teacher)



    subjects = set()
    for role in roles:
        if role.subject:
            for subj in role.subject.split(","):
                subj = subj.strip()
                if subj:
                    subjects.add(subj)

    grades = roles.values_list("grade", flat=True).distinct()
    streams = roles.values_list("stream", flat=True).distinct()

    


    selected_grade = request.GET.get("grade", "")
    selected_stream = request.GET.get("stream", "")
    selected_term = request.GET.get("term", "")
    selected_exam_type = request.GET.get("exam_type", "")
    selected_subject = request.GET.get("subject", "")

    students = (
        StudentInfo.objects
        .filter(school_id = school_id,grade=selected_grade, stream=selected_stream)
        .order_by("registration_no")
        if selected_grade and selected_stream else []
    )

    if selected_grade in lower_grades:
        subject_field_map = lower_subject_map
    elif selected_grade in upper_grades:
        subject_field_map = upper_subject_map
    elif selected_grade in junior_grades:
        subject_field_map = junior_subject_map
    else:
        subject_field_map = {}

    subject_field = subject_field_map.get(selected_subject)

    marks_map = {}
    if selected_grade and selected_stream and selected_term and selected_exam_type and subject_field:
        marks_qs = Marks.objects.filter(
            school_id=school_id,
            registration_no__in = students,
            term=selected_term,
            type_of_exam=selected_exam_type,
        )

        for m in marks_qs:
            value = getattr(m, subject_field, None)
            if value is not None:
                # if registration_no is a FK, get the actual string
                reg_no = (
                    m.registration_no.registration_no
                    if hasattr(m.registration_no, 'registration_no')
                    else m.registration_no
                )
                marks_map[reg_no] = value

    if request.method == "POST" and students and subject_field:
        for student in students:
            reg_no = student.registration_no
            mark = request.POST.get(f"mark_{reg_no}")
            if mark not in (None, ""):
                mark = int(mark)
                obj, created = Marks.objects.get_or_create(
                    school = school_instance,
                    registration_no=student,
                    term=selected_term,
                    type_of_exam=selected_exam_type,
                    defaults={subject_field: mark},
                )
            
                if not created:
                    setattr(obj, subject_field, mark)
                    obj.save()
        messages.success(request, "Marks recorded/updated successfully!")
        return redirect(
            request.path
            + f"?grade={selected_grade}&stream={selected_stream}&term={selected_term}&exam_type={selected_exam_type}&subject={selected_subject}"
        )

    term_choices = ["Term 1", "Term 2", "Term 3"]
    exam_types = ["Opener", "Mid Term", "End Term"]

    print("Marks: ",marks_map)

    context = {
        "grades": grades,
        "streams": streams,
        "subjects": sorted(subjects),
        "students": students,
        "marks_map": marks_map,
        "term_choices": term_choices,
        "exam_types": exam_types,
        "selected_grade": selected_grade,
        "selected_stream": selected_stream,
        "selected_term": selected_term,
        "selected_exam_type": selected_exam_type,
        "selected_subject": selected_subject,
    }
    return render(request, "teacher_portal/record_marks.html", context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import Strand
from ..forms import StrandForm

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import Strand
from ..forms import StrandForm

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import Strand
from ..forms import StrandForm

@login_required
def strand_list(request):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get('school_id')
    strands = Strand.objects.filter(school_id = school_id,created_by = request.user).all().order_by("subject", "name")
    teacher = request.session.get('teacher_no')
    roles = TeachersRole.objects.filter(school_id = school_id,registration_no=teacher)
    grades = []
    streams = []
    subjects = set()
    for role in roles:
        if role.subject:
            grades.append(role.grade)
            streams.append(role.stream)
            for subj in role.subject.split(","):
                subj = subj.strip()
                if subj:
                    subjects.add(subj)
    
    form = StrandForm()
    return render(request, "teacher_portal/strands_list.html", {"strands": strands, "form": form,"subjects": subjects,"grades": grades,"streams":streams})


@login_required 
def strand_add(request):
    school_id = request.session.get('school_id')
    school_instance = MasterSchool.objects.get(id = school_id)
    for _ in messages.get_messages(request):
        pass
    
    if request.method == "POST":
        subject = request.POST.get("subject")
        form = StrandForm(request.POST)
        
        if form.is_valid():
            strand = form.save(commit=False)
            strand.school = school_instance
            strand.subject = subject
            strand.created_by = request.user
            strand.save()
            messages.success(request, "Strand added successfully.")
        else:
            messages.error(request, "Error adding strand.")
    else:
        print("Form is not valid",form.errors)
    return redirect("strand_list")


from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from ..forms import StrandForm
from ..models import Strand,SubStrandMark

@login_required
def strand_edit(request, pk):
    for _ in messages.get_messages(request):
        pass
    strand = get_object_or_404(Strand, pk=pk)

    if request.method == "POST":
        form = StrandForm(request.POST, instance=strand)
        if form.is_valid():
            form.save()
            messages.success(request, "Strand updated successfully.")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return HttpResponse('success')  # AJAX knows it worked
            return redirect('strand_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return render(request, 'teacher_portal/strand_edit.html', {'form': form, 'strand': strand})
    else:
        form = StrandForm(instance=strand)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(request, 'teacher_portal/strand_edit.html', {'form': form, 'strand': strand})

    return render(request, 'teacher_portal/strand_edit.html', {'form': form})

@login_required
def strand_delete(request, pk):
    for _ in messages.get_messages(request):
        pass
    strand = get_object_or_404(Strand, pk=pk)
    if request.method == "POST":
        strand.delete()
        messages.success(request, "Strand deleted successfully.")
    return redirect("strand_list")


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from ..models import Strand, StudentInfo, SubStrandMark,SubStrand
from datetime import date


@login_required
@login_required
# def record_scores(request, strand_id):
#     school_id = request.session.get('school_id')
#     strand = get_object_or_404(Strand, pk=strand_id)
#     students = StudentInfo.objects.filter(school_id=school_id).order_by("registration_no")

#     term_choices = ["Term 1", "Term 2", "Term 3"]
#     year = date.today().year

#     # Track selected term for pre-fill and template state
#     selected_term = request.GET.get("term") or request.POST.get("term") or ""

#     # AJAX POST: save scores
#     if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
#         term = request.POST.get("term")
#         if not term:
#             return JsonResponse({"status": "error", "message": "Term is required."}, status=400)
#         if term not in term_choices:
#             return JsonResponse({"status": "error", "message": "Invalid term."}, status=400)

#         updated = 0
#         errors = []

#         for student in students:
#             field_name = f"score_{student.registration_no}"
#             raw_value = request.POST.get(field_name)
#             if raw_value in (None, ""):
#                 continue
#             print("Raw valus: ",raw_value)
#             try:
#                 # Convert to Decimal with two decimal places
#                 score_value = Decimal(str(raw_value)).quantize(Decimal("0.01"))
#                 if score_value < 0:
#                     raise ValueError("Score cannot be negative")

#                 SubStrandMark.objects.update_or_create(
#                     student=student,
#                     strand=strand,
#                     term=term,
#                     year=year,
#                     defaults={"score": score_value},
#                 )
#                 updated += 1
#             except Exception as e:
#                 logger.exception("Error saving score for %s", student.registration_no)
#                 errors.append(
#                     {"registration_no": student.registration_no, "error": str(e)}
#                 )

#         status = "success" if not errors else "partial"
#         return JsonResponse({"status": status, "updated": updated, "errors": errors})

#     # GET: pre-fill existing scores (term-aware)
#     # Batch-fetch marks for all students, current strand/year and optionally the selected term
#     marks_qs = SubStrandMark.objects.filter(
#         student__school_id=school_id,
#         strand=strand,
#         year=year,
#     )
#     if selected_term:
#         marks_qs = marks_qs.filter(term=selected_term)

#     # Build a map of reg_no -> score
#     mark_map = {
#         m.student.registration_no: m.score
#         for m in marks_qs.select_related("student")
#     }
#     scores = {s.registration_no: mark_map.get(s.registration_no, "") for s in students}

#     return render(
#         request,
#         "teacher_portal/scores_form.html",
#         {
#             "strand": strand,
#             "students": students,
#             "scores": scores,
#             "term_choices": term_choices,
#             "selected_term": selected_term,
#             "year": year,
#         },
#     )


@login_required
def sub_strands_view(request, strand_id,grade,stream):
    for _ in messages.get_messages(request):
        pass
    logger = logging.getLogger(__name__)
    school_id = request.session['school_id']
    teacher_no = request.session.get('teacher_no')
    strand = get_object_or_404(Strand, pk=strand_id,grade = grade,stream = stream)
    
    
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()

        if not name:
            return JsonResponse({"status": "error", "message": "Name is required."}, status=400)

        try:
            SubStrand.objects.create(
                strand=strand,
                name=name,
                description=description or None,
                created_by=request.user,
            )
            return JsonResponse({"status": "success"})
        except Exception as e:
            logger.exception("Failed to create SubStrand for strand_id=%s", strand_id)
            return JsonResponse(
                {"status": "error", "message": "Failed to create sub strand."},
                status=500,
            )

    sub_strands = strand.sub_strands.all().order_by("created_at")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(
            request,
            "teacher_portal/sub_strands_list.html",
            {"strand": strand, "sub_strands": sub_strands},
        )

    return render(
        request,
        "teacher_portal/sub_strands_page.html",
        {"strand": strand, "sub_strands": sub_strands},
    )

from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.template.loader import render_to_string

@require_http_methods(["GET", "POST"])
@login_required
@login_required


def edit_substrand_view(request, sub_strand_id):
    """Handle inline edit of a Sub-Strand (AJAX)."""
    if request.method == "POST":
        try:
            sub_strand = get_object_or_404(SubStrand, pk=sub_strand_id)
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()

            if not name:
                return JsonResponse({
                    "status": "error",
                    "message": "Sub-strand name is required."
                }, status=400)

            # ✅ Update and save
            sub_strand.name = name
            sub_strand.description = description
            sub_strand.save()

            return JsonResponse({
                "status": "success",
                "message": "Sub-strand updated successfully.",
                "data": {
                    "id": sub_strand.id,
                    "name": sub_strand.name,
                    "description": sub_strand.description,
                    "updated_at": sub_strand.updated_at.strftime("%b %d, %Y") if hasattr(sub_strand, "updated_at") else ""
                }
            })
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=500)
    
    return JsonResponse({
        "status": "error",
        "message": "Invalid request method."
    }, status=405)



from django.views.decorators.csrf import csrf_exempt
@login_required
@csrf_exempt
def record_substrand_scores(request, sub_strand_id,grade,stream):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get('school_id')
    sub_strand = get_object_or_404(SubStrand, pk=sub_strand_id)
    strand = sub_strand.strand
    print("Grade: ",grade)
    print("Stream: ",stream)
    
    students = StudentInfo.objects.filter(school_id=school_id,grade = grade,stream = stream).order_by('registration_no')

    term_choices = ['Term 1', 'Term 2', 'Term 3']
    current_year = str(datetime.now().year)

    # ---- Handle POST (AJAX or normal)
    if request.method == "POST":
        term = (request.POST.get('term') or '').strip()
        if term not in term_choices:
            return JsonResponse({'status': 'error', 'message': 'Valid term is required.'}, status=400)

        updated = 0
        for student in students:
            raw_value = request.POST.get(f'score_{student.registration_no}')
            remark = request.POST.get(f'remark_{student.registration_no}')
            if not raw_value:
                continue
            try:
                score_value = float(raw_value)
                SubStrandMark.objects.update_or_create(
                    student=student,
                    sub_strand=sub_strand,
                    term=term,
                    year=current_year,
                    defaults={
                        'score': score_value,
                        'remark': remark,
                        'recorded_by': request.user
                    }
                )
                updated += 1
            except Exception as e:
                logger.exception("Error saving score for %s", student.registration_no)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "success", "updated": updated})
        else:
            # fallback for non-AJAX forms
            return redirect("strand_list")

    # ---- Handle GET
    selected_term = request.GET.get('term', '').strip()
    existing_qs = SubStrandMark.objects.filter(sub_strand=sub_strand, year=current_year)
    if selected_term:
        existing_qs = existing_qs.filter(term=selected_term)

    existing_scores = existing_qs.values('student__registration_no', 'score', 'remark')
    score_map = {row['student__registration_no']: row['score'] for row in existing_scores}
    remark_map = {row['student__registration_no']: row['remark'] for row in existing_scores}

    return render(request, 'teacher_portal/record_substrand_scores.html', {
        'sub_strand': sub_strand,
        'strand': strand,
        'students': students,
        'term_choices': term_choices,
        'scores': score_map,
        'remark': remark_map,
        'selected_term': selected_term,
    })

@login_required
def teaching_progress(request):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get('school_id')
    school_instance = MasterSchool.objects.get(id = school_id)

    email = request.session.get("email")
    print(f"Session email: {email}")
    

    alias = get_school_db_alias_from_session(request)
    try:
        teacher = TeacherInfo.objects.get(school = school_instance,registration_no = request.session.get('teacher_no'))
    except TeacherInfo.DoesNotExist:
        teacher = None




    roles = TeachersRole.objects.filter(school_id = school_id,registration_no=teacher)

    grade_choices = sorted(set((role.grade, role.grade) for role in roles))
    stream_choices = sorted(set((role.stream, role.stream) for role in roles))
    subject_set = set()
    for role in roles:
        if role.subject:
            subjects = [s.strip() for s in role.subject.split(",") if s.strip()]
            subject_set.update(subjects)
    subject_choices = sorted((subject, subject) for subject in subject_set)

    if request.method == "POST" and "add_progress" in request.POST:
        form = TeachingProgressForm(request.POST)
        form.fields["grade"].widget.choices = grade_choices
        form.fields["stream"].widget.choices = stream_choices
        form.fields["subject"].widget.choices = subject_choices
        if form.is_valid():
            progress = form.save(commit=False)
            progress.registration_no = teacher
            progress.school = school_instance
            progress.save()
            return redirect("teaching_progress")
    else:
        form = TeachingProgressForm()
        form.fields["grade"].widget.choices = grade_choices
        form.fields["stream"].widget.choices = stream_choices
        form.fields["subject"].widget.choices = subject_choices

    if request.method == "POST" and "update_progress" in request.POST:
        progress_id = request.POST.get("progress_id")
        qs = TeachingProgress.objects.filter(school_id = school_id).all()
        progress = get_object_or_404(qs, id=progress_id, registration_no=teacher)
        update_form = TeachingProgressForm(request.POST, instance=progress)
        update_form.fields["grade"].widget.choices = grade_choices
        update_form.fields["stream"].widget.choices = stream_choices
        update_form.fields["subject"].widget.choices = subject_choices
        if update_form.is_valid():
            update_form.save()
            return redirect("teaching_progress")

    progresses = TeachingProgress.objects.filter(school_id = school_id,registration_no=teacher)

    return render(
        request,
        "teacher_portal/teaching_progress.html",
        {
            "form": form,
            "progresses": progresses,
            "grade_choices": grade_choices,
            "stream_choices": stream_choices,
            "subject_choices": subject_choices,
        },
    )