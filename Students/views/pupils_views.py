# --- Imports ---
from datetime import datetime
from collections import defaultdict
from decimal import Decimal
import io
import os
import zipfile
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, models, transaction, connection
from django.db.models import Q, Sum, Count, Case, When, IntegerField
from django.db.models.functions import ExtractYear, ExtractMonth, TruncMonth
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from fpdf import FPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import pymysql

from ..forms import *
from ..models import *

def reg_config(request):
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
                target_type = 'student'
            )
            messaages.success(request,f'student registration format: {reg_format} updated')
            return redirect('manage_details')


# --- Utility function for next registration number ---




def reg_config(request):
    school_id = request.session.get('school_id')
    school_instance = MasterSchool.objects.get(id = school_id)

    if request.method == 'POST':
        reg_format = request.POST.get('reg_format')
        if '/' in reg_format:
            messages.error(request,f'Invalid format {reg_format} use (-) instead of /')
            return redirect('manage_details')
        else:

            RegConfig.objects.update_or_create(
                school = school_instance,
                reg_format = reg_format,
                target_type = 'student'

            )
            
            messages.success(request,f'student registration format: {reg_format} updated')
            return redirect('manage_details')

def get_next_registration_number(school_id,existing_regnos):
    reg_format = RegConfig.objects.filter(school_id = school_id,target_type = 'student').first()
    formt = reg_format.reg_format.upper() if reg_format != None else ''
    


    for i in range(1, 20000):  # allow up to 19999 pupils
        reg_no = f"{formt}{i:02d}"
        if reg_no not in existing_regnos:
            return reg_no
    return None
def get_next_registration_number(school_id,existing_regnos):
        reg_format = RegConfig.objects.filter(school_id = school_id,target_type = 'teacher').first()
        formt = reg_format.reg_format.upper()
        for i in range (1,500):
            reg_no = f'{formt}{i:02d}'
            if reg_no not in existing_regnos:
                return reg_no
            return None
            

# --- Streams API ---
@login_required
@require_http_methods(["GET"])
def get_streams(request):
    
    school_id = request.session.get('school_id')
    try:
        grade = (request.GET.get("grade") or "").strip()
        base_qs = GradeStream.objects.filter(school_id=school_id)

        if grade:
            streams = list(
                base_qs.filter(grade__iexact=grade)
                       .values_list("stream", flat=True)
                       .distinct()
                       .order_by("stream")
            )
            streams = [s for s in streams if s]
            return JsonResponse({"streams": streams})

        # No grade provided: return all grades -> streams mapping
        data = defaultdict(list)
        for g, s in base_qs.values_list("grade", "stream").order_by("grade", "stream"):
            if g and s and s not in data[g]:
                data[g].append(s)

        grades = sorted(data.keys())
        # Sort streams for each grade
        for k in data:
            data[k] = sorted(data[k])

        return JsonResponse({"streams_by_grade": dict(data), "grades": grades})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# --- student List ---
@login_required
def pupil_list(request):
    
    school_id = request.session.get('school_id')
    query = request.GET.get('search', '').strip()

    pupils = StudentInfo.objects.filter(school_id=school_id)
    if query:
        pupils = pupils.filter(registration_no__icontains=query)

    return render(request, 'students/pages/pupil_list.html', {'pupils': pupils, 'query': query})

# --- GradeStream Configuration ---
@login_required
def gradestream_config(request):
    
    school_id = request.session.get('school_id')

    if request.method == 'POST':
        grades = request.POST.getlist('grade[]')
        streams = request.POST.getlist('stream[]')
        created = 0
        school_instance = MasterSchool.objects.get(id = school_id)
        for grade, stream in zip(grades, streams):
            g, s = (grade or '').strip(), (stream or '').strip()
            if not g or not s:
                continue
            try:
                GradeStream.objects.get_or_create(school_id=school_id, grade=g, stream=s)
                created += 1
            except IntegrityError:
                pass

        if created:
            messages.success(request, f"{created} grade/stream pair(s) saved.")
        else:
            messages.info(request, "No new grade/stream pairs to save.")
        return redirect('manage_details')

    return redirect('manage_details')

from django.contrib.auth.hashers import make_password
# --- Manage Pupil Details ---

# inside models.py




@login_required
def manage_details(request):
    
    school_id = request.session.get('school_id')
    print('School id',school_id)
    school_instance = MasterSchool.objects.get(id = school_id)
    
    if not school_id:
        messages.error(request, "Session expired. Please login again.")
        return redirect('login')
    school_instance = get_object_or_404(MasterSchool, id=school_id)

    # Registration handling
    if request.method == "POST":
        form = RegisterForm(request.POST)

        
        type_of_user = "student"
        school_name = school_instance.school_name
        

        if form.is_valid():
            registration_no = form.cleaned_data["registration_no"]
            if StudentInfo.objects.filter(school_id = school_id, registration_no=registration_no).exists():
                messages.error(f"Student with registration {registration_no} already exists")
            else:
                username = form.cleaned_data["registration_no"]
                phone = form.cleaned_data["phone"]
                password = username
                # email = form.cleaned_data["email"] if form.cleaned_data["email"] else ''
                name = form.cleaned_data["first_name"]
                try:
                    obj = form.save(commit=False)
                    obj.school = school_instance
                    
                    # Enforce phone number format
                    s_phone = str(obj.phone)
                    if s_phone.startswith('0'):
                        s_phone = '254' + s_phone[1:]
                    elif not s_phone.startswith('254'):
                        s_phone = '254' + s_phone
                    obj.phone = int(s_phone[:12])
                    
                    obj.save()

                    Users.objects.create(
                        school=school_instance,
                        username=username,
                        school_name=school_name,
                        role=type_of_user,
                        password=make_password(password),
                        email='',
                        registration_no=registration_no,
                    )
                    


                    messages.success(request, f"✅ {name} registered successfully.")
                    return redirect("manage_details")
                except Exception as e:
                    messages.error(request, f"❌ Failed to register pupil: {str(e)}")
        else:
            print('Form is not valid',form.errors)
    else:
        form = RegisterForm()

    # Filtering
    query = request.GET.get("search", "").strip()
    grade = request.GET.get("grade", "").strip()
    stream = request.GET.get("stream", "").strip()

    
    pupils = StudentInfo.objects.filter(school_id=school_id)
    if query:
        pupils = pupils.filter(Q(registration_no__icontains=query) |
                               Q(first_name__icontains=query) |
                               Q(surname__icontains=query))
    if grade:
        pupils = pupils.filter(grade__iexact=grade)
    if stream:
        pupils = pupils.filter(stream__iexact=stream)

    # Grades for dropdown
    grades = GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct().order_by('grade')
    gradestream = GradeStream.objects.filter(school_id = school_id)
    # Suggested registration number
    existing_regnos = set(pupils.values_list('registration_no', flat=True))
    suggested_regno = get_next_registration_number(school_id,existing_regnos)
    reg_format = RegConfig.objects.filter(school_id = school_id,target_type = 'student')
    formt = reg_format.reg_format.upper() if reg_format != None else ''

    


    return render(request, "students/pages/register.html", {
        "form": form,
        "query": query,
        "pupils": pupils,
        "grades": grades,
        "selected_grade": grade,
        "selected_stream": stream,
        "suggested_regno": suggested_regno,
        'gradestream': gradestream,
        'reg_format': formt
    })

@login_required
def delete_grade_stream(request, id):
    school_id = request.session.get('school_id')
    gradestream = get_object_or_404(GradeStream, id=id, school_id=school_id)
    gradestream.delete()
    messages.success(request, "Grade configuration deleted successfully.")
    return redirect('manage_details')

@login_required 
def edit_grade_stream(request, id):
    school_id = request.session.get('school_id')
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            grade_obj = get_object_or_404(GradeStream, pk=id, school_id=school_id)
            grade_obj.grade = data.get('grade')
            grade_obj.stream = data.get('stream')
            grade_obj.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


# --- Update Pupil ---
@login_required
def update_pupil(request, reg_no):
    
    school_id = request.session.get('school_id')

    pupil = get_object_or_404(StudentInfo.objects.filter(school_id=school_id), registration_no=reg_no)

    if request.method == 'POST':
        form = RegisterForm(request.POST, instance=pupil)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            messages.success(request, f'{pupil.first_name} details updated successfully')
            return redirect('manage_details')
    else:
        form = RegisterForm(instance=pupil)

    grades = GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct().order_by('grade')

    return render(request, "students/pages/update_pupil.html", {'form': form, 'pupil': pupil, 'grades': grades})


@login_required
def promote_students(request):
    school_id = request.session.get('school_id')
    

    # CBC progression mapping
    cbc_promotion = {
        'PP1': 'PP2',
        'PP2': 'Grade 1',
        'Grade 1': 'Grade 2',
        'Grade 2': 'Grade 3',
        'Grade 3': 'Grade 4',
        'Grade 4': 'Grade 5',
        'Grade 5': 'Grade 6',
        'Grade 6': 'Grade 7',
        'Grade 7': 'Grade 8',
        'Grade 8': 'Grade 9',
        'Grade 9': 'Graduated',
    }

    grade = request.GET.get('grade', '')

    selected_stream = request.GET.get('stream', '')
    choices = list(GradeStream.objects.filter(school_id = school_id).values_list('stream'))
    stream_choices = []
    for choice in choices:
        stream_choices.append(choice[0])
    
    for stream in stream_choices:
        print("Stream choices: ",stream[0])

    students = []
    if grade:
        students = StudentInfo.objects.filter(
            school_id=school_id, grade=grade
        )

        if selected_stream:
            students = students.filter(stream=selected_stream)
        students = students.order_by('registration_no')

    if request.method == 'POST':
        selected_students = request.POST.getlist('students')
        promoted_count = 0

        with transaction.atomic():
            for reg_no in selected_students:
                student = StudentInfo.objects.filter(
                    school_id=school_id, registration_no=reg_no
                ).first()
                if student:
                    next_grade = cbc_promotion.get(student.grade)
                    if next_grade:
                        student.grade = next_grade
                        student.save()
                        promoted_count += 1

        messages.success(request, f'{promoted_count} students successfully promoted!')
        return redirect('manage_details')

    return render(request, 'students/pages/register.html', {
        'students': students,
        'grade': grade,
        'stream': selected_stream,
        'stream_choices': stream_choices
    })


# --- Delete Pupil ---
@login_required
def delete_pupil(request, reg_no):
    
    school_id = request.session.get('school_id')

    pupil = get_object_or_404(StudentInfo.objects.filter(school_id=school_id), registration_no=reg_no)
    student_as_user = get_object_or_404(Users.objects.filter(school_id = school_id,registration_no = reg_no))
    parent_phone = get_object_or_404(StudentInfo.objects.filter(school_id = school_id,registration_no = reg_no)).phone
    parent_as_user = get_object_or_404(Users.objects.filter(school_id = school_id,username = str(parent_phone)))
    if request.method == 'POST':
        pupil.delete()
        student_as_user.delete()
        parent_as_user.delete()
        messages.success(request, f"{pupil.first_name} data deleted successfully")
        return redirect('manage_details')

    return render(request, 'students/pages/delete_pupil.html', {'pupil': pupil})

from decimal import Decimal
from collections import defaultdict
import json
import calendar



# ----------------- Fee Summary -----------------
def fee_summary(school_id,term,year,filter_type):

    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.localdate()
    
    

    # Fetch expected fee per grade
    grade_fees = Grade.objects.filter(school_id=school_id).values("name", "term", "expected_fee")

    # Count students per grade & stream
    students_per_group = (
        StudentInfo.objects
        .filter(school_id=school_id)
        .values("grade", "stream")
        .annotate(total_students=Count("registration_no"))
    )

    # Total paid fee per student
    paid_per_student = (
            Fee.objects
            .filter(school_id=school_id,status = 'Confirmed')
            .values("registration_no")
            .annotate(total_paid=Sum("amount"))
        )
    if term:
        paid_per_student = (
            Fee.objects
            .filter(school_id=school_id,term=term)
            .values("registration_no")
            .annotate(total_paid=Sum("amount"))
        )
    if year:
        paid_per_student = (
            Fee.objects
            .filter(school_id=school_id,year=year)
            .values("registration_no")
            .annotate(total_paid=Sum("amount"))
        )
    if filter_type == 'today':
        paid_per_student = paid_per_student.filter(date_of_payment=today)
    elif filter_type == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        paid_per_student = paid_per_student.filter(date_of_payment__gte=week_start, date_of_payment__lte=today)
    
    paid_dict = {p["registration_no"]: p["total_paid"] for p in paid_per_student}

    # Build fee summary
    summary = []
    for s in students_per_group:
        grade_name = s["grade"]
        stream_name = s["stream"]
        student_count = s["total_students"]

        grade_fee_obj = next((g for g in grade_fees if g["name"] == grade_name), None)
        expected_fee = grade_fee_obj["expected_fee"] if grade_fee_obj else 0
        expected_total = expected_fee * student_count

        reg_nos = StudentInfo.objects.filter(
            school=school_id, grade=grade_name, stream=stream_name
        ).values_list("registration_no", flat=True)

        paid_total = sum(paid_dict.get(reg, 0) for reg in reg_nos)
        balance = expected_total - Decimal(paid_total)

        summary.append({
            "grade": grade_name,
            "stream": stream_name,
            "students": student_count,
            "expected_total": expected_total,
            "total_paid": paid_total,
            "balance": balance,
        })
    
    return summary

# ----------------- Fee Payment -----------------
@login_required

def fee_payment(request):
    school_id = request.session.get("school_id")
    school_instance = get_object_or_404(MasterSchool, id=school_id)
    
    # Clear existing messages for a clean state
    for _ in messages.get_messages(request):
        pass

    # ----------------- 1. Verification Actions (From Modal) -----------------
    # This handles the buttons inside your new verification modal
    if request.method == "POST" and request.POST.get('keep_modal') == 'true':
        fee_id = request.POST.get('fee_id')
        action = request.POST.get('action')
        fee_record = get_object_or_404(Fee, id=fee_id, school_id=school_id)
        
        if action == 'approve':
            fee_record.status = 'Confirmed'
            fee_record.save()
            messages.success(request, f"Payment {fee_record.transaction_code} confirmed for {fee_record.registration_no.first_name}")
        elif action == 'reject':
            fee_record.status = 'Rejected'
            fee_record.save()
            messages.warning(request, "Transaction rejected.")
        
        # Redirect back with a flag to re-open the modal automatically
        return redirect(f"{reverse('fee_payment')}?show_verify=true")

    # ----------------- 2. Standard Payment Submission -----------------
    form_type = request.POST.get("form_type", "").strip()
    form = FeeForm(request.POST or None)

    if request.method == "POST" and form_type == "payment" and form.is_valid():
        registration_no = form.cleaned_data["registration_no"]
        
        # Check if student exists
        if not StudentInfo.objects.filter(school_id=school_id, registration_no=registration_no.registration_no).exists():
            messages.error(request, f"Pupil with registration number {registration_no} does not exist.")
            return redirect('fee_payment')

        obj = form.save(commit=False)
        obj.registration_no = registration_no
        obj.school = school_instance
        obj.status = 'Confirmed'  # Admin-entered payments are confirmed by default
        obj.save()
        messages.success(request, "Payment recorded successfully!")
        return redirect("fee_payment")

    # ----------------- 3. Filtering & Display (Confirmed Only) -----------------
    query = request.GET.get("search", "").strip()
    grade = request.GET.get("grade", "").strip()
    stream = request.GET.get("stream", "").strip()
    term = request.GET.get("term", "").strip()

    # We only show Confirmed payments in the main table
    fees_qs = Fee.objects.filter(school_id=school_id, status='Confirmed')

    if query:
        fees_qs = fees_qs.filter(registration_no__registration_no__icontains=query)
    if grade:
        reg_nos_list = StudentInfo.objects.filter(school_id=school_id, grade__iexact=grade).values_list("registration_no", flat=True)
        fees_qs = fees_qs.filter(registration_no__registration_no__in=reg_nos_list)
    if stream:
        reg_nos_list = StudentInfo.objects.filter(school_id=school_id, stream__iexact=stream).values_list("registration_no", flat=True)
        fees_qs = fees_qs.filter(registration_no__registration_no__in=reg_nos_list)
    if term:
        fees_qs = fees_qs.filter(term__iexact=term)

    fees = fees_qs.values("registration_no", "term").annotate(total_paid=Sum("amount")).order_by("registration_no", "term")

    # ----------------- 4. Pending Payments (For Modal) -----------------
    pending_fees = Fee.objects.filter(school_id=school_id, status='Pending').select_related('registration_no')
    pending_fees_count = pending_fees.count()

    # ----------------- 5. Grade Fees Logic -----------------
    grade_names = GradeStream.objects.filter(school_id=school_id).values_list("grade", flat=True).distinct()
    for name in grade_names:
        if name:
            Grade.objects.get_or_create(school_id=school_id, name=name)

    grades = list(Grade.objects.filter(school_id=school_id).order_by("name"))
    
    if request.method == "POST" and form_type == "grade_fee":
        term_select = request.POST.get("term_select", "").strip()
        if not term_select:
            messages.error(request, "Please select a term before updating fees.")
            return redirect("fee_payment")

        valid = True
        for g in grades:
            gform = GradeFeeForm(request.POST, instance=g, prefix=f"grade_{g.id}")
            if gform.is_valid():
                instance = gform.save(commit=False)
                instance.school = school_instance
                instance.term = term_select
                instance.save()
            else:
                valid = False

        if valid:
            messages.success(request, "Fees updated successfully!")
        else:
            messages.error(request, "Some rows had errors.")
        return redirect("fee_payment")

    grade_forms = [GradeFeeForm(instance=g, prefix=f"grade_{g.id}") for g in grades]
    term_choices = ['Term 1','Term 2','Term 3']

    return render(request, "students/pages/fee.html", {
        "reg_nos": StudentInfo.objects.filter(school_id=school_id).values_list("registration_no", flat=True),
        "form": form,
        "fees": fees,
        "pending_fees": pending_fees,
        "pending_fees_count": pending_fees_count,
        "forms": grade_forms,
        "grades": grades,
        "query": query,
        "selected_grade": grade,
        "selected_stream": stream,
        "selected_term": term,
        "term_choices": term_choices
    })
from django.urls import reverse
@login_required
def verify_mpesa_payments(request):
    school_id = request.session.get('school_id')
    
    # --- 1. Handle Verification Actions (Approve/Reject) ---
    if request.method == "POST" and request.POST.get('keep_modal') == 'true':
        fee_id = request.POST.get('fee_id')
        action = request.POST.get('action')
        fee_record = get_object_or_404(Fee, id=fee_id, school_id=school_id)
        
        if action == 'approve':
            fee_record.status = 'Confirmed'
            fee_record.save()
            messages.success(request, f"Confirmed: {fee_record.transaction_code}")
        elif action == 'reject':

            fee_record.status = 'Rejected' 
            fee_record.save()
            messages.warning(request, "Transaction rejected.")
        
        # Redirect back to the same page but with a flag to keep the modal open
        return redirect(f"{reverse('fee_payment')}?show_verify=true")
    # --- 2. Existing Search/Filter Logic ---
    # (Assuming your existing logic for fetching 'fees' queryset is here)
    fees = Fee.objects.filter(school_id=school_id, status='Confirmed') # Main table shows confirmed
    
    # --- 3. Fetch Pending Data for Modal ---
    pending_fees = Fee.objects.filter(school_id=school_id, status='Pending').select_related('registration_no_id')
    pending_fees_count = pending_fees.count()

    context = {
        'fees': fees,
        'pending_fees': pending_fees,
        'pending_fees_count': pending_fees_count,
        'reg_nos': StudentInfo.objects.filter(school_id=school_id).values_list('registration_no_id', flat=True),
        'grades': Grade.objects.filter(school_id=school_id),
        'term_choices': ['Term 1', 'Term 2', 'Term 3'],
        # ... include forms for grade fees and payment
    }
    return render(request, 'student/pages/fee.html', context)
# ---------------- Individual Fee List -----------------
@login_required
def individual_fee_list(request, reg_no):
    school_id = request.session.get('school_id')
    
    for _ in messages.get_messages(request):
        pass

    student = get_object_or_404(StudentInfo.objects.filter(school_id=school_id), registration_no=reg_no)
    fees = Fee.objects.filter(school_id=school_id, registration_no=reg_no).order_by('term')

    grade_fee = get_object_or_404(Grade.objects.filter(school_id=school_id), name=student.grade)
    expected_fee = grade_fee.expected_fee
    total_paid = sum(fee.amount for fee in fees)
    balance = expected_fee - Decimal(total_paid)

    query = request.GET.get('search','').strip()
    if query:
        fees = Fee.objects.filter(school_id=school_id, registration_no=reg_no, term__icontains=query)
        total_paid = sum(fee.amount for fee in fees)
        balance = expected_fee - Decimal(total_paid)

    return render(request, 'students/pages/individual_fee_list.html', {
        'student': student,
        'fees': fees,
        'expected_fee': expected_fee,
        'balance': balance,
    })


# ----------------- Fee Dashboard -----------------
@login_required
def fee_dashboard(request):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass

    term = request.GET.get('term', '').strip()
    year = request.GET.get('year', '').strip()
    filter_type = request.GET.get('filter_type', '').strip()  # NEW: today, weekly, all

    years = Fee.objects.filter(school_id=school_id).values_list("year", flat=True).distinct().order_by("-year")
    fees = Fee.objects.filter(school_id=school_id,status = 'Confirmed')

    # Apply date-based filters
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.localdate()
    
    if filter_type == 'today':
        fees = fees.filter(date_of_payment=today)
    elif filter_type == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        fees = fees.filter(date_of_payment__gte=week_start, date_of_payment__lte=today)
    
    if term:
        fees = fees.filter(term=term)
    if year:
        fees = fees.filter(year=year)

    # Chart 1: Cash vs Mpesa
    student_map = {s.registration_no: (s.grade, s.stream) for s in StudentInfo.objects.filter(school_id=school_id)}
    chart_map = {}
    for row in fees.values("registration_no", "mode_of_payment").annotate(total=Sum("amount")):
        reg_no = row["registration_no"]
        grade, stream = student_map.get(reg_no, ("", ""))
        if not grade:
            continue
        key = f"{grade} - {stream}"
        if key not in chart_map:
            chart_map[key] = {"Cash": 0.0, "Mpesa": 0.0}
        pm = (row["mode_of_payment"] or "").title()
        if pm in ("Cash", "Mpesa"):
            chart_map[key][pm] += float(row["total"] or 0.0)

    labels = sorted(chart_map.keys())
    cash_data = [chart_map[k]["Cash"] for k in labels]
    mpesa_data = [chart_map[k]["Mpesa"] for k in labels]

    # Chart 2: Pie chart totals
    total_cash = sum(cash_data)
    total_mpesa = sum(mpesa_data)

    # Chart 3: Monthly totals
    monthly_rows = fees.annotate(month=models.functions.ExtractMonth("date_of_payment")).values("month").annotate(total=Sum("amount")).order_by("month")
    month_labels = [calendar.month_name[r["month"]] for r in monthly_rows]
    month_totals = [float(r["total"] or 0.0) for r in monthly_rows]

    # Chart 4: Stacked bar by Grade only
    grade_totals = defaultdict(lambda: {"Cash": 0.0, "Mpesa": 0.0})
    for key, vals in chart_map.items():
        grade = key.split(" - ")[0]
        grade_totals[grade]["Cash"] += vals["Cash"]
        grade_totals[grade]["Mpesa"] += vals["Mpesa"]

    grade_labels = sorted(grade_totals.keys())
    grade_cash = [grade_totals[g]["Cash"] for g in grade_labels]
    grade_mpesa = [grade_totals[g]["Mpesa"] for g in grade_labels]
    fee_sum = fee_summary(school_id,term,year if year != '' else 0,filter_type)
    print(fee_sum)
    context = {
        "term": term,
        "year": year,
        "years": years,
        "fee_balances": fee_sum,

        "labels_json": json.dumps(labels),
        "cash_json": json.dumps(cash_data),
        "mpesa_json": json.dumps(mpesa_data),

        "total_cash_json": total_cash,
        "total_mpesa_json": total_mpesa,

        "month_labels_json": json.dumps(month_labels),
        "month_totals_json": json.dumps(month_totals),

        "grade_labels_json": json.dumps(grade_labels),
        "grade_cash_json": json.dumps(grade_cash),
        "grade_mpesa_json": json.dumps(grade_mpesa),
    }
    return render(request, "students/pages/fee_dashboard.html", context)


@login_required
def attendance_dashboard(request):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    

    term = request.GET.get("term", "").strip()
    year = request.GET.get("year", "").strip()
    date_str = (request.GET.get("date") or '').strip()
    today_flag = (request.GET.get("today") == '1')
    filter_type = request.GET.get("filter_type", "").strip()  # NEW: today, weekly, all

    # Available years for filter
    years_qs = StudentAttendance.objects.filter(school_id=school_id).dates("date_of_attendance", "year")
    years = [str(y.year) for y in years_qs]

    # Base queryset
    qs = StudentAttendance.objects.filter(school_id=school_id)
    if term:
        qs = qs.filter(term=term)
    if year:
        qs = qs.filter(date_of_attendance__year=year)

    # Date/today/weekly filter
    from django.utils import timezone
    from datetime import datetime as _dt, timedelta
    
    today = timezone.localdate()
    
    if filter_type == 'today':
        qs = qs.filter(date_of_attendance=today)
    elif filter_type == 'weekly':
        week_start = today - timedelta(days=today.weekday())
        qs = qs.filter(date_of_attendance__gte=week_start, date_of_attendance__lte=today)
    elif today_flag:
        qs = qs.filter(date_of_attendance=today)
    elif date_str:
        try:
            sel_date = _dt.strptime(date_str, '%Y-%m-%d').date()
            qs = qs.filter(date_of_attendance=sel_date)
        except ValueError:
            # Ignore invalid date input
            pass

    # Chart 1: Attendance by Grade-Stream
    students = {
        s.registration_no: (s.grade, s.stream)
        for s in StudentInfo.objects.filter(school_id=school_id)
    }

    chart_map = defaultdict(lambda: {"Present": 0, "Absent": 0})
    for a in qs:
        grade, stream = students.get(a.registration_no, ("", ""))
        if not grade:
            print("Grade not found: ",grade)
        key = f"{grade} - {stream}"
        chart_map[key][a.status] += 1
    print("Chart map: ",chart_map)

    labels = sorted(chart_map.keys())
    present_data = [chart_map[k]["Present"] for k in labels]
    absent_data = [chart_map[k]["Absent"] for k in labels]

    total_present = sum(present_data)
    total_absent = sum(absent_data)

    # Chart 2: Monthly line chart
    monthly_qs = (
        qs.annotate(month=models.functions.ExtractMonth("date_of_attendance"))
        .values("month")
        .annotate(
            present=Sum(Case(When(status="Present", then=1), default=0, output_field=IntegerField())),
            absent=Sum(Case(When(status="Absent", then=1), default=0, output_field=IntegerField())),
        )
        .order_by("month")
    )
    month_labels = [calendar.month_name[r["month"]] for r in monthly_qs]
    month_present = [int(r["present"] or 0) for r in monthly_qs]
    month_absent = [int(r["absent"] or 0) for r in monthly_qs]

    # Chart 3: Stacked bar by Grade
    grade_totals = defaultdict(lambda: {"Present": 0, "Absent": 0})
    
    for key, vals in chart_map.items():
        grade = key.split(" - ")[0]
        grade_totals[grade]["Present"] += vals["Present"]
        grade_totals[grade]["Absent"] += vals["Absent"]

    
    grade_labels = sorted(grade_totals.keys())
    grade_present = [grade_totals[g]["Present"] for g in grade_labels]
    grade_absent = [grade_totals[g]["Absent"] for g in grade_labels]
    


    context = {
        "term": term,
        "year": year,
        "years": years,

        "labels_json": json.dumps(labels),
        "present_json": json.dumps(present_data),
        "absent_json": json.dumps(absent_data),

        "total_present_json": total_present,
        "total_absent_json": total_absent,

        "month_labels_json": json.dumps(month_labels),
        "month_present_json": json.dumps(month_present),
        "month_absent_json": json.dumps(month_absent),

        "grade_labels_json": json.dumps(grade_labels),
        "grade_present_json": json.dumps(grade_present),
        "grade_absent_json": json.dumps(grade_absent),
    }
    return render(request, "students/pages/attendance_dashboard.html", context)


@login_required
def leave_application_approval(request,leave_id):
    school_id = request.session.get('school_id')
    if not school_id:
        messages.error(request, "No school selected in session.")
        return redirect("leave_home")

    

    leave_instance = get_object_or_404(LeaveManagement.objects.filter(school_id=school_id), id=leave_id)

    if request.method == "POST":
        term = request.POST.get("term_select", "").strip()
        if not term:
            messages.error(request, "Please provide a valid term.")
            return redirect("leave_home")
        try:
            
            leave_instance.status = "Approved"
            leave_instance.save()
            messages.success(request, "Leave approved successfully.")
            return redirect("leave_home")
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return redirect("leave_home")

    return render(request, "students/pages/leave.html", {"leave": leave_instance})

def reject_leave_request(request, leave_id):
    school_id = request.session.get('school_id')

    if not school_id:
        messages.error(request, "No school selected in session.")
        return redirect("leave_home")

    

    leave_instance = get_object_or_404(LeaveManagement.objects.filter(school_id=school_id), id=leave_id)

    if request.method == "POST":
        term = request.POST.get("term_select", "").strip()
        if not term:
            messages.error(request, "Please provide a valid term.")
            return redirect("leave_home")
        else:
            try:
                leave_instance.status = "Rejected"
                leave_instance.term = term
                leave_instance.save()
                messages.success(request, "Leave request rejected successfully.")
                return redirect("leave_home")
            except ValueError:
                messages.error(request, "An error occurred while rejecting the leave request.")
                return redirect("leave_home")

    return render(request, "students/pages/leave.html", {"leave": leave_instance}) 

# Ajax codes.....
from .whatsapp_view import send_whatsapp_message

from django.views.decorators.http import require_POST
@require_POST
def approve_leave_request_ajax(request, leave_id):
    """Handles AJAX request to approve a leave application."""
    school_id = request.session.get('school_id')
    if not school_id:
        return JsonResponse({'success': False, 'message': 'No school selected in session.'}, status=403)

    # Note: If you rely on 'alias', ensure get_school_db_alias_from_session is run if needed.
    # 

    try:
        # Load JSON payload sent by Fetch API
        data = json.loads(request.body)
        term = data.get('term_select') # The term from the modal's select box

        if not term:
             return JsonResponse({'success': False, 'message': 'Please select a valid term.'}, status=400)

        leave_instance = get_object_or_404(LeaveManagement.objects.filter(school_id=school_id), id=leave_id)
        
        # Check if already approved/rejected
        if leave_instance.status in ["Approved", "Rejected"]:
             return JsonResponse({'success': False, 'message': f'Leave already {leave_instance.status}.'}, status=409)

        # Update database
        leave_instance.status = "Approved"
        leave_instance.term = term
        leave_instance.save()

        # Success: Return JSON for front-end update
        return JsonResponse({'success': True, 'message': 'Leave approved successfully.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON format in request body.'}, status=400)
    except Exception as e:
        # Log this error on the server side
        print(f"Error approving leave {leave_id}: {e}")
        return JsonResponse({'success': False, 'message': 'Internal Server Error during processing.'}, status=500)


@require_POST
def reject_leave_request_ajax(request, leave_id):
    """Handles AJAX request to reject a leave application."""
    school_id = request.session.get('school_id')
    if not school_id:
        return JsonResponse({'success': False, 'message': 'No school selected in session.'}, status=403)
        
    try:
        # Load JSON payload sent by Fetch API
        data = json.loads(request.body)
        term = data.get('term_select') # The term from the modal's select box

        if not term:
             return JsonResponse({'success': False, 'message': 'Please select a valid term.'}, status=400)

        leave_instance = get_object_or_404(LeaveManagement.objects.filter(school_id=school_id), id=leave_id)

        # Check if already approved/rejected
        if leave_instance.status in ["Approved", "Rejected"]:
             return JsonResponse({'success': False, 'message': f'Leave already {leave_instance.status}.'}, status=409)

        # Update database
        leave_instance.status = "Rejected"
        leave_instance.term = term
        leave_instance.save()

        # Success: Return JSON for front-end update
        return JsonResponse({'success': True, 'message': 'Leave rejected successfully.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON format in request body.'}, status=400)
    except Exception as e:
        # Log this error on the server side
        print(f"Error rejecting leave {leave_id}: {e}")
        return JsonResponse({'success': False, 'message': 'Internal Server Error during processing.'}, status=500)


@login_required
def approve_leave(request):
    school_id = request.session.get('school_id')
    if not school_id:
        messages.error(request, "No school selected in session.")
        return redirect("leave_home")

    for _ in messages.get_messages(request):
        pass
    

    school_instance = MasterSchool.objects.get(id = school_id)

    if request.method == "POST":
        form = LeaveForm(request.POST)
        if form.is_valid():
            registration_no = form.cleaned_data["registration_no"]
            student = StudentInfo.objects.filter(school_id=school_id, registration_no=registration_no.registration_no).first()
            
            if not student:
                messages.error(request, f"Student with registration no. {registration_no} does not exist.")
            elif LeaveManagement.objects.filter(school_id=school_id, registration_no=registration_no, return_date__isnull=True).exists():
                messages.error(request, f"Student with registration no. {registration_no} is already on leave.")
            else:
                leave = form.save(commit=False)
                leave.registration_no = student
                leave.school = school_instance
                leave.status = "Approved"
                leave.phone = student.phone
                reason = form.cleaned_data["reason"]
                leave.save()
                
                # send_whatsapp_message(str(student.phone),f"Hello parent you child has been give a leave due to: {reason}")
                messages.success(request, f"Leave has been approved successfully. whatsapp message sent to parent. {student.parent_name}")

                return redirect("leave_home")
        else:
            messages.error(request, f"Form error: {form.errors}")
    else:
        form = LeaveForm()

    # Filtering
    query = request.GET.get("search", "").strip()
    term = request.GET.get("term", "").strip()
    grade = request.GET.get("grade", "").strip()
    stream = request.GET.get("stream", "").strip()

    leave_data = LeaveManagement.objects.filter(school_id=school_id, return_date__isnull=True)
    leave_application_data = LeaveManagement.objects.filter(school_id = school_id,status="Pending")
    if term:
        leave_data = leave_data.filter(term__iexact=term)
    if grade:
        reg_nos = StudentInfo.objects.filter(school_id=school_id, grade=grade, stream=stream).values_list("registration_no", flat=True)
        leave_data = leave_data.filter(registration_no__in=reg_nos)
    
    leave_data = leave_data.values("registration_no", "term", "reason", "date_of_leave")
    leave_application_data = leave_application_data.values("id","registration_no_id","other_reason", "date_of_leave","status")

    grades = list(GradeStream.objects.filter(school_id=school_id).values_list("grade", flat=True).distinct().order_by("grade"))
    reg_nos = StudentInfo.objects.filter(school_id=school_id).values_list("registration_no", flat=True)

    return render(request, "students/pages/leave.html", {
        "reg_nos": reg_nos,
        "form": form,
        "leave_data": leave_data,
        "leave_application_data": leave_application_data,
        "query": query,
        "grades": grades,
        "selected_grade": grade,
        "selected_stream": stream,
        "selected_term": term,
        "term_choices": ["Term 1", "Term 2", "Term 3"],
    })


@login_required
def bulk_leave_approval(request):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    
    today = timezone.now().date()
    time_str = timezone.now().strftime('%H:%M')
    year = today.year

    if request.method == 'POST':
        grade = request.POST.get('grade', '').strip()
        amount = int(request.POST.get('amount', 0))
        term = request.POST.get('term', '').strip()

        # Already approved pupils today
        leave_approvals = set(LeaveManagement.objects.filter(school_id=school_id, date_of_leave=today).values_list('registration_no', flat=True))

        pupils = StudentInfo.objects.filter(school_id=school_id, grade=grade)
        grade_obj = get_object_or_404(Grade.objects.filter(school_id=school_id), name=grade)
        expected_fee = grade_obj.expected_fee
        print("Pupils: ",[p.registration_no for p in pupils])

        # Fee mapping 
        fees = Fee.objects.filter(school_id=school_id, registration_no__in=[p.registration_no for p in pupils]).values('registration_no').annotate(total_paid=Sum('amount'))
        fee_map = {f['registration_no']: (f['total_paid'] or 0) for f in fees}
        print("Fee map: ",fee_map)
        # Determine eligible pupils
        eligible_reg_nos = [
            p.registration_no for p in pupils
            if (expected_fee - Decimal(fee_map.get(p.registration_no, 0)) >= amount)
        ]

        # Create leave approvals
        school_instance =  MasterSchool.objects.get(id = school_id)
        
        leave_data = [
            LeaveManagement(
                school=school_instance,
                registration_no=StudentInfo.objects.get(registration_no = reg_no), 
                date_of_leave=today,
                reason='School Fees',
                year=year,
                time=time_str,
                term=term,
                phone=StudentInfo.objects.get(school=school_instance, registration_no=reg_no).phone
            )
            for reg_no in eligible_reg_nos if reg_no not in leave_approvals
        ]

        if leave_data:
            LeaveManagement.objects.bulk_create(leave_data)
            messages.success(request, "Bulk leave approved successfully!")
        else:
            messages.info(request, "No leave approvals were recorded.")

        return redirect('leave_home')

    term_choices = ['Term 1', 'Term 2', 'Term 3']
    grades = Grade.objects.filter(school_id=school_id)
    return render(request, 'students/pages/leave.html', {
        'today': today,
        'term_choices': term_choices,
        'grades': grades,
    })


@login_required
def update_leave(request, reg_no):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    
    leave_instance = get_object_or_404(LeaveManagement.objects.filter(school_id=school_id), registration_no=reg_no)

    if request.method == 'POST':
        form = LeaveForm(request.POST, instance=leave_instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Pupil leave details updated successfully.")
            return redirect('leave_home')
    else:
        form = LeaveForm(instance=leave_instance)

    return render(request, "students/pages/update_leave.html", {'form': form})


@login_required
def leave_statement(request, reg_no):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    
    student = get_object_or_404(StudentInfo.objects.filter(school_id=school_id), registration_no=reg_no)
    statements = LeaveManagement.objects.filter(school_id=school_id, registration_no=reg_no)

    query = request.GET.get('search', '').strip()
    if query:
        statements = statements.filter(term__icontains=query)

    return render(request, 'students/pages/leave_statement.html', {
        'student': student,
        'statements': statements,
    })




@login_required
def academic_home(request):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass

    grade = request.GET.get('grade', '')
    stream = request.GET.get('stream', '')
    term = request.GET.get('term', '') 
    exam_type = request.GET.get('exam_type', '') 


    CATEGORY_CHOICES = ['Languages','Sciences','Humanities','Technical / Applied','Creative Arts & Sports',
    ]
    REQUIRED_LEVELS = ['Lower Primary', 'Upper Primary', 'Junior Secondary']

    # 1. --- Base Filter Construction ---
    student_filter = Q(school_id=school_id)
    if grade:
        student_filter &= Q(grade=grade)
    if stream:
        student_filter &= Q(stream=stream)
        
    valid_student_reg_nos = StudentInfo.objects.filter(student_filter).values_list('registration_no', flat=True)
    
    if not valid_student_reg_nos.exists() and (grade or stream):
         # If no students match the grade/stream filter
         final_student_summary = []
    else:
        filter_args = Q(sub_strand__strand__isnull=False)
        filter_args &= Q(student__registration_no__in=valid_student_reg_nos)

        # 2. --- Step A: Aggregate by Student and Subject (Strand) ---
        # This gives us the average level and score FOR EACH SUBJECT for each student.
        subject_marks_qs = SubStrandMark.objects.filter(filter_args).values(
            'student__registration_no', 
            'sub_strand__strand__name',
        ).annotate(
            avg_level=Avg('level'),
            avg_score=Avg('score'),
            total_marks_count=Count('id')
        )
        
        # 3. --- Step B: Aggregate by Student ONLY (Overall Mean) ---
        # We start a new query using the results of the filtered marks, 
        # grouping only by the student.
        final_student_summary = SubStrandMark.objects.filter(filter_args).values(
            'student__registration_no'
        ).annotate(
            overall_avg_level=Avg('level'),
            overall_avg_score=Avg('score'),
            overall_subject_count=Count('sub_strand__strand__name', distinct=True)
        ).order_by('student__registration_no')
        
    # 4. --- Map Student Info and Calculate Capped Level ---
    
    # Store overall averages and ensure level is capped at 3.0 for display
    student_summary_map = {}
    for summary in final_student_summary:
        reg_no = summary['student__registration_no']
        
        # Apply the 3.0 cap to the average level
        raw_level = summary['overall_avg_level']
        capped_level = min(raw_level, 4.0) if raw_level is not None else None
        
        summary['overall_avg_level_capped'] = capped_level
        student_summary_map[reg_no] = summary

    students = StudentInfo.objects.filter(school_id=school_id, registration_no__in=student_summary_map.keys())
    student_map = {s.registration_no: s for s in students}
    
    # 5. --- Dropdown Data (Unchanged) ---
    grade_choices = GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct()
    stream_choices = GradeStream.objects.filter(school_id=school_id).values_list('stream', flat=True).distinct()
    term_choices = ['Term 1', 'Term 2', 'Term 3']
    exam_type_choices = ['SBA-Project', 'SBA-Practical', 'SBA-Written', 'End-Level Assessment']
    learning_areas = LearningArea.objects.filter(school_id = school_id)
    return render(request, 'students/pages/academics.html', {
        'marks_list': final_student_summary, # Now a list of overall student summaries
        'student_map': student_map,
        'grade_choices': grade_choices,
        'stream_choices': stream_choices,
        'term_choices': term_choices,
        'exam_type_choices': exam_type_choices,
        'selected_grade': grade,
        'selected_stream': stream,
        'selected_term': term,
        'selected_exam_type': exam_type,
        'categories': CATEGORY_CHOICES,
        'grade_levels': REQUIRED_LEVELS,
        'learning_areas': learning_areas
    })

GOOD_THRESHOLD = 2.5 
 
GOOD_THRESHOLD = 2.5 
LEVEL_NAMES = {4: 'Exceeding Expectations', 3: 'Meeting Expectation', 2: 'Approaching Expectation',1: 'Below Expectation'}
 
def dashboard_comparison_view(request,school_id,selected_term,selected_year,grade,stream):
    """
    Generates data for a dashboard comparing performance across all Learning Areas (Subjects), 
    filtered by optional term and year provided in the request query parameters.
    """
    
    # 1. Retrieve Filters from the Request (Query Parameters)
    # Assumes filters are passed via URL query parameters like ?year=2025&term=1
    

    # 2. Fetch all unique Learning Areas (Strands) based on their subject name.
    learning_areas = Strand.objects.filter(school_id = school_id).values('subject').distinct()
    
    
    dashboard_data = []

    for area in learning_areas:
        subject_name = area['subject']
        
        # 3. Identify ALL Strands belonging to this specific subject name.
        subject_strands = Strand.objects.filter(school_id = school_id,subject=subject_name)
        
        # 4. Get all SubStrands linked to these Strands.
        # Assumes SubStrand has a ForeignKey field named 'strand'
        area_substrands = SubStrand.objects.filter(strand__in=subject_strands)
        total_substrands_count = area_substrands.count()
        
        # Handle cases where the subject exists but has no related substrands
        if not area_substrands.exists():
            dashboard_data.append({
                'name': subject_name,
                'avg_level_area': None,
                'avg_score': None,
                'total_students': 0,
                'level_distribution': {},
                'total_substrands': 0
            })
            continue

        # 5. Filter ALL Marks associated with these SubStrands AND apply term/year filters 🎯
        
        # Start with all marks for this learning area
        all_marks_in_area = SubStrandMark.objects.filter(
            sub_strand__in=area_substrands
        )

        # Apply term and year filters if they exist in the request
        if selected_year:
            # Assumes 'year' is a field on SubStrandMark
            all_marks_in_area = all_marks_in_area.filter(year=selected_year)
        
        if selected_term:
            # Assumes 'term' is a field on SubStrandMark
            all_marks_in_area = all_marks_in_area.filter(term=selected_term)

        if grade:
            # Assumes 'year' is a field on SubStrandMark
            all_marks_in_area = all_marks_in_area.filter(sub_strand__strand__grade=grade)
        if stream and grade:
            # Assumes 'year' is a field on SubStrandMark
            all_marks_in_area = all_marks_in_area.filter(sub_strand__strand__stream=stream,sub_strand__strand__grade=grade)


        # --- Handle cases where the area has marks but none match the filter ---
        if not all_marks_in_area.exists():
            dashboard_data.append({
                'name': subject_name,
                'avg_level_area': None,
                'avg_score': None,
                'total_students': 0,
                'level_distribution': {},
                'total_substrands': total_substrands_count
            })
            continue
    
        
        # 6. Calculate Aggregations for the entire Learning Area
        area_aggregate = all_marks_in_area.aggregate(
            avg_level=Avg('level'),
            avg_score=Avg('score'),
            total_students=Count('student', distinct=True) 
        )
        
        
        # 7. Distribution of Marks by Level
        level_distribution_raw = all_marks_in_area.values('level').annotate(
            count=Count('level')
        )

        # Structure the level distribution data
        distribution_map = {
            LEVEL_NAMES.get(item['level']): item['count'] 
            for item in level_distribution_raw if item['level'] in LEVEL_NAMES
        }
        
        final_distribution = {}
        for level, label in LEVEL_NAMES.items():
            final_distribution[label] = distribution_map.get(label, 0)
            
        # 8. Consolidate data
        dashboard_data.append({
            'name': subject_name,
            'avg_level_area': area_aggregate['avg_level'],
            'avg_score': round(area_aggregate['avg_score'],2), 
            'total_students': area_aggregate['total_students'],
            'level_distribution': final_distribution,
            'total_substrands': total_substrands_count,
            'grade': grade,
            'stream': stream
        })
        
    context = { 
        'dashboard_data': dashboard_data,
        'level_labels': LEVEL_NAMES.values(),
        'max_score_level': 3,
        'selected_year': selected_year, # Include selected filters in context
        'selected_term': selected_term, 
    }
    
    # Example return (modify as needed for your application, e.g., render or JsonResponse)
    return dashboard_data
    
    


from django.db.models import Sum, Avg, Q


@login_required
def academic_dashboard(request):
    school_id = request.session.get('school_id')
    #  # Removed as it's not used in core logic
    for _ in messages.get_messages(request):
        pass
    
    # 1. Retrieve Filters from the Request (Query Parameters)
    year = request.GET.get('year', '')
    term = request.GET.get('term', '')
    assessment_type = request.GET.get('assessment_type', '') # RENAMED
    grade = request.GET.get('grade', '')  # NEW
    stream = request.GET.get('stream', '') # NEW

    # Use SubStrandMark for all marks-related lookups
    # MODIFIED: Filter via student foreign key since SubStrandMark lacks school_id
    SubStrandMark_qs_all = SubStrandMark.objects.filter(student__school_id=school_id)
    
    latest_year = SubStrandMark_qs_all.values_list("year", flat=True).distinct().order_by("-year").first()
    # Logic for update_marks removed as it was specific to the old 'Marks' model
    # if latest_year:
    #     update_marks(school_id, year=latest_year)  

    # 2. Fetch all unique filter options from SubStrandMark and GradeStream
    years = SubStrandMark_qs_all.values_list('year', flat=True).distinct().order_by('-year')
    terms = SubStrandMark_qs_all.values_list('term', flat=True).distinct()
    assessment_types = SubStrandMark_qs_all.values_list('assessment_type', flat=True).distinct() # RENAMED

    # Fetch all distinct grades/streams from GradeStream (for filter dropdowns)
    grades = list(GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct())
    # Group streams if a stream appears twice (implicitly done by distinct())
    streams = list(GradeStream.objects.filter(school_id=school_id).values_list('stream', flat=True).distinct())

    # 3. Create the base filtered queryset for SubStrandMark
    marks_qs = SubStrandMark_qs_all
    if year:
        marks_qs = marks_qs.filter(year=year)
    if term:
        marks_qs = marks_qs.filter(term=term)
    if assessment_type: # RENAMED
        marks_qs = marks_qs.filter(assessment_type=assessment_type)
    
    # NEW FILTERS: Filter marks by selected Grade and Stream
    # We filter SubStrandMark through the student foreign key linkage
    if grade or stream:
        student_filter = {'school_id': school_id}
        if grade:
            student_filter['grade'] = grade
        if stream:
            student_filter['stream'] = stream
            
        # Get registration numbers of students matching grade/stream criteria
        filtered_reg_nos = StudentInfo.objects.filter(**student_filter).values_list('registration_no', flat=True)
        # Filter marks_qs by these students
        # Assumes SubStrandMark has a ForeignKey to StudentInfo named 'student'
        marks_qs = marks_qs.filter(student__registration_no__in=filtered_reg_nos)

    
    # 4. Build top students per grade (using SubStrandMark Avg Score)
    top_students_per_grade = {}
    
    # Determine the grades to loop through (use selected grade if provided, otherwise all grades)
    grades_to_process = [grade] if grade else grades

    for g in grades_to_process:
        # Determine students in the current grade (and selected stream, if provided)
        student_info_filter = {'school_id': school_id, 'grade': g}
        if stream:
            student_info_filter['stream'] = stream
            
        reg_nos = StudentInfo.objects.filter(**student_info_filter).values_list('registration_no', flat=True)
        
        # Aggregate SubStrandMark scores (using average score)
        grade_marks = (
            marks_qs.filter(student__registration_no__in=reg_nos)
            .values('student__registration_no') # Group by student registration number
            .annotate(avg_score=Avg('score')) # Calculate average score across all their filtered substrand marks
            .order_by('-avg_score')[:3]
        )

        students_list = []
        for m in grade_marks:
            # Note: We use the registration number from the aggregation to fetch student info
            student = StudentInfo.objects.filter(school_id=school_id, registration_no=m['student__registration_no']).first()
            if student:
                full_name = f"{student.first_name} {student.second_name} {student.surname}".strip()
                students_list.append({
                    'name': full_name,
                    'stream': student.stream,
                    'avg_score': round(m['avg_score'], 2), # Use avg_score and round it
                })
        top_students_per_grade[g] = students_list

    # 5. Charts (Pie Chart: Student Count per Grade, Line Chart: Average Score per Grade)
    
    pie_labels = grades
    pie_data = []
    line_labels = grades
    line_data = []

    for g in grades:
        # Determine students in the current grade (and selected stream if applicable)
        student_info_filter = {'school_id': school_id, 'grade': g}
        if stream:
            student_info_filter['stream'] = stream
            
        reg_nos = StudentInfo.objects.filter(**student_info_filter).values_list('registration_no', flat=True)
        
        # PIE CHART DATA: Student Count (filtered by stream)
        pie_data.append(len(reg_nos)) 

        # LINE CHART DATA: Average SubStrandMark Score (filtered by all time/assessment filters)
        avg_score = marks_qs.filter(student__registration_no__in=reg_nos).aggregate(avg=Avg('score'))['avg'] or 0
        line_data.append(round(avg_score, 2))
    
    
    # 6. Call the comparison view (assuming it accepts the request object and applies filters)
    # The comparison view will now receive the year, term, assessment_type, grade, and stream filters.
    learning_areas = dashboard_comparison_view(request,school_id,term,year,grade,stream)

    
    # 7. Return final context
    return render(request, 'students/pages/academic_dashboard.html', {
        'learning_areas': learning_areas,
        'top_students_per_grade': top_students_per_grade,
        'pie_labels': json.dumps(pie_labels),
        'pie_data': json.dumps(pie_data),
        'line_labels': json.dumps(line_labels),
        'line_data': json.dumps(line_data),
        'years': years,
        'grades': grades,
        'streams': streams, # Passed for filter dropdown
        'terms': terms,
        'assessment_types': assessment_types, # RENAMED
        'selected_year': year,
        'selected_term': term,
        'selected_assessment_type': assessment_type, # RENAMED
        'selected_grade': grade, # NEW
        'selected_stream': stream, # NEW
    })
CBC_LEVEL_MAP = {
    'EE': {'min_avg': 3.5, 'label': 'Exceeding Expectations', 'remark': 'Excellent Mastery'},
    'ME': {'min_avg': 2.5, 'label': 'Meeting Expectations', 'remark': 'Good Progress'},
    'AE': {'min_avg': 1.5, 'label': 'Approaching Expectations', 'remark': 'Needs Improvement'},
    'BE': {'min_avg': 0.0, 'label': 'Below Expectations', 'remark': 'Critical Intervention'},
}

def get_cbc_level_and_remark(avg_level):
    """Determines the CBC level and remark based on the calculated average level."""
    if avg_level is None or avg_level <= 0:
        return {'level': '-', 'remark': 'No Data'}
    
    # Cap the average at 3.0 before mapping
    capped_avg = min(avg_level, 4.0) 
        
    for code, data in sorted(CBC_LEVEL_MAP.items(), key=lambda item: item[1]['min_avg'], reverse=True):
        if capped_avg >= data['min_avg']:
            return {'level': code, 'remark': data['remark']}
            
    return {'level': 'BE', 'remark': CBC_LEVEL_MAP['BE']['remark']}


def other_exams(request, reg_no):
    school_id = request.session.get('school_id')
    messages.get_messages(request).used = True

    # 1. Get the student safely
    student = get_object_or_404(
        StudentInfo.objects.filter(school_id=school_id),
        registration_no=reg_no
    )
    
    # Context filters (assuming these might be passed via GET from the dashboard)
    term = request.GET.get('term', '') 
    exam_type = request.GET.get('exam_type', '') 
    
    # 2. Base Query and Filtering
    
    mark_filter_args = Q(
        student__registration_no=reg_no,
        sub_strand__strand__isnull=False
    )
    
    # Note: If term/exam_type are fields on SubStrandMark, you can re-enable these filters:
    if term:
        mark_filter_args &= Q(term=term)
    # if exam_type:
    #     mark_filter_args &= Q(type_of_exam=exam_type)

    # 3. Aggregate Average Level and Score per Subject (Strand)
    
    # This query gives the average score and level for EACH SUBJECT the student took.
    subject_averages = SubStrandMark.objects.filter(mark_filter_args).values(
        'sub_strand__strand__name','sub_strand__strand__subject',  # Group by the subject/strand name
    ).annotate(
        avg_level=Avg('level'),
        avg_score=Avg('score'),
        total_sub_strand_marks=Count('id')
    ).order_by('sub_strand__strand__name')
    
    subject_breakdown_data = []
    
    # 4. Process Aggregated Data for Display
    for data in subject_averages:
        avg_level = data['avg_level']
        
        # Determine CBC Level and Remark
        report_data = get_cbc_level_and_remark(avg_level)
        
        subject_breakdown_data.append({
            'strand_name': data['sub_strand__strand__name'],
            'subject_name': data['sub_strand__strand__subject'],

            'avg_score': data['avg_score'],
            'avg_level': avg_level,
            'total_assessments': data['total_sub_strand_marks'],
            'cbc_level': report_data['level'],
            'cbc_remark': report_data['remark'],
        })

    # 5. Get list of ALL subjects taught in the student's grade (for comparison/completeness)
    all_subjects_in_grade = Strand.objects.filter(grade=student.grade).values_list('name', flat=True).distinct()
    
    # 6. Render the detailed report page
    context = {
        'student': student,
        'subject_breakdown_data': subject_breakdown_data,
        'all_subjects_in_grade': all_subjects_in_grade,
        'current_term': term,
    }
    
    return render(request, 'students/pages/other_exams.html', context)
        

@login_required
def pupil_attendance_list(request):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass

    # Get filter parameters
    grade = request.GET.get('grade', '').strip()
    stream = request.GET.get('stream', '').strip()
    term = request.GET.get('term', '').strip()
    registration_no = request.GET.get('registration_no', '').strip()

    

    # Base queryset
    attendance_qs = StudentAttendance.objects.filter(school_id=school_id)

    # Apply filters
    if grade:
        attendance_qs = attendance_qs.filter(grade=grade)
    if stream:
        attendance_qs = attendance_qs.filter(stream=stream)
    if term:
        attendance_qs = attendance_qs.filter(term=term)
    if registration_no:
        attendance_qs = attendance_qs.filter(registration_no=registration_no)

    # Fetch student info for display
    reg_nos = attendance_qs.values_list('registration_no', flat=True)
    students = StudentInfo.objects.filter(school_id=school_id, registration_no__in=reg_nos)
    student_map = {s.registration_no: s for s in students}

    # Choices for filters
    grade_choices = list(GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct())
    term_choices = ['Term 1', 'Term 2', 'Term 3']

    context = {
        'attendance_list': attendance_qs,
        'student_map': student_map,
        'grade_choices': grade_choices,
        'term_choices': term_choices,
        'selected_grade': grade,
        'selected_stream': stream,
        'selected_term': term,
        'selected_registration_no': registration_no,
    }
    return render(request, 'students/pages/pupil_attendance.html', context)
