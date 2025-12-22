from ..models import StudentInfo, GradeStream, Grade,Fee,LeaveManagement,StudentAttendance,MasterSchool, SubStrandMark, LearnerCompetency, TeachersRole
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Q, Count, F,Case, When, Avg

@login_required

def parent_portal_dashboard(request):
    school_id = request.session.get('school_id')
    username = request.session.get('username') # Parent's phone number
    
    # 1. Fetch all children linked to this phone number
    students = StudentInfo.objects.filter(school_id=school_id, phone=username)
    
    if not students.exists():
        messages.error(request, "No students found linked to this account.")
        return redirect('login')

    # 2. Determine which student's data to show
    # Check if user clicked a specific child, else check session, else default to first child
    reg_no = request.GET.get('student_id') or request.session.get('registration_no')
    
    if reg_no:
        student = students.filter(registration_no=reg_no).first()
        if not student: # Safety check
            student = students.first()
    else:
        student = students.first()

    # Update session so other pages (Academics, Fees) follow this selection
    request.session['registration_no'] = student.registration_no
    registration_no = student.registration_no

    # 3. Fetch Data for the SELECTED student
    grade_obj = get_object_or_404(Grade, school_id=school_id, name=student.grade)
    
    # Fees
    fee_records = Fee.objects.filter(school_id=school_id, registration_no=registration_no)
    expected_fee = grade_obj.expected_fee
    total_fees_paid = fee_records.aggregate(total_paid=Sum('amount'))['total_paid'] or Decimal('0.00')
    balance = expected_fee - Decimal(total_fees_paid)

    # Leaves
    leave_records = LeaveManagement.objects.filter(school_id=school_id, registration_no_id=registration_no)
    
    # Attendance
    attendance_records = StudentAttendance.objects.filter(school_id=school_id, registration_no=registration_no)
    total_days = attendance_records.count()
    present_days = attendance_records.filter(status='Present').count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    context = {
        "students": students,  # All children
        "student": student,    # The selected child
        "year": datetime.now().year,
        "expected_fee": expected_fee,
        "total_fees_paid": total_fees_paid,
        "balance": balance,
        "total_leaves": leave_records.count(),
        "approved_leaves": leave_records.filter(status='Approved').count(),
        "pending_leaves": leave_records.filter(status='Pending').count(),
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": attendance_records.filter(status='Absent').count(),
        "attendance_percentage": attendance_percentage,
    }

    return render(request, 'parent_portal/dashboard.html', context)
from django.db.models import Sum
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect

from datetime import datetime

def parent_student_portal_fee_payment(request):
    school_id = request.session.get('school_id')
    username = request.session.get('username') # Parent phone
    
    # 1. Multi-student handling
    students = StudentInfo.objects.filter(school_id=school_id, phone=username)
    reg_no = request.GET.get('student_id') or request.session.get('registration_no')
    student = students.filter(registration_no=reg_no).first() or students.first()
    
    if not student:
        messages.error(request, "No student profile found.")
        return redirect('parent_portal_dashboard')

    request.session['registration_no'] = student.registration_no

    # 2. Handle M-Pesa Payment Submission (POST)
    if request.method == "POST" and 'submit_mpesa' in request.POST:
        trans_code = request.POST.get('transaction_code').strip().upper()
        amount = request.POST.get('amount')
        date_paid = request.POST.get('date_of_payment')
        term = request.POST.get('term')

        # Check if this transaction code already exists (Prevent duplicates)
        if Fee.objects.filter(transaction_code=trans_code, school_id=school_id).exists():
            messages.error(request, f"Transaction code {trans_code} has already been reported.")
        else:
            Fee.objects.create(
                registration_no=student,
                school_id=school_id,
                mode_of_payment="Mpesa",
                transaction_code=trans_code,
                amount=amount,
                date_of_payment=date_paid,
                term=term,
                year=datetime.now().year,
                status='Pending' # Parent submissions start as Pending
            )
            messages.success(request, "Payment reported successfully! Awaiting admin confirmation.")
        return redirect('parent_student_portal_fee_payment')

    # 3. Fetch Data for Display
    current_year = str(datetime.now().year)
    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', current_year)
    grade_obj = get_object_or_404(Grade, school_id=school_id, name=student.grade)
    
    # Only 'Confirmed' payments count toward the paid balance
    all_fee_records = Fee.objects.filter(registration_no=student, school_id=school_id).order_by('-date_of_payment')
    confirmed_payments = all_fee_records.filter(status='Confirmed')
    pending_payments = all_fee_records.filter(status='Pending')

    total_fees_paid = confirmed_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    expected_fee = grade_obj.expected_fee
    balance = expected_fee - total_fees_paid

    context = {
        "students": students,
        "student": student,
        "expected_fee": expected_fee,
        "total_fees_paid": total_fees_paid,
        "balance": balance,
        "confirmed_payments": confirmed_payments,
        "pending_payments": pending_payments,
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
    }

    return render(request, 'parent_portal/fee.html', context)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

def parent_portal_student_attendance(request):
    school_id = request.session.get('school_id')
    username = request.session.get('username')  # Parent's phone number
    
    # 1. Fetch all children linked to this phone number
    students = StudentInfo.objects.filter(school_id=school_id, phone=username)
    
    if not students.exists():
        messages.error(request, "No students found.")
        return redirect('login')

    # 2. Determine which student's attendance to show
    # Priorities: URL parameter (?student_id=...) -> Session -> First child found
    reg_no = request.GET.get('student_id') or request.session.get('registration_no')
    
    if reg_no:
        student = students.filter(registration_no=reg_no).first()
        if not student:
            student = students.first()
    else:
        student = students.first()

    # Sync session to keep the selection across different pages
    request.session['registration_no'] = student.registration_no
    registration_no = student.registration_no

    current_year = str(datetime.now().year)
    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', current_year)
    # 3. Fetch Attendance Data for the SELECTED student
    attendance_records = StudentAttendance.objects.filter(
        school_id=school_id,
        registration_no=registration_no,
        term = term_filter,
        year = year_filter
    ).order_by('-date_of_attendance')

    present_days = attendance_records.filter(status='Present').count()
    absent_days = attendance_records.filter(status='Absent').count()
    total_days = attendance_records.count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    context = {
        "students": students,  # All children for the switcher
        "student": student,    # The currently selected child
        "attendance_records": attendance_records,
        "present_days": present_days,
        "absent_days": absent_days,
        "total_days": total_days,
        "attendance_percentage": attendance_percentage,
    }

    return render(
        request,
        'parent_portal/attendance.html',
        context
    )
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

def parent_student_portal_leave_application(request):
    school_id = request.session.get('school_id')
    username = request.session.get('username')  # Parent's phone number
    
    # 1. Fetch the selected child's registration number from session
    # (This was set by the switcher on the dashboard/fees/attendance pages)
    registration_no = request.session.get('registration_no')
    
    if not registration_no:
        messages.error(request, "Please select a student first.")
        return redirect('parent_portal_dashboard')

    # 2. Get the specific student instance
    student = get_object_or_404(StudentInfo, school_id=school_id, registration_no=registration_no)

    if request.method == "POST":
        date_of_leave = request.POST.get('date_of_leave')
        reason = request.POST.get('reason')

        # 3. Create the leave record for the SPECIFIC student selected
        LeaveManagement.objects.create(
            school_id=school_id,
            registration_no=student, # This is the ForeignKey to StudentInfo
            date_of_leave=date_of_leave,
            reason='Other Reason',
            phone=username, # Parent's phone used for login
            other_reason=reason,
            status='Pending'
        )
        
        messages.success(request, f"✅ Leave application for {student.first_name} submitted successfully.")

    return redirect('parent_student_portal_leave_statement')

def parent_student_portal_leave_statement(request):
    school_id = request.session.get('school_id')
    username = request.session.get('username') # Parent's phone number

    # 1. Fetch all children linked to this phone number
    students = StudentInfo.objects.filter(school_id=school_id, phone=username)
    
    # 2. Determine which student's leaves to show
    # Priorities: URL parameter -> Session -> First child found
    reg_no = request.GET.get('student_id') or request.session.get('registration_no')
    
    if reg_no:
        student = students.filter(registration_no=reg_no).first()
        if not student:
            student = students.first()
    else:
        student = students.first()

    # Sync session so the selection persists across the portal
    if student:
        request.session['registration_no'] = student.registration_no
        registration_no = student.registration_no
    else:
        messages.error(request, "No student records found.")
        return redirect('parent_portal_dashboard')
    
    current_year = str(datetime.now().year)
    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', current_year)

    # 3. Fetch Leave Data for the SELECTED student
    leave_records = LeaveManagement.objects.filter(
        school_id=school_id,
        registration_no_id=registration_no,
        term = term_filter,
        year = year_filter
    ).order_by('-date_of_leave')
    
    context = {
        "students": students,  # For the selection pills
        "student": student,    # The current student being viewed
        "leave_records": leave_records,
        "total_leaves": leave_records.count(),
        "approved_leaves": leave_records.filter(status='Approved').count(),
        "pending_leaves": leave_records.filter(status='Pending').count(),
        "rejected_leaves": leave_records.filter(status='Rejected').count(),
    }

    return render(
        request,
        'parent_portal/leave.html',
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




def get_cbc_level_and_remark(avg_level):
    """Determines the CBC level and remark based on a numeric average level (e.g., 1.0-3.0)."""
    if avg_level is None:
        return {'level': 'N/A', 'remark': 'No Data'}
    if avg_level >= 2.5:
        return {'level': 'EE', 'remark': 'Exceeding Expectations'}
    if avg_level >= 1.5:
        return {'level': 'ME', 'remark': 'Meeting Expectations'}
    if avg_level >= 0.5:
        return {'level': 'AE', 'remark': 'Approaching Expectations'}
    return {'level': 'BE', 'remark': 'Below Expectations'}

# --- THE MAIN DJANGO VIEW ---
from django.urls import reverse
@login_required


def parent_student_portal_academics(request):
    school_id = request.session.get('school_id')
    username = request.session.get('username') # Parent's phone number

    # 1. --- Multi-Student Handling ---
    students = StudentInfo.objects.filter(school_id=school_id, phone=username)
    
    # Priority: URL param -> Session -> First child
    registration_no = request.GET.get('student_id') or request.session.get('registration_no')
    
    student = students.filter(registration_no=registration_no).first()
    if not student:
        student = students.first()
        registration_no = student.registration_no if student else None

    # Sync session
    request.session['registration_no'] = registration_no

    if not student:
        messages.error(request, "No student records found.")
        return redirect('parent_portal_dashboard')

    # 2. --- Filters ---
    current_year = str(datetime.now().year)
    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', current_year)
    
    # Improved Query Filtering
    base_marks_qs = SubStrandMark.objects.filter(
        student=student,
        term=term_filter,
        year=year_filter
    ).select_related('sub_strand__strand', 'recorded_by')

    # 3. --- Subject Performance Summary ---
    subject_summaries_qs = base_marks_qs.values(
        'sub_strand__strand__subject'
    ).annotate(
        mean_score=Avg('score'),
        mean_level=Avg('level')
    ).order_by('sub_strand__strand__subject')

    subject_summaries = []
    for summary in subject_summaries_qs:
        subject_name = summary['sub_strand__strand__subject']
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
    )

    competency_map = {
        c.competency: get_cbc_level_and_remark(c.level or None)['level']
        for c in competency_qs
    }
    
    # Fetch distinct competencies for this specific student
    CORE_COMPETENCIES = list(LearnerCompetency.objects.filter(
        school_id=school_id,
        student=student
    ).values_list('competency', flat=True).distinct())

    competency_ratings = []
    for competency_name in CORE_COMPETENCIES:
        rating = competency_map.get(competency_name, 'N/A')
        # Assign Color
        color_map = {'EE': 'success', 'ME': 'info', 'AE': 'warning', 'BE': 'danger'}
        color = color_map.get(rating, 'secondary')
        
        competency_ratings.append({"competency": competency_name, "rating": rating, "color": color})
    
    # 6. --- Placeholder / Links ---
    report_url = reverse("report_card") + f"?registration_no={registration_no}&term={term_filter}"

    latest_report = {
        "term": term_filter,
        "link": report_url,
        "date": datetime.now().strftime("%B %d, %Y")
    }
    
    context = {
        "students": students, # Pass all children for the switcher
        "student": student,   # Selected child
        "term_choices": ['Term 1', 'Term 2', 'Term 3'],
        "current_term": term_filter,
        "overall_mean": overall_mean,
        "subject_summaries": subject_summaries,
        "competency_ratings": competency_ratings,
        "latest_report": latest_report,
        "upcoming_assignments": [],
        "year_choices": SubStrandMark.objects.filter(student=student).values_list('year', flat=True).distinct().order_by('-year'),
        "selected_year": year_filter,
    }

    return render(request, 'parent_portal/academics.html', context)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from datetime import datetime

@login_required
def parent_student_view_learning_area_breakdown(request, subject):
    school_id = request.session.get('school_id')
    username = request.session.get('username')  # Parent's phone number
    
    # 1. --- Multi-Student Handling ---
    # Fetch all students linked to this phone number to verify ownership
    students = StudentInfo.objects.filter(school_id=school_id, phone=username)
    
    # Get the specific registration number from GET or Session
    registration_no = request.GET.get('student_id') or request.session.get('registration_no')
    
    # Securely get the student (ensures the student belongs to this parent)
    student = get_object_or_404(students, registration_no=registration_no)

    # 2. --- Filters ---
    term_filter = request.GET.get('term', 'Term 1')
    year_filter = request.GET.get('year', str(datetime.now().year))

    # 3. --- Querying Marks ---
    marks_qs = SubStrandMark.objects.filter(
        student=student,
        sub_strand__strand__subject=subject,
        term=term_filter,
        year=year_filter
    ).select_related('sub_strand__strand', 'recorded_by').order_by('date_recorded')

    # 4. --- Fetch Teacher Info ---
    teacher_role = TeachersRole.objects.filter(
        school_id=school_id,
        grade=student.grade,
        subject__icontains=subject
    ).select_related('registration_no').first()

    teacher_name = f"{teacher_role.registration_no.first_name} {teacher_role.registration_no.surname}" if teacher_role else "N/A"

    # 5. --- Build Response Data ---
    data = []
    for mark in marks_qs:
        data.append({
            "sub_strand": mark.sub_strand.name,
            "score": float(mark.score) if mark.score else 0, # Ensure float for JSON
            "term": mark.term,
            "year": mark.year,
            "recorded_by": teacher_name
        })

    return JsonResponse({
        "student": f"{student.first_name} {student.surname}",
        "subject": subject,
        "term": term_filter,
        "year": year_filter,
        "marks": data
    })

from ..models import Announcement
def parents_announcements(request):
    school_id = request.session.get('school_id')
    registration_no = request.session.get('registration_no')

    announcements = Announcement.objects.filter(
        Q(target_audience='PARENTS') | 
        Q(target_audience__icontains=registration_no)
    , school_id=school_id).order_by('-created_at')

    context = {
        "announcements": announcements,
    }

    return render(
        request,
        'parent_portal/announcements.html',
        context 
    )


    