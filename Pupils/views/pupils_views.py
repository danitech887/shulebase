# --- Imports ---
from datetime import datetime
from collections import defaultdict
from decimal import Decimal
import io
import os
import zipfile

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

from ..forms import RegisterForm, FeeForm, LeaveForm
from ..models import StudentInfo, Fee, LeaveManagement, Marks, PupilAttendance, GradeStream
from ..utils.per_school_db_utils import get_school_db_alias_from_session


# --- Utility function for next registration number ---
def get_next_registration_number(school_id,existing_regnos):

    for i in range(1, 20000):  # allow up to 19999 pupils
        reg_no = f"SCH{school_id}REG{i:02d}"
        if reg_no not in existing_regnos:
            return reg_no
    return None


# --- Streams API ---
@login_required
@require_http_methods(["GET"])
def get_streams(request):
    alias = get_school_db_alias_from_session(request)
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


# --- Pupil List ---
@login_required
def pupil_list(request):
    alias = get_school_db_alias_from_session(request)
    school_id = request.session.get('school_id')
    query = request.GET.get('search', '').strip()

    pupils = StudentInfo.objects.filter(school_id=school_id)
    if query:
        pupils = pupils.filter(registration_no__icontains=query)

    return render(request, 'pupil/pupil_list.html', {'pupils': pupils, 'query': query})

from ..models import MasterSchool
# --- GradeStream Configuration ---
@login_required
def gradestream_config(request):
    alias = get_school_db_alias_from_session(request)
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


# --- Manage Pupil Details ---
@login_required
def manage_details(request):
    alias = get_school_db_alias_from_session(request)
    school_id = request.session.get('school_id')
    print('School id',school_id)
    school_instance = MasterSchool.objects.get(id = school_id)

    # Registration handling
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            registration_no = form.cleaned_data["registration_no"]
            if StudentInfo.objects.filter(school_id = school_id, registration_no=registration_no).exists():
                messages.error(f"Student with registration {registration_no} already exists")
            else:
                name = form.cleaned_data["first_name"]
                try:
                    obj = form.save(commit=False)
                    obj.school = school_instance
                    obj.save()
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

    # Suggested registration number
    existing_regnos = set(pupils.values_list('registration_no', flat=True))
    suggested_regno = get_next_registration_number(school_id,existing_regnos)

    return render(request, "pupil/register.html", {
        "form": form,
        "query": query,
        "pupils": pupils,
        "grades": grades,
        "selected_grade": grade,
        "selected_stream": stream,
        "suggested_regno": suggested_regno,
    })


# --- Update Pupil ---
@login_required
def update_pupil(request, reg_no):
    alias = get_school_db_alias_from_session(request)
    school_id = request.session.get('school_id')

    pupil = get_object_or_404(StudentInfo.objects.filter(school_id=school_id), registration_no=reg_no)

    if request.method == 'POST':
        form = RegisterForm(request.POST, instance=pupil)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            messages.success(request, 'Pupils details updated successfully')
            return redirect('manage_details')
    else:
        form = RegisterForm(instance=pupil)

    grades = GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct().order_by('grade')

    return render(request, "pupil/update_pupil.html", {'form': form, 'pupil': pupil, 'grades': grades})


@login_required
def promote_students(request):
    school_id = request.session.get('school_id')
    alias = get_school_db_alias_from_session(request)

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

        with transaction.atomic(using=alias):
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

    return render(request, 'pupil/register.html', {
        'students': students,
        'grade': grade,
        'stream': selected_stream,
        'stream_choices': stream_choices
    })


# --- Delete Pupil ---
@login_required
def delete_pupil(request, reg_no):
    alias = get_school_db_alias_from_session(request)
    school_id = request.session.get('school_id')

    pupil = get_object_or_404(StudentInfo.objects.filter(school_id=school_id), registration_no=reg_no)

    if request.method == 'POST':
        pupil.delete()
        messages.success(request, "Pupil deleted successfully")
        return redirect('manage_details')

    return render(request, 'pupil/delete_pupil.html', {'pupil': pupil})

from decimal import Decimal
from collections import defaultdict
import json
import calendar

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse

from ..models import StudentInfo, Fee, Grade, GradeStream
from ..forms import FeeForm, GradeFeeForm
from ..utils.per_school_db_utils import get_school_db_alias_from_session


# ----------------- Fee Summary -----------------
def fee_summary(school_id):
    

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
        .filter(school_id=school_id)
        .values("registration_no")
        .annotate(total_paid=Sum("amount"))
    )
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
    alias = get_school_db_alias_from_session(request)
    for _ in messages.get_messages(request):
        pass

    form_type = request.POST.get("form_type", "").strip()
    form = FeeForm(request.POST or None)

    # Handle Payment Submission
    if request.method == "POST" and form_type == "payment" and form.is_valid():
        registration_no = form.cleaned_data["registration_no"]

        if not StudentInfo.objects.filter(school_id=school_id, registration_no=registration_no.registration_no).exists():
            messages.error(request, f"Pupil with registration number {registration_no} does not exist.")
            return redirect('fee_payment')

        school_instance = MasterSchool.objects.get(id = school_id)
        obj = form.save(commit=False)
        obj.registration_no = registration_no
        obj.school = school_instance
        obj.save()
        messages.success(request, "Payment recorded successfully!")
        return redirect("fee_payment")

    # ----------------- Filtering -----------------
    query = request.GET.get("search", "").strip()
    grade = request.GET.get("grade", "").strip()
    stream = request.GET.get("stream", "").strip()
    term = request.GET.get("term", "").strip()

    fees = Fee.objects.filter(school_id=school_id)

    if query:
        fees = fees.filter(registration_no__icontains=query)
    if grade:
        reg_nos = StudentInfo.objects.filter(school_id=school_id, grade__iexact=grade).values_list("registration_no", flat=True)
        fees = fees.filter(registration_no__in=reg_nos)
    if stream:
        reg_nos = StudentInfo.objects.filter(school_id=school_id, stream__iexact=stream).values_list("registration_no", flat=True)
        fees = fees.filter(registration_no__in=reg_nos)
    if term:
        fees = fees.filter(term__iexact=term)

    fees = fees.values("registration_no", "term").annotate(total_paid=Sum("amount")).order_by("registration_no", "term")

    # Ensure Grade entries exist
    grade_names = GradeStream.objects.filter(school_id=school_id).values_list("grade", flat=True).distinct()
    school_instance = MasterSchool.objects.get(id = school_id)
    for name in grade_names:
        if name:
            Grade.objects.get_or_create(school_id=school_id, name=name)

    grades = list(Grade.objects.filter(school_id=school_id).order_by("name"))
    pupils = StudentInfo.objects.filter(school_id=school_id)
    reg_nos = pupils.values_list("registration_no", flat=True)
    print(reg_nos)

    # Handle Grade Fee Submission
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

    # AJAX Fetch
    if request.headers.get("x-requested-with") == "XMLHttpRequest" and request.method == "GET":
        return JsonResponse({"fees": list(fees)})

    return render(request, "pupil/fee.html", {
        "reg_nos": reg_nos,
        "form": form,
        "fees": fees,
        "forms": grade_forms,
        "grades": grades,
        "query": query,
        "selected_grade": grade,
        "selected_stream": stream,
        "selected_term": term,
    })


# ----------------- Individual Fee List -----------------
@login_required
def individual_fee_list(request, reg_no):
    school_id = request.session.get('school_id')
    alias = get_school_db_alias_from_session(request)
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

    return render(request, 'pupil/individual_fee_list.html', {
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

    years = Fee.objects.filter(school_id=school_id).values_list("year", flat=True).distinct().order_by("-year")
    fees = Fee.objects.filter(school_id=school_id)

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

    context = {
        "term": term,
        "year": year,
        "years": years,
        "fee_balances": fee_summary(school_id),

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
    return render(request, "pupil/fee_dashboard.html", context)


from django.db import connection
from django.core.serializers.json import DjangoJSONEncoder
import json
from collections import defaultdict



from collections import defaultdict
import calendar
import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Case, When, IntegerField, F
from django.shortcuts import render

from ..models import StudentInfo, PupilAttendance
from ..utils.per_school_db_utils import get_school_db_alias_from_session


@login_required
def attendance_dashboard(request):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    alias = get_school_db_alias_from_session(request)

    term = request.GET.get("term", "").strip()
    year = request.GET.get("year", "").strip()

    # Available years for filter
    years_qs = PupilAttendance.objects.filter(school_id=school_id).dates("date_of_attendance", "year")
    years = [str(y.year) for y in years_qs]

    # Base queryset
    qs = PupilAttendance.objects.filter(school_id=school_id)
    if term:
        qs = qs.filter(term=term)
    if year:
        qs = qs.filter(date_of_attendance__year=year)

    # Chart 1: Attendance by Grade-Stream
    students = {
        s.registration_no: (s.grade, s.stream)
        for s in StudentInfo.objects.filter(school_id=school_id)
    }

    chart_map = defaultdict(lambda: {"Present": 0, "Absent": 0})
    for a in qs:
        grade, stream = students.get(a.registration_no, ("", ""))
        if not grade:
            continue
        key = f"{grade} - {stream}"
        chart_map[key][a.status] += 1

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
    return render(request, "pupil/attendance_dashboard.html", context)


from collections import defaultdict
from datetime import datetime
from django.utils import timezone
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from ..models import StudentInfo, LeaveManagement, Grade, Fee, GradeStream
from ..forms import LeaveForm
from ..utils.per_school_db_utils import get_school_db_alias_from_session


@login_required
def approve_leave(request):
    school_id = request.session.get('school_id')
    if not school_id:
        messages.error(request, "No school selected in session.")
        return redirect("leave_home")

    for _ in messages.get_messages(request):
        pass
    alias = get_school_db_alias_from_session(request)

    school_instance = MasterSchool.objects.get(id = school_id)

    if request.method == "POST":
        form = LeaveForm(request.POST)
        if form.is_valid():
            registration_no = form.cleaned_data["registration_no"]
            student = StudentInfo.objects.filter(school_id=school_id, registration_no=registration_no.registration_no).first()
            
            if not student:
                messages.error(request, f"Pupil with registration no. {registration_no} does not exist.")
            elif LeaveManagement.objects.filter(school_id=school_id, registration_no=registration_no, return_date__isnull=True).exists():
                messages.error(request, f"Pupil with registration no. {registration_no} is already on leave.")
            else:
                leave = form.save(commit=False)
                leave.registration_no = student
                leave.school = school_instance
                leave.phone = student.phone
                leave.save()
                messages.success(request, "Leave has been approved successfully.")
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
    if term:
        leave_data = leave_data.filter(term__iexact=term)
    if grade:
        reg_nos = StudentInfo.objects.filter(school_id=school_id, grade=grade, stream=stream).values_list("registration_no", flat=True)
        leave_data = leave_data.filter(registration_no__in=reg_nos)

    leave_data = leave_data.values("registration_no", "term", "reason", "date_of_leave")

    grades = list(GradeStream.objects.filter(school_id=school_id).values_list("grade", flat=True).distinct().order_by("grade"))
    reg_nos = StudentInfo.objects.filter(school_id=school_id).values_list("registration_no", flat=True)

    return render(request, "pupil/leave.html", {
        "reg_nos": reg_nos,
        "form": form,
        "leave_data": leave_data,
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
    alias = get_school_db_alias_from_session(request)
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
    return render(request, 'pupil/leave.html', {
        'today': today,
        'term_choices': term_choices,
        'grades': grades,
    })


@login_required
def update_leave(request, reg_no):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    alias = get_school_db_alias_from_session(request)
    leave_instance = get_object_or_404(LeaveManagement.objects.filter(school_id=school_id), registration_no=reg_no)

    if request.method == 'POST':
        form = LeaveForm(request.POST, instance=leave_instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Pupil leave details updated successfully.")
            return redirect('leave_home')
    else:
        form = LeaveForm(instance=leave_instance)

    return render(request, "pupil/update_leave.html", {'form': form})


@login_required
def leave_statement(request, reg_no):
    school_id = request.session.get('school_id')
    for _ in messages.get_messages(request):
        pass
    alias = get_school_db_alias_from_session(request)
    student = get_object_or_404(StudentInfo.objects.filter(school_id=school_id), registration_no=reg_no)
    statements = LeaveManagement.objects.filter(school_id=school_id, registration_no=reg_no)

    query = request.GET.get('search', '').strip()
    if query:
        statements = statements.filter(term__icontains=query)

    return render(request, 'pupil/leave_statement.html', {
        'student': student,
        'statements': statements,
    })



from collections import defaultdict
import json
from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg
from ..models import Marks, StudentInfo, GradeStream, Fee
from ..utils.per_school_db_utils import get_school_db_alias_from_session
from .services import update_marks



from django.db.models import Sum, Avg
from django.contrib import messages
from django.shortcuts import render
import json
@login_required
def academic_home(request):
    school_id = request.session.get('school_id')
    alias = get_school_db_alias_from_session(request)
    for _ in messages.get_messages(request):
        pass

    grade = request.GET.get('grade', '')
    stream = request.GET.get('stream', '')
    term = request.GET.get('term', '')
    exam_type = request.GET.get('exam_type', '')

    # Base queryset for marks
    marks_qs = Marks.objects.filter(school_id=school_id)

    # Map registration numbers to students
    reg_nos = marks_qs.values_list('registration_no', flat=True)
    students = StudentInfo.objects.filter(school_id=school_id, registration_no__in=reg_nos)
    student_map = {s.registration_no: s for s in students}

    # Filter by grade and stream via student model
    if grade:
        reg_nos = students.filter(grade=grade).values_list('registration_no', flat=True)
        marks_qs = marks_qs.filter(registration_no__in=reg_nos)
    if stream:
        reg_nos = students.filter(stream=stream).values_list('registration_no', flat=True)
        marks_qs = marks_qs.filter(registration_no__in=reg_nos)

    # Filter by term and exam type
    if term:
        marks_qs = marks_qs.filter(term=term)
    if exam_type:
        marks_qs = marks_qs.filter(type_of_exam=exam_type)

    # Dropdown data
    grade_choices = GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct()
    stream_choices = GradeStream.objects.filter(school_id=school_id).values_list('stream', flat=True).distinct()
    term_choices = ['Term 1', 'Term 2', 'Term 3']
    exam_type_choices = Marks.objects.filter(school_id=school_id).values_list('type_of_exam', flat=True).distinct()

    return render(request, 'pupil/academics.html', {
        'marks_list': marks_qs,
        'student_map': student_map,
        'grade_choices': grade_choices,
        'stream_choices': stream_choices,
        'term_choices': term_choices,
        'exam_type_choices': exam_type_choices,
        'selected_grade': grade,
        'selected_stream': stream,
        'selected_term': term,
        'selected_exam_type': exam_type,
    })

@login_required
@login_required
def academic_dashboard(request):
    school_id = request.session.get('school_id')
    alias = get_school_db_alias_from_session(request)
    for _ in messages.get_messages(request):
        pass

    latest_year = Marks.objects.filter(school_id=school_id).values_list("year", flat=True).distinct().order_by("-year").first()
    if latest_year:
        update_marks(school_id, year=latest_year)

    year = request.GET.get('year', '')
    term = request.GET.get('term', '')
    exam_type = request.GET.get('exam_type', '')

    years = Marks.objects.filter(school_id=school_id).values_list('year', flat=True).distinct().order_by('-year')
    terms = Marks.objects.filter(school_id=school_id).values_list('term', flat=True).distinct()
    exam_types = Marks.objects.filter(school_id=school_id).values_list('type_of_exam', flat=True).distinct()

    marks_qs = Marks.objects.filter(school_id=school_id)
    if year:
        marks_qs = marks_qs.filter(year=year)
    if term:
        marks_qs = marks_qs.filter(term=term)
    if exam_type:
        marks_qs = marks_qs.filter(type_of_exam=exam_type)

    # Fetch all distinct grades from GradeStream
    grades = list(GradeStream.objects.filter(school_id=school_id).values_list('grade', flat=True).distinct())

    # Build top students per grade using StudentInfo linkage
    top_students_per_grade = {}
    for grade in grades:
        reg_nos = StudentInfo.objects.filter(school_id=school_id, grade=grade).values_list('registration_no', flat=True)
        grade_marks = (
            marks_qs.filter(registration_no__in=reg_nos)
            .values('registration_no')
            .annotate(total_marks=Sum('total_marks'))
            .order_by('-total_marks')[:3]
        )

        students_list = []
        for m in grade_marks:
            student = StudentInfo.objects.filter(school_id=school_id, registration_no=m['registration_no']).first()
            if student:
                full_name = f"{student.first_name} {student.second_name} {student.surname}".strip()
                students_list.append({
                    'name': full_name,
                    'stream': student.stream,
                    'total_marks': m['total_marks'],
                })
        top_students_per_grade[grade] = students_list

    # Charts
    pie_labels = grades
    pie_data = [StudentInfo.objects.filter(school_id=school_id, grade=grade).count() for grade in grades]

    line_labels = grades
    line_data = []
    for grade in grades:
        reg_nos = StudentInfo.objects.filter(school_id=school_id, grade=grade).values_list('registration_no', flat=True)
        avg_marks = marks_qs.filter(registration_no__in=reg_nos).aggregate(avg=Avg('total_marks'))['avg'] or 0
        line_data.append(round(avg_marks, 2))

    return render(request, 'pupil/academic_dashboard.html', {
        'top_students_per_grade': top_students_per_grade,
        'pie_labels': json.dumps(pie_labels),
        'pie_data': json.dumps(pie_data),
        'line_labels': json.dumps(line_labels),
        'line_data': json.dumps(line_data),
        'years': years,
        'terms': terms,
        'exam_types': exam_types,
        'selected_year': year,
        'selected_term': term,
        'selected_exam_type': exam_type,
    })

@login_required
def other_exams(request, reg_no):
    school_id = request.session.get('school_id')
    alias = get_school_db_alias_from_session(request)
    for _ in messages.get_messages(request):
        pass

    # Get the student safely
    student = get_object_or_404(
        StudentInfo.objects.filter(school_id=school_id),
        registration_no=reg_no
    )

    type_of_exam = request.GET.get('search', '')

    # Define subjects per CBC grade level
    lower_grades = ['PP1','PP2','Grade 1', 'Grade 2', 'Grade 3']
    upper_grades = ['Grade 4', 'Grade 5', 'Grade 6']
    junior_grades = ['Grade 7', 'Grade 8', 'Grade 9']

    if student.grade in lower_grades:
        subjects = [
            ('mathematics', 'Mathematics'),
            ('english', 'English'),
            ('kiswahili', 'Kiswahili'),
            ('environmental_activities', 'Environmental Activities'),
            ('integrated_creative', 'Integrated Creative'),
            ('social_studies','Social Studies'),
            ('Cre','cre')
        ]
    elif student.grade in upper_grades:
        subjects = [
            ('mathematics', 'Mathematics'),
            ('english', 'English'),
            ('kiswahili', 'Kiswahili'),
            ('science_technology', 'Science & Technology'),
            ('sst_cre', 'SST/CRE'),
            ('agri_nutrition', 'Agriculture & Nutrition'),
            ('creative_arts', 'Creative Arts'),
        ]
    elif student.grade in junior_grades:
        subjects = [
            ('mathematics', 'Mathematics'),
            ('english', 'English'),
            ('kiswahili', 'Kiswahili'),
            ('sst_cre', 'SST/CRE'),
            ('agri_nutrition', 'Agriculture & Nutrition'),
            ('creative_arts', 'Creative Arts'),
            ('pretech_bs_computer', 'Pretech/Business/Computer'),
            ('integrated_science', 'Integrated Science'),
        ]
    else:
        subjects = []

    # ✅ FIX: Use registration_no__registration_no to match FK
    marks_qs = Marks.objects.filter(
        school_id=school_id,
        registration_no__registration_no=reg_no
    )

    if type_of_exam:
        marks_qs = marks_qs.filter(type_of_exam__icontains=type_of_exam)

    # Build lookup by exam type
    exam_lookup = {m.type_of_exam: m for m in marks_qs}

    other_exams_data = []
    for field, subject_name in subjects:
        opener = getattr(exam_lookup.get('Opener'), field, 0) or 0
        mid_term = getattr(exam_lookup.get('Mid Term'), field, 0) or 0
        end_term = getattr(exam_lookup.get('End Term'), field, 0) or 0
        avg = round((opener + mid_term + end_term) / 3, 1)
        other_exams_data.append({
            'subject': subject_name,
            'opener': opener,
            'mid_term': mid_term,
            'end_term': end_term,
            'average': avg,
        })

    return render(request, 'pupil/other_exams.html', {
        'student': student,
        'other_exams_data': other_exams_data,
    })


        




from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import PupilAttendance, StudentInfo, GradeStream
from ..utils.per_school_db_utils import get_school_db_alias_from_session

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

    alias = get_school_db_alias_from_session(request)

    # Base queryset
    attendance_qs = PupilAttendance.objects.filter(school_id=school_id)

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
    return render(request, 'pupil/pupil_attendance.html', context)



