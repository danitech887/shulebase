from ..models import*
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Q, Count, F,Case, When, Avg

@login_required

def student_portal_dashboard(request):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')

    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', str(datetime.now().year))
    
    student = get_object_or_404(StudentInfo, school_id=school_id, registration_no=registration_no)
    grade = student.grade
    grade = get_object_or_404(Grade, school_id=school_id, name=grade)
    term_choices = ['Term 1', 'Term 2', 'Term 3']
    for _ in messages.get_messages(request):
        pass
    today = now().date()
    

    fee_records = Fee.objects.filter(school_id=school_id, registration_no=registration_no,term = term_filter)
    expected_fee = grade.expected_fee
    total_fees_paid = fee_records.aggregate(total_paid=Sum('amount'))['total_paid'] or Decimal('0.00')
    balance = expected_fee - Decimal(total_fees_paid)


    leave_records = LeaveManagement.objects.filter(school_id=school_id, registration_no_id=registration_no)
    total_leaves = leave_records.count()
    approved_leaves = leave_records.filter(status='Approved').count()
    pending_leaves = leave_records.filter(status='Pending').count()

    print("approved_leaves",approved_leaves)
    print("pending_leaves",pending_leaves)
    print("Announcements: ",request.session.get("no_of_announcements"))


    attendance_records = StudentAttendance.objects.filter(
        school_id=school_id,
        registration_no=registration_no
    )
    total_days = attendance_records.count()
    present_days = attendance_records.filter(status='Present').count()
    absent_days = attendance_records.filter(status='Absent').count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    context = {
        "term_choices": term_choices,
        "year": datetime.now().year,
        "expected_fee": expected_fee,
        "total_fees_paid": total_fees_paid,
        "balance": balance,
        "total_leaves": total_leaves,
        "approved_leaves": approved_leaves,
        "pending_leaves": pending_leaves,
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "attendance_percentage": attendance_percentage,
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
    }

    return render(
        request,
        'students/student_portal/dashboard.html',
        context
    )

def student_portal_fee_payment(request):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')

    student = get_object_or_404(StudentInfo, school_id=school_id, registration_no=registration_no)
    grade = student.grade
    grade = get_object_or_404(Grade, school_id=school_id, name=grade)
    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', str(datetime.now().year))

    fee_records = Fee.objects.filter(school_id=school_id, registration_no=registration_no,term = term_filter)
    expected_fee = grade.expected_fee
    total_fees_paid = fee_records.aggregate(total_paid=Sum('amount'))['total_paid'] or Decimal('0.00')
    balance = expected_fee - Decimal(total_fees_paid)

    context = {
        "student": student,
        "expected_fee": expected_fee,
        "total_fees_paid": total_fees_paid,
        "balance": balance,
        "fee_records": fee_records,
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
    }

    return render(
        request,
        'students/student_portal/fee.html',
        context
    )

def student_portal_attendance(request):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')

    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', str(datetime.now().year))
    attendance_records = StudentAttendance.objects.filter(
        school_id=school_id,
        registration_no=registration_no,
        term = term_filter
    ).order_by('-date_of_attendance')



    present_days = attendance_records.filter(status='Present').count()
    absent_days = attendance_records.filter(status='Absent').count()
    total_days = attendance_records.count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    student_obj = get_object_or_404(StudentInfo, school_id=school_id, registration_no=registration_no)
    grade = student_obj.grade
    stream = student_obj.stream

    teacher_role = TeachersRole.objects.filter(
        school_id=school_id, 
        grade=grade, 
        stream=stream, 
        type_of_teacher='Class Teacher'
    ).select_related('registration_no').first()
    
    class_teachername = teacher_role.registration_no.first_name if teacher_role else "N/A"
    

    context = {
        "attendance_records": attendance_records,
        "present_days": present_days,
        "absent_days": absent_days,
        "total_days": total_days,
        "attendance_percentage": attendance_percentage,
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
        'class_teacher': class_teachername
    }

    return render(
        request,
        'students/student_portal/attendance.html',
        context
    )
def student_leave_application(request):
    school_id = request.session.get('school_id')
    print("school_id",school_id)
    registration_no = request.session.get('registration_no')
    student = StudentInfo.objects.get(school_id=school_id, registration_no=registration_no)
    school_instance = MasterSchool.objects.get(id=school_id)
    if request.method == "POST":
        date_of_leave = request.POST.get('date_of_leave')
        reason = request.POST.get('reason')

        LeaveManagement.objects.create(
            school_id=school_id,
            registration_no=student,
            date_of_leave=date_of_leave,
            reason = 'Other Reason',
            phone = student.phone,
            other_reason=reason,
            status='Pending'
        )
        messages.success(request, "✅ Leave application submitted successfully.")

    return redirect('student_portal_leave_statement')

def student_portal_leave_statement(request):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')
    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', str(datetime.now().year))
    leave_records = LeaveManagement.objects.filter(
        school_id=school_id,
        registration_no_id=registration_no,
        term = term_filter
    ).order_by('-date_of_leave')
    total_leaves = leave_records.count()
    approved_leaves = leave_records.filter(status='Approved').count()
    pending_leaves = leave_records.filter(status='Pending').count()
    rejected_leaves = leave_records.filter(status='Rejected').count()

    context = {
        "leave_records": leave_records,
        "total_leaves": total_leaves,
        "approved_leaves": approved_leaves,
        "pending_leaves": pending_leaves,
        "rejected_leaves": rejected_leaves, 
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
    }

    return render(
        request,
        'students/student_portal/leave.html',
        context
    )

LOWER_SUBJECTS = [
    'Mathematics', 'English', 'Kiswahili', 'Environmental Activities', 'Integrated Creative','Cre'
]
UPPER_SUBJECTS = [
    'Mathematics', 'English', 'Kiswahili', 'Science & Technology', 'Cre', 'Agriculture & Nutrition', 'Creative Arts','Social Studies'
]
JUNIOR_SUBJECTS = [
    'Mathematics', 'English', 'Kiswahili', 'Cre', 'Agriculture & Nutrition', 'Creative Arts', 'Pretech/Bs/Comps', 'Integrated Science','Social Studies'
]
LOWER_GRADES = ['PP 1', 'PP 2', 'Grade 1', 'Grade 2', 'Grade 3']
UPPER_GRADES = ['Grade 4', 'Grade 5', 'Grade 6']
JUNIOR_GRADES = ['Grade 7', 'Grade 8', 'Grade 9']
STREAMS = ['Stream 1', 'Stream 2', 'Stream 3', 'Stream 4']


from ..models import StudentInfo, GradeStream, Grade,Fee,LeaveManagement,StudentAttendance,MasterSchool, SubStrandMark, LearnerCompetency, TeachersRole
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Q, Count, F,Case, When, Avg

# CORE_COMPETENCIES = [
#     'Communication Skills',
#     'Critical Thinking',
#     'Creativity',
#     'Collaboration',
#     'Digital Literacy',
#     'Learning to Learn',
#     'Citizenship',
#     'Self-Efficacy',
# ]




# Updated with 4.0 scale logic
CBC_LEVEL_MAP = {
    'EE': {'min_avg': 3.50, 'label': 'Exceeding Expectations', 'remark': 'Excellent Mastery'},
    'ME': {'min_avg': 2.50, 'label': 'Meeting Expectations', 'remark': 'Good Progress'},
    'AE': {'min_avg': 1.50, 'label': 'Approaching Expectations', 'remark': 'Needs Improvement'},
    'BE': {'min_avg': 1.00, 'label': 'Below Expectations', 'remark': 'Critical Intervention'},
}

def get_cbc_level_and_remark(avg_level):
    if avg_level is None:
        return {'level': 'N/A', 'remark': 'No Data'}

    # Ensure we handle scores slightly above 4.0 or below 1.0 just in case
    # We sort by min_avg descending to catch the highest threshold first
    for key, data in sorted(CBC_LEVEL_MAP.items(), key=lambda x: x[1]['min_avg'], reverse=True):
        if avg_level >= data['min_avg']:
            return {
                'level': key, 
                'label': data['label'], 
                'remark': data['remark']
            }
            
    # Fallback for very low scores
    return {'level': 'BE', 'label': 'Below Expectations', 'remark': 'Critical Intervention'}
# --- THE MAIN DJANGO VIEW ---
from django.urls import reverse
@login_required
def student_portal_academics(request):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')

    # 1. --- Fetch Student and Basic Info ---
    student = get_object_or_404(StudentInfo, school_id=school_id, registration_no=registration_no)

    # 2. --- Get Filters and Define Base Query ---
    current_year = str(datetime.now().year)
    term_filter = request.GET.get('term', 'Term 1') # Default to Term 1 if not provided
    year_filter = request.GET.get('year', current_year)
    base_marks_qs = SubStrandMark.objects.filter(student=student).select_related('sub_strand__strand', 'recorded_by')
   
    if term_filter:
        
        base_marks_qs = SubStrandMark.objects.filter(
            student=student,
            term=term_filter,
            year=year_filter
        ).select_related('sub_strand__strand', 'recorded_by')
    if year_filter:
        
        base_marks_qs = SubStrandMark.objects.filter(
            student=student,
            year=year_filter
        ).select_related('sub_strand__strand', 'recorded_by')
    
    

    # 3. --- Subject Performance Summary ---
    subject_summaries_qs = base_marks_qs.values(
        'sub_strand__strand__subject' # Group by the main learning area
    ).annotate(
        mean_score=Avg('score'),
        mean_level=Avg('level')
    ).order_by('sub_strand__strand__subject')

    subject_summaries = []
    for summary in subject_summaries_qs:
        subject_name = summary['sub_strand__strand__subject']
        # Find a teacher for that subject in the student's grade
        teacher_role = TeachersRole.objects.filter(
            school_id=school_id,
            grade=student.grade,
            subject__icontains=subject_name
        ).select_related('registration_no').first()

        teacher_name = f"{teacher_role.registration_no.first_name} {teacher_role.registration_no.surname}" if teacher_role else "N/A"

        subject_summaries.append({
            "name": subject_name, 
            "score": summary['mean_score'],
            "level": get_cbc_level_and_remark(summary['mean_level'])['level'],
            "teacher": teacher_name
        })

    # 4. --- Calculate Overall Mean Score ---
    overall_mean_agg = base_marks_qs.aggregate(overall_mean=Avg('score'))
    overall_mean = overall_mean_agg['overall_mean'] or 0

    # 5. --- Core Competency Ratings ---
    competency_qs = LearnerCompetency.objects.filter(
        student=student,
        term=term_filter,
        year=year_filter
    ).order_by('subject', 'competency')

    # A. Detailed List (for Table)
    detailed_competencies = []
    for comp in competency_qs:
        details = get_cbc_level_and_remark(comp.level)
        rating = details['level']
        
        color = 'secondary'
        if rating == 'EE': color = 'success'
        elif rating == 'ME': color = 'info'
        elif rating == 'AE': color = 'warning'
        elif rating == 'BE': color = 'danger'

        detailed_competencies.append({
            "subject": comp.subject,
            "competency": comp.competency,
            "level": comp.level,
            "rating": rating,
            "remark": details['remark'],
            "comment": comp.comment,
            "color": color
        })

    # B. Aggregated Averages (for Cards)
    competency_ratings = []
    agg_qs = LearnerCompetency.objects.filter(
        student=student,
        term=term_filter,
        year=year_filter
    ).values('competency').annotate(avg_level=Avg('level')).order_by('competency')

    for item in agg_qs:
        details = get_cbc_level_and_remark(item['avg_level'])
        rating = details['level']
        color = 'secondary'
        if rating == 'EE': color = 'success'
        elif rating == 'ME': color = 'info'
        elif rating == 'AE': color = 'warning'
        elif rating == 'BE': color = 'danger'
        
        competency_ratings.append({"competency": item['competency'], "rating": rating, "color": color})
    
    # 6. --- Placeholder Data (can be developed further) ---
    report_url = reverse("report_card") + f"?registration_no={registration_no}&term={term_filter}"

    latest_report = {
        "term": term_filter,
        "link": report_url,
        "date": datetime.now().strftime("%B %d, %Y")
    }
    resources = Resource.objects.filter(school_id = school_id,grade = student.grade, stream = student.stream,term = term_filter)
    
    term_choices = list(SubStrandMark.objects.filter(student=student).values_list('term', flat=True).distinct())


    context = {
        "student": student,
        "term_choices": term_choices,
        "current_term": term_filter,
        "overall_mean": overall_mean,
        "subject_summaries": subject_summaries,
        "competency_ratings": competency_ratings,
        "detailed_competencies": detailed_competencies,
        "latest_report": latest_report,
        "resources": resources,
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
        "year_choices": SubStrandMark.objects.filter(student=student).values_list('year', flat=True).distinct().order_by('-year'),
        "selected_year": year_filter,
    }

    return render(
        request,
        'students/student_portal/academics.html',
        context
    )


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from datetime import datetime

@login_required
def view_learning_area_breakdown(request, subject):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')
    student = get_object_or_404(StudentInfo, school_id=school_id, registration_no=registration_no)

    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', str(datetime.now().year))

    marks_qs = SubStrandMark.objects.filter(
        student=student,
        sub_strand__strand__subject=subject
    ).select_related('sub_strand__strand', 'recorded_by')
    # This line is just to trigger evaluation for debugging purposes
    
    marks = marks_qs.order_by('date_recorded')
    if term_filter:
        marks_qs = marks_qs.filter(term=term_filter)
    if year_filter:
        marks_qs = marks_qs.filter(year=year_filter)

    # marks = marks_qs.order_by('sub_strand__name')
    teacher_role = TeachersRole.objects.filter(
            school_id=school_id,
            grade=student.grade,
            subject__icontains=subject
        ).select_related('registration_no').first()

    teacher_name = f"{teacher_role.registration_no.first_name} {teacher_role.registration_no.surname}" if teacher_role else "N/A"

    # Fetch competencies for this subject
    competencies_qs = LearnerCompetency.objects.filter(
        student=student,
        subject=subject,
        term=term_filter,
        year=year_filter
    )
    
    competencies_data = []
    for comp in competencies_qs:
        competencies_data.append({
            'competency': comp.competency,
            'level': comp.level,
            'comment': comp.comment,
            'cbc_level': get_cbc_level_and_remark(comp.level)['level']
        })

      # Debugging log 
    for mark in marks:
        print(f"Mark: {mark.sub_strand.name}, Score: {mark.score}, Term: {mark.term}, Year: {mark.year}, Recorded By: {mark.recorded_by}")

    # Build JSON response
    data = []
    for mark in marks:
        
        data.append({
            "sub_strand": mark.sub_strand.name,
            "score": mark.score,
            "term": mark.term,
            "year": mark.year,
            "recorded_by": teacher_name
        })

    # print("Learning Area Breakdown Data:", data)  # Debugging log
    
    return JsonResponse({
        "student": f"{student.first_name} {student.surname}",
        "subject": subject,
        "term": term_filter,
        "year": year_filter,
        "marks": data,
        "competencies": competencies_data
    })

from ..models import Announcement
def students_announcements(request):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')

    announcements = Announcement.objects.filter(
        Q(target_audience__icontains='Students') | 
        Q(target_audience__icontains=registration_no)
    , school_id=school_id).order_by('-created_at')

    context = {
        "announcements": announcements,
    }

    return render(
        request,
        'students/student_portal/announcements.html',
        context 
    )


    
