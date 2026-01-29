import logging
import re
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum, Avg, Count
from django.http import JsonResponse,HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from ..utils.per_school_db_utils import get_school_db_alias_from_session
from ..models import *
from ..forms import *

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
        teacher = TeacherInfo.objects.filter(school_id = school_id).get(registration_no = request.session.get('registration_no'))
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
        StudentAttendance.objects
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
        StudentAttendance.objects
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
    registration_no = request.session.get('registration_no')
    school_id = request.session.get('school_id')

    if not registration_no or not school_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('login')

    try:
        teacher = TeacherInfo.objects.get(registration_no=registration_no, school_id=school_id)
    except TeacherInfo.DoesNotExist:
        messages.error(request, "Teacher record not found.")
        return redirect('login')
    school_instance = MasterSchool.objects.get(id = school_id)
    if request.method == "POST":
        form = RegisterTeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            # ✅ form.save() will update, not create
            obj = form.save(commit=False)
            obj.registration_no = registration_no
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
        "registration_no": registration_no,
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

    try:
        teacher = TeacherInfo.objects.get(school = school_instance,registration_no = request.session.get('registration_no'))
    except TeacherInfo.DoesNotExist:
        teacher = None
    

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
        StudentAttendance.objects
        .filter(school_id = school_id,registration_no__grade=grade, registration_no__stream=stream, date_of_attendance=today)
        .values_list("registration_no", flat=True)
    )

    filter_date = request.GET.get("filter_date")
    filter_term = request.GET.get("filter_term")

    attendance_records = StudentAttendance.objects.filter(
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
                    StudentAttendance(
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
            StudentAttendance.objects.bulk_create(attendance_data)
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
        teacher = TeacherInfo.objects.get(school = school_instance,registration_no = request.session.get('registration_no'))
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


def get_subjects(request,grade,stream):
    school_id = request.session.get('school_id')
    teacher = request.session.get('registration_no')
    roles = TeachersRole.objects.filter(school_id = school_id,registration_no=teacher)
    subjects = set()
    for role in roles:
        if role.subject and role.grade == grade and role.stream == stream:
            for subj in role.subject.split(","):
                subj = subj.strip()
                if subj:
                    subjects.add(subj)
        print("subjects: ",subjects )
    return JsonResponse({"subjects": list(subjects)})

from django.http import JsonResponse

def get_students(request):
    school_id = request.session.get('school_id')
    grade = request.GET.get('grade')
    stream = request.GET.get('stream')

    if grade and stream:
        students = StudentInfo.objects.filter(
            school_id=school_id,
            grade=grade,
            stream=stream
        ).values('registration_no', 'first_name','surname')
        students_list = list(students)
    else:
        students_list = []

    return JsonResponse({'students': students_list})

@login_required
def competency(request):
    school_id = request.session.get('school_id')
    school_instance = MasterSchool.objects.get(id=school_id)

    try:
        teacher = TeacherInfo.objects.get(
            school=school_instance,
            registration_no=request.session.get('registration_no')
        )
    except TeacherInfo.DoesNotExist:
        teacher = None

    roles = TeachersRole.objects.filter(school_id=school_id, registration_no=teacher)
    grades = roles.values_list("grade", flat=True).distinct()
    streams = roles.values_list("stream", flat=True).distinct()

    selected_grade = request.POST.get("grade") or request.GET.get("grade") or ""
    selected_stream = request.POST.get("stream") or request.GET.get("stream") or ""

    if request.method == "POST":
        subject = request.POST.get("subject", "").strip()
        comment = request.POST.get("comment", "").strip()
        competency = request.POST.get("competency", "").strip()
        term = request.POST.get("term", "").strip()
        year = int(timezone.now().year)
        level = int(request.POST.get("level", 1))
        student_id = request.POST.get("student_id")

        if subject and comment and term and student_id:
            try:
                student = StudentInfo.objects.get(registration_no=student_id, school=school_instance)
                
                LearnerCompetency.objects.create_or_update(
                    school=school_instance,
                    student=student,
                    grade=selected_grade,
                    stream=selected_stream,
                    subject=subject,
                    term=term,
                    year=year,
                    competency=competency,
                    level=level,
                    comment=comment,
                    recorded_by=request.user,
                )
                messages.success(request, "Competency added successfully.")
            except StudentInfo.DoesNotExist:
                messages.error(request, "Selected student does not exist.")
        else:
            messages.error(request, "All fields are required to add a competency.")

    return redirect("strand_list")

@login_required
def edit_competency(request, pk):
    school_id = request.session.get('school_id')
    comp = get_object_or_404(LearnerCompetency, pk=pk, school_id=school_id)
    
    if request.method == "POST":
        subject = request.POST.get("subject", "").strip()
        comment = request.POST.get("comment", "").strip()
        competency = request.POST.get("competency", "").strip()
        term = request.POST.get("term", "").strip()
        level = int(request.POST.get("level", 1))
        
        comp.subject = subject
        comp.comment = comment
        comp.competency = competency
        comp.term = term
        comp.level = level
        comp.save()
        
        messages.success(request, "Competency updated successfully.")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return HttpResponse('success')
        return redirect("strand_list")

    teacher_registration_no = request.session.get('registration_no')
    roles = TeachersRole.objects.filter(school_id=school_id, registration_no=teacher_registration_no)
    subjects = set()
    for role in roles:
        if role.subject:
            for subj in role.subject.split(","):
                subj = subj.strip()
                if subj:
                    subjects.add(subj)
    
    competencies = [
        'Communication Skills', 'Critical Thinking', 'Creativity', 'Collaboration',
        'Digital Literacy', 'Learning to Learn', 'Citizenship', 'Self-Efficacy',
    ]

    context = {
        'comp': comp,
        'subjects': subjects,
        'competencies': competencies,
    }
    return render(request, 'teacher_portal/competency_edit.html', context)

@login_required
def delete_competency(request, pk):
    school_id = request.session.get('school_id')
    comp = get_object_or_404(LearnerCompetency, pk=pk, school_id=school_id)
    
    if request.method == "POST":
        comp.delete()
        messages.success(request, "Competency deleted successfully.")
    return redirect("strand_list")


@login_required
def strand_list(request):
    # Clear existing messages
    for _ in messages.get_messages(request):
        pass

    school_id = request.session.get('school_id')
    school_instance = MasterSchool.objects.get(id=school_id)
    teacher_registration_no = request.session.get('registration_no')

    selected_grade = request.GET.get("grade", "")
    selected_stream = request.GET.get("stream", "")

    # Competency Filters
    comp_grade = request.GET.get("comp_grade", "")
    comp_stream = request.GET.get("comp_stream", "")
    comp_subject = request.GET.get("comp_subject", "")
    comp_term = request.GET.get("comp_term", "")

    competencies_qs = LearnerCompetency.objects.filter(school_id=school_id,grade = comp_grade,stream = comp_stream)
    if comp_grade:
        competencies_qs = competencies_qs.filter(grade=comp_grade) 
    if comp_stream:
        competencies_qs = competencies_qs.filter(stream=comp_stream)
    if comp_subject:
        competencies_qs = competencies_qs.filter(subject__icontains=comp_subject)
    if comp_term:
        competencies_qs = competencies_qs.filter(term=comp_term)

    # Strand objects
    strands = Strand.objects.filter(school_id=school_id, created_by=request.user).order_by("subject", "name")

    # Teacher roles
    roles = TeachersRole.objects.filter(school_id=school_id, registration_no=teacher_registration_no)
    grades = set()
    streams = set()
    subjects = set()
    for role in roles:
        if role.subject:
            grades.add(role.grade)
            streams.add(role.stream)
            for subj in role.subject.split(","):
                subj = subj.strip()
                if subj:
                    subjects.add(subj)

    # Students filtering
    if selected_grade and selected_stream:
        students = StudentInfo.objects.filter(
            school=school_instance,
            grade=selected_grade,
            stream=selected_stream
        )
    else:
        students = StudentInfo.objects.filter(school=school_instance)

    # --- Aggregated SubStrandMark Logic ---
    agg_grade = request.GET.get("agg_grade", "")
    agg_stream = request.GET.get("agg_stream", "")
    agg_term = request.GET.get("agg_term", "")
    agg_subject = request.GET.get("agg_subject", "")

    aggregated_marks = []
    student_performance = []
    if agg_grade and agg_stream and agg_term:
        marks_qs = SubStrandMark.objects.filter(
            student__school_id=school_id,
            student__grade=agg_grade,
            student__stream=agg_stream,
            term=agg_term
        )
        
        if agg_subject:
            marks_qs = marks_qs.filter(sub_strand__strand__subject=agg_subject)
        
        aggregated_data = marks_qs.values('sub_strand__strand__subject').annotate(
            avg_score=Avg('score'),
            avg_level=Avg('level'),
            student_count=Count('student', distinct=True)
        ).order_by('sub_strand__strand__subject')

        for item in aggregated_data:
            aggregated_marks.append({
                'subject': item['sub_strand__strand__subject'],
                'avg_score': round(item['avg_score'], 2) if item['avg_score'] else 0,
                'avg_level': round(item['avg_level'], 2) if item['avg_level'] else 0,
                'student_count': item['student_count']
            })
        
        # --- Student Performance Breakdown ---
        student_data = marks_qs.values(
            'student__registration_no', 
            'student__first_name', 
            'student__surname'
        ).annotate(
            avg_score=Avg('score'),
            avg_level=Avg('level'),
            subjects_count=Count('sub_strand__strand__subject', distinct=True)
        ).order_by('student__registration_no')

        for item in student_data:
            student_performance.append({
                'reg_no': item['student__registration_no'],
                'name': f"{item['student__first_name']} {item['student__surname']}",
                'avg_score': round(item['avg_score'], 2) if item['avg_score'] else 0,
                'avg_level': round(item['avg_level'], 2) if item['avg_level'] else 0,
                'subjects_count': item['subjects_count']
            })
   

    # Core competencies
    competencies = [
        'Communication Skills',
        'Critical Thinking',
        'Creativity',
        'Collaboration',
        'Digital Literacy',
        'Learning to Learn',
        'Citizenship',
        'Self-Efficacy',
    ]

    form = StrandForm()

    context = {
        "strands": strands,
        "form": form,
        "subjects": subjects,
        "grades": sorted(list(grades)),
        "streams": sorted(list(streams)),
        "selected_grade": selected_grade,
        "selected_stream": selected_stream,
        "students": students,
        "competencies": competencies,
        "competencies_list": competencies_qs.order_by('-recorded_at'),
        "comp_grade": comp_grade,
        "comp_stream": comp_stream,
        "comp_subject": comp_subject,
        "comp_term": comp_term,
        "agg_grade": agg_grade,
        "agg_stream": agg_stream,
        "agg_term": agg_term,
        "agg_subject": agg_subject,
        "aggregated_marks": aggregated_marks,
        "student_performance": student_performance,
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
    }

    return render(request, "teacher_portal/strands_list.html", context)


@login_required 
def export_strand_marks_csv(request):
    school_id = request.session.get('school_id')
    grade = request.GET.get("agg_grade")
    stream = request.GET.get("agg_stream")
    term = request.GET.get("agg_term")
    subject = request.GET.get("agg_subject")

    response = HttpResponse(content_type='text/csv')
    filename_subject = f"_{subject}" if subject else ""
    response['Content-Disposition'] = f'attachment; filename="student_performance_{grade}_{stream}_{term}{filename_subject}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Registration No', 'Name', 'Average Score', 'Average Level', 'Subjects Assessed'])

    if grade and stream and term:
        marks_qs = SubStrandMark.objects.filter(
            student__school_id=school_id,
            student__grade=grade,
            student__stream=stream,
            term=term
        )
        
        if subject:
            marks_qs = marks_qs.filter(sub_strand__strand__subject=subject)
            
        student_data = marks_qs.values(
            'student__registration_no', 
            'student__first_name', 
            'student__surname'
        ).annotate(
            avg_score=Avg('score'),
            avg_level=Avg('level'),
            subjects_count=Count('sub_strand__strand__subject', distinct=True)
        ).order_by('student__registration_no')

        for item in student_data:
            writer.writerow([
                item['student__registration_no'],
                f"{item['student__first_name']} {item['student__surname']}",
                round(item['avg_score'], 2) if item['avg_score'] else 0,
                round(item['avg_level'], 2) if item['avg_level'] else 0,
                item['subjects_count']
            ])

    return response

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
    # print("Strand: ",strand)
    if request.method == "POST":
        strand.delete()
        messages.success(request, "Strand deleted successfully.")
    return redirect("strand_list")

@login_required
def sub_strands_view(request, strand_id,grade,stream):
    for _ in messages.get_messages(request):
        pass
    logger = logging.getLogger(__name__)
    school_id = request.session['school_id']
    registration_no = request.session.get('registration_no')
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

@require_http_methods(["GET", "POST"])
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

def delete_substrand(request, sub_strand_id):
    try:
        for _ in messages.get_messages(request):
            pass
    # Retrieve the object or return 404
        substrand = get_object_or_404(SubStrand, pk=sub_strand_id) 
        
        # Perform the deletion
        substrand.delete()
        
        # Redirect back to a safe page (e.g., the list page)
        messages.success(request, "Sub-strand deleted successfully.")
        return redirect("strand_list")
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }, status=500)

from django.views.decorators.csrf import csrf_exempt
@login_required
@csrf_exempt

def record_substrand_scores(request, sub_strand_id,grade,stream):
    for _ in messages.get_messages(request):
        pass
    school_id = request.session.get('school_id')
    sub_strand = get_object_or_404(SubStrand, pk=sub_strand_id)
    strand = sub_strand.strand
    
    
    students = StudentInfo.objects.filter(school_id=school_id,grade = grade,stream = stream).order_by('registration_no')

    term_choices = ['Term 1', 'Term 2', 'Term 3']
    levels = ['Level 1', 'Level 2', 'Level 3','Level 4']
    ASSESSMENT_TYPES = [
        'SBA-Project', 
        'SBA-Practical', 
        'SBA-Written', 
        'End-Level Assessment'
    ]
    current_year = str(datetime.now().year)

    # ---- Handle POST (AJAX or normal)
    if request.method == "POST":
        # Ensure we only attempt JSON for AJAX
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        term = (request.POST.get('term') or '').strip()
        assessment_type = (request.POST.get('assessment_type') or '').strip()
        if term not in term_choices:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Valid term is required.'}, status=400)
            messages.error(request, 'Valid term is required.')
            return redirect("strand_list")

        updated = 0
        errors = []
        for student in students:
            raw_value = request.POST.get(f'score_{student.registration_no}')
            raw_score = request.POST.get(f'raw_score_{student.registration_no}')
            remark = request.POST.get(f'remark_{student.registration_no}')
            level = request.POST.get(f'level_{student.registration_no}')

            if raw_value in (None, "") and raw_score in (None ,""):
                continue
            try:
                score_value = float(raw_value)
                raw_score_value = float(raw_score) 
                SubStrandMark.objects.update_or_create(
                    student=student,
                    sub_strand=sub_strand,
                    term=term,
                    year=current_year,
                    defaults={
                        'raw_score': raw_score_value,
                        'score': score_value,
                        'remark': remark,
                        'level': level,
                        'assessment_type': assessment_type,
                        'recorded_by': request.user
                    }
                )
                updated += 1
            except Exception as e:
                logger.exception("Error saving score for %s", student.registration_no)
                errors.append({
                    'registration_no': student.registration_no,
                    'error': str(e)
                })

        if is_ajax:
            status_value = 'success' if not errors else 'partial'
            return JsonResponse({"status": status_value, "updated": updated, "errors": errors})
        else:
            if errors:
                messages.error(request, "Some scores failed to save.")
            else:
                messages.success(request, "Scores saved successfully.")
            # fallback for non-AJAX forms
            return redirect("strand_list")

    # ---- Handle GET
    selected_term = request.GET.get('term', '').strip()
    existing_qs = SubStrandMark.objects.filter(sub_strand=sub_strand, year=current_year)
    if selected_term:
        existing_qs = existing_qs.filter(term=selected_term)

    existing_scores = existing_qs.values('student__registration_no', 'score','raw_score', 'remark','level')
    score_map = {row['student__registration_no']: row['score'] for row in existing_scores}
    raw_score_map = {row['student__registration_no']: row['raw_score'] for row in existing_scores}
    remark_map = {row['student__registration_no']: row['remark'] for row in existing_scores}
    level_map = {row['student__registration_no']: row['level'] for row in existing_scores}

    return render(request, 'teacher_portal/record_substrand_scores.html', {
        'sub_strand': sub_strand,
        'strand': strand,
        'students': students,
        'term_choices': term_choices,
        'scores': score_map,
        'raw_scores': raw_score_map, 
        'remark': remark_map,
        'level_map': level_map,
        'levels': levels,
        'assessment_types': ASSESSMENT_TYPES,
        'selected_term': selected_term,
    })

from django.db.models import Count, Avg
from django.http import HttpRequest
# Assuming your models are imported correctly (SubStrand, SubStrandMark)

def substrand_report_view(request: HttpRequest, substrand_id): 
    
    # 1. Fetch the Substrand object (will raise 404 if not found)
    selected_substrand = get_object_or_404(SubStrand, pk=substrand_id)
    
    # Define the base queryset (efficient: only includes the required filter)
    mark_query = SubStrandMark.objects.filter(
        sub_strand=selected_substrand
    )

    # 2. Aggregate data: Count how many pupils achieved each level
    report_data = mark_query.values('level').annotate(
        pupil_count=Count('level')
    ).order_by('level')
    
    # 3. Calculate the average level/score
    average_level = mark_query.aggregate(Avg('level'))['level__avg']
    # Fetch detailed records for the table
    all_records = mark_query.select_related('student').order_by('student__registration_no')

    # 4. Define context for the template
    context = {
        'all_records': all_records, 
        'selected_substrand': selected_substrand,
        'report_data': report_data,
        # Format the average to 2 decimal places if it's not None
        'average_level': f"{average_level:.2f}" if average_level is not None else "N/A", 
        # Define level names here or use a helper function/model
        # NOTE: This assumes 'level' is 1, 2, or 3
        'level_names': ['Level 1 (Improve)', 'Level 2 (Good)', 'Level 3 (Very Good)', 'Level 4 (Excellent)'], 
    }
    
    # 5. Check if the request is AJAX 
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if is_ajax:
        # If it's AJAX, render only the report fragment for the modal body
        template_name = 'teacher_portal/reports/substrand_report_fragment.html'
    else:
        # Otherwise, render the full page (for direct browser access)
        template_name = 'teacher_portal/reports/substrand_report.html'
    
    return render(request, template_name, context)
@login_required
def cbc_events(request):
    """Create/list CBC assessment events (AJAX friendly)."""
    school_id = request.session.get('school_id')
    school = get_object_or_404(MasterSchool, id=school_id)

    if request.method == 'POST':
        data = request.POST
        try:
            event = AssessmentEvent.objects.create(
                school=school,
                created_by=request.user,
                date=data.get('date') or timezone.now().date(),
                term=data.get('term', ''),
                year=data.get('year') or str(timezone.now().year),
                grade=data.get('grade',''),
                stream=data.get('stream') or '',
                subject=data.get('subject',''),
                activity=data.get('activity',''),
                method=data.get('method') or '',
            )
            return JsonResponse({'status':'success','id':event.id})
        except Exception as e:
            return JsonResponse({'status':'error','message':str(e)}, status=400)

    # GET list (lightweight)
    qs = AssessmentEvent.objects.filter(school=school).order_by('-date')[:50]
    payload = [
        {
            'id': e.id,
            'date': e.date.strftime('%Y-%m-%d'),
            'term': e.term,
            'year': e.year,
            'grade': e.grade,
            'stream': e.stream,
            'subject': e.subject,
            'activity': e.activity,
            'method': e.method,
        }
        for e in qs
    ]
    return JsonResponse({'status':'success','events': payload})


@login_required
def cbc_record_substrand(request, sub_strand_id, grade, stream):
    """Render CBC form for a sub-strand and save observations via AJAX."""
    school_id = request.session.get('school_id')
    school = get_object_or_404(MasterSchool, id=school_id)

    sub_strand = get_object_or_404(SubStrand, pk=sub_strand_id)
    strand = sub_strand.strand
    students = StudentInfo.objects.filter(school_id=school_id, grade=grade, stream=stream).order_by('registration_no')
    term_choices = ['Term 1','Term 2','Term 3']

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        term = (request.POST.get('term') or '').strip()
        if term not in term_choices:
            return JsonResponse({'status':'error','message':'Valid term is required.'}, status=400)
        year = str(timezone.now().year)
        updated = 0
        errors = []
        for student in students:
            lvl = request.POST.get(f'level_{student.registration_no}')
            cmt = request.POST.get(f'comment_{student.registration_no}', '')
            if lvl in (None, ''):
                continue
            try:
                lvl = int(lvl)
                if lvl not in (1,2,3,4):
                    raise ValueError('Invalid level')
                # Update existing latest observation for this student/term/year, otherwise create new
                existing = Observation.objects.filter(
                    student=student,
                    sub_strand=sub_strand,
                    term=term,
                    year=year,
                ).order_by('-recorded_at').first()
                if existing:
                    existing.level = lvl
                    existing.comment = cmt or None
                    existing.recorded_by = request.user
                    existing.save(update_fields=['level','comment','recorded_by'])
                else:
                    Observation.objects.create(
                        school=school,
                        student=student,
                        sub_strand=sub_strand,
                        term=term,
                        year=year,
                        level=lvl,
                        comment=cmt or None,
                        recorded_by=request.user,
                    )
                updated += 1
            except Exception as e:
                errors.append({'registration_no': student.registration_no, 'error': str(e)})
        status_val = 'success' if not errors else 'partial'
        return JsonResponse({'status': status_val, 'updated': updated, 'errors': errors})

    # GET: render CBC form with existing values for selected term
    selected_term = request.GET.get('term', '')
    descriptors = OutcomeDescriptor.objects.filter(sub_strand=sub_strand)
    desc_map = {d.level: d.descriptor for d in descriptors}

    existing_levels = {}
    existing_comments = {}
    if selected_term:
        year = str(timezone.now().year)
        obs_qs = (
            Observation.objects
            .filter(student__in=students, sub_strand=sub_strand, term=selected_term, year=year)
            .order_by('student_id', '-recorded_at')
        )
        seen = set()
        for o in obs_qs:
            reg = getattr(o.student, 'registration_no', None)
            if reg and reg not in seen:
                existing_levels[reg] = o.level
                existing_comments[reg] = o.comment or ''
                seen.add(reg)

    context = {
        'cbc_mode': True,
        'sub_strand': sub_strand,
        'strand': strand,
        'students': students,
        'term_choices': ['Term 1','Term 2','Term 3'],
        'selected_term': selected_term,
        'descriptors': desc_map,
        'existing_levels': existing_levels,
        'existing_comments': existing_comments,
    }
    return render(request, 'teacher_portal/cbc_record_substrand.html', context)


@login_required
def cbc_report_student(request, reg_no):
    school_id = request.session.get('school_id')
    student = get_object_or_404(StudentInfo, registration_no=reg_no, school_id=school_id)
    term = request.GET.get('term') or 'Term 1'
    year = request.GET.get('year') or str(timezone.now().year)

    obs = Observation.objects.filter(student=student, term=term, year=year).select_related('sub_strand__strand')
    report = {}
    for o in obs:
        subject = o.sub_strand.strand.subject
        strand_name = o.sub_strand.strand.name
        sub_name = o.sub_strand.name
        report.setdefault(subject, {}).setdefault(strand_name, {}).setdefault(sub_name, []).append(o.level)

    import statistics
    final = {}
    for subject, strands in report.items():
        final[subject] = {}
        for sname, subs in strands.items():
            final[subject][sname] = {}
            for sub_name, levels in subs.items():
                try:
                    lvl = statistics.mode(levels)
                except statistics.StatisticsError:
                    lvl = levels[-1] if levels else None
                final[subject][sname][sub_name] = lvl

    return JsonResponse({'status':'success','student': student.registration_no, 'term': term, 'year': year, 'report': final})


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
        teacher = TeacherInfo.objects.get(school = school_instance,registration_no = request.session.get('registration_no'))
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

def teacher_announcements(request):
    school_id = request.session.get('school_id')
    announcements = Announcement.objects.filter(school_id = school_id,target_audience__icontains='teachers').order_by('-created_at')
    return render(request, 'teacher_portal/announcements.html', {'announcements': announcements})
 

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test


# Helper function to check if the user is a teacher/staff


# 1. CREATE: Upload a new resource
def get_resource_progress(request, resource_id):
    """API to fetch progress of all students for a specific resource"""
    resource = get_object_or_404(Resource, id=resource_id)
    
    # Fetch all students in the same Grade and Stream as the resource
    students = StudentInfo.objects.filter(grade=resource.grade, stream=resource.stream)
    
    student_data = []
    for s in students:
        # Check if a log exists for this student and resource
        log = LearningLog.objects.filter(student__user=s.user, resource=resource).first()
        
        progress = log.progress if log else 0
        status = "Completed" if progress >= 95 else ("In Progress" if progress > 0 else "Not Started")
        badge = "bg-success" if progress >= 95 else ("bg-warning text-dark" if progress > 0 else "bg-secondary")
        
        student_data.append({
            'name': f"{s.first_name} {s.last_name}",
            'adm': s.registration_no,
            'progress': progress,
            'status': status,
            'badge_class': badge
        })
        
    return JsonResponse({'students': student_data})

@login_required
def resource_progress(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    school_id = request.session.get('school_id')
    
    # Fetch all students in the resource's assigned grade and stream
    # select_related('admin') optimizes the query if you are accessing User fields
    students = StudentInfo.objects.filter(
        grade=resource.grade, 
        stream=resource.stream,
        school_id = school_id,
    ).select_related('school')
    
    data = []
    for student in students:
        # Check if a log exists for this student and resource
        log = LearningLog.objects.filter(student=student, resource=resource).first()
        
        progress = log.progress if log else 0
        
        # Determine status and styling
        if progress >= 95:
            status = 'Completed'
            badge_class = 'bg-success'
        elif progress > 0:
            status = 'In Progress'
            badge_class = 'bg-warning'
        else:
            status = 'Not Started'
            badge_class = 'bg-secondary'
            
        data.append({
            'name': f"{student.first_name} {student.surname}", 
            'adm': student.registration_no,  # Replace with your actual admission number field
            'progress': progress,
            'status': status,
            'badge_class': badge_class
        })
    
    return JsonResponse({'students': data})
@login_required
def manage_resources(request):
    registration_no = request.session.get('registration_no')
    school_id = request.session.get('school_id')
    user = request.user.username
    grades = list(TeachersRole.objects.filter(registration_no = registration_no).values_list('grade',flat=True).distinct())
    streams = list(TeachersRole.objects.filter(registration_no = registration_no).values_list('stream',flat=True).distinct())
    resources = Resource.objects.filter(school_id = school_id,recorded_by = request.user)  
    subject_set = set()
    roles = TeachersRole.objects.filter(school_id = school_id,registration_no = registration_no)
    for role in roles:
        if role.subject:
            subjects = [s.strip() for s in role.subject.split(",") if s.strip()]
            subject_set.update(subjects)
    subject_choices = sorted((subject) for subject in subject_set)

    
    if request.method == 'POST':
        # FILES is required for thumbnail and PDF uploads
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid(): 
            resource = form.save(commit=False)
            resource.school_id = school_id
            
            # Extract YouTube ID if it's a video
            if resource.resource_type == 'video' and resource.url_or_file:
                regex = r'(?:v=|\/|embed\/|youtu\.be\/)([0-9A-Za-z_-]{11})'
                match = re.search(regex, resource.url_or_file)
                if match:
                    resource.url_or_file = match.group(1)
        
            resource.recorded_by = request.user
            
            resource.save()
            messages.success(request, 'Resource uploaded successfully!')
            return redirect('manage_resources')
        else:
            print("errors: ",form.errors,'User id',request.user.id) 
    else:
        form = ResourceForm()
    
    context = {
        'form': form, 
        'grades': grades,
        'streams': streams,
        'subjects': subject_choices,
        'resources': resources,
        'title': 'Upload Resource',
        'term_choices': ['Term 1','Term 2','Term 3']
    }
    return render(request, 'teacher_portal/learning_resources.html', context)

# 2. UPDATE: Edit an existing resource
@login_required

def update_resource(request, resource_id):
    school_id = request.session.get('school_id')
    resource = get_object_or_404(Resource, id=resource_id)
    registration_no = request.session.get('registration_no')
    if request.method == 'POST':
        # Pass instance=resource to update the existing record
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            resource = form.save(commit=False)
            
            # Extract YouTube ID if it's a video
            if resource.resource_type == 'video' and resource.url_or_file:
                regex = r'(?:v=|\/|embed\/|youtu\.be\/)([0-9A-Za-z_-]{11})'
                match = re.search(regex, resource.url_or_file)
                if match:
                    resource.url_or_file = match.group(1)
            
            resource.save()
            messages.success(request, f'"{resource.title}" updated successfully!')
            return redirect('manage_resources') 
    else:
        form = ResourceForm(instance=resource)
    resources = Resource.objects.filter(school_id = school_id,recorded_by = request.user)  
    roles = TeachersRole.objects.filter(school_id = school_id,registration_no = registration_no)
    grades = roles.values_list('grade',flat=True).distinct()
    streams = roles.values_list('stream',flat=True).distinct()
    subject_set = set()
    for role in roles:
        if role.subject:
            subjects = [s.strip() for s in role.subject.split(",") if s.strip()]
            subject_set.update(subjects)
    subject_choices = sorted((subject) for subject in subject_set)
    
    context = {
        'form': form, 
        'title': 'Update Resource',
        'resource': resource,
        'resources': resources,
        'subjects': subject_choices,
        'grades': grades,
        'streams': streams
    }
    return render(request, 'teacher_portal/learning_resources.html', context)

# 3. DELETE: Remove a resource
@login_required

def delete_resource(request, resource_id):

    """
    Handles deletion via POST request from the modal on the Learning Hub.
    """
    if request.method == 'POST':
        resource = get_object_or_404(Resource, id=resource_id)
        title = resource.title
        resource.delete()
        messages.success(request, f'Resource "{title}" has been deleted.')
    
    return redirect('manage_resources')
