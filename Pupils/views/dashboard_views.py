from ..models import*
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.utils.timezone import now
from datetime import datetime
from decimal import Decimal
from ..utils.per_school_db_utils import get_school_db_alias_from_session


def dashboard(request):
    school_id = request.session.get('school_id')
    term_choices = ['Term 1', 'Term 2', 'Term 3']
    

    for _ in messages.get_messages(request):
        pass

    alias = get_school_db_alias_from_session(request)
    today = now().date()

    # 🔹 Use GET instead of POST
    term = request.GET.get('term', '').strip()
    request.session['term'] = term  
    year = datetime.now().year
    request.session['year'] = year

    # Core stats
    pupils = StudentInfo.objects.filter(school_id = school_id).count()
    teachers = TeacherInfo.objects.filter(school_id = school_id).count()
    present_teachers = TeacherAttendance.objects.filter(
        school_id = school_id,
        date_of_attendance=today, status='Present'
    ).count()

    # Fee balances per grade
    grade_fees_balances = []
    grades = list(
        GradeStream.objects
        .filter(school_id = school_id)
        .values_list('grade', flat=True)
        .distinct()
        .order_by('grade')
    )
    if not grades:
        grade_fee_balances = [0,]
    else:
        if Grade.objects.filter(school_id = school_id).count() == 0:
            grade_fees_balances = [0,]
        else:
            for g in grades:
                expected_fee = get_object_or_404(Grade.objects.filter(school_id = school_id), name=g).expected_fee
                no_of_students = StudentInfo.objects.filter(school_id = school_id,grade=g).count()

                fee_filter = {
                    "registration_no__in": StudentInfo.objects
                    .filter(school_id = school_id,grade=g)
                    .values_list('registration_no', flat=True)
                }
                if term:
                    fee_filter["term"] = term
                    fee_filter['year'] = year

                total_paid = Fee.objects.filter(school_id = school_id,**fee_filter).aggregate(Sum('amount'))['amount__sum'] or 0
                grade_balance = (expected_fee * Decimal(no_of_students)) - Decimal(total_paid)
                grade_fees_balances.append(grade_balance)

    total_balance = sum(grade_fees_balances)

    # Fees (global)
    fee_query = Fee.objects.filter(school_id = school_id).all()
    if term:
        fee_query = fee_query.filter(term=term,year = year)
    fee_paid = fee_query.aggregate(Sum('amount'))['amount__sum'] or 0

    # Leave data
    leave_query = LeaveManagement.objects.filter(school_id = school_id,return_date__isnull=True)
    if term:
        leave_query = leave_query.filter(term=term,year = year)
    leave_data = leave_query.count()

    # Attendance
    present_pupils = PupilAttendance.objects.filter(
        school = school_id,
        date_of_attendance=today, status='Present'
    ).count()
    
    try:
        attendance_pecentage = (present_pupils * 100) / pupils
    except ZeroDivisionError:
        attendance_pecentage = 0
    print("Attendance rate: ",attendance_pecentage)
    return render(
        request,
        'pupil/dashboard.html',
        {
            "term_choices": term_choices,
            "year": year,
            "selected_term": term,
            "pupils": pupils,
            "teachers": teachers,
            "present_teachers": present_teachers,
            "present_pupils": present_pupils,
            "attendance_pecentage": round(attendance_pecentage,2),
            "fee_paid": fee_paid,
            "fee_balance": total_balance,
            "leave_data": leave_data,
        },
    )
