from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from django.http import JsonResponse, HttpResponse
from django.contrib import messages

from ..models import*
from django.db.models import Sum
from django.utils.timezone import now
from datetime import datetime
from reportlab.pdfgen import canvas

import zipfile, io
import io
import zipfile
from collections import defaultdict

from decimal import Decimal

from Pupils.utils.per_school_db_utils import get_school_db_alias_from_session

import pymysql
import os

import os
import pymysql









from fpdf import FPDF
def pdf_header(request,pdf,x):
    logo = request.session['logo_path']
    name = request.session['school_name']
    address = request.session['address']
    contact = request.session['contact']
    email = request.session['email']
    motto = request.session['motto']
    if logo:
        try:
            pdf.image(str(logo), x=10, y=10, w=25)
            pdf.ln(20)  
        except Exception as e:
            print(e)
            pdf.image(str("static/images/logo.png"),x=10,y=10,w=25)
    
        
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 5, name, ln=1, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Address: {address}", ln=1, align="C")
    pdf.cell(0, 5, f"Tel: {contact} | Email: {email}", ln=1, align="C")
    pdf.cell(0,5,f"Motto: {motto}",ln=1,align="C")
    pdf.ln(5)  # space after header  
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    

def pdf_footer(pdf,vision):
    pdf.set_y(-10)  # 15 mm from bottom
    pdf.set_font("Arial", "I", 8)
    # pdf.cell(0,10,f"Vision: {vision}",ln=1,align="C")

class PdfWaterMark(FPDF):
        def add_watermark(self,text):
            self.set_font('Arial', size=100, style='B')
            self.set_text_color(200,200,200)
            self.set_xy(0,0)
            width = self.get_string_width(text)
            x = (self.w - width) / 2
            # x = self.w / 4
            y = self.h / 2

            self.text(x, y, text)
            self.rotate(45, x=x , y=y)
            self.rotate(0)
        def add_footer(self):
            select = "select email from school_details"
            email = self.manager.search_detail(select)
            self.set_y(-15)
            self.set_font('Arial','I',8)
            self.set_text_color(128,128,128)
            self.cell(0,10,email['email'],align='C')



@login_required
@login_required
def generate_result_papers(request):
    school_id = request.session.get("school_id")
    storage = messages.get_messages(request)
    storage.used = True

    grade = request.GET.get('grade', '')
    term = request.GET.get('term', '')
    exam_type = request.GET.get('exam_type', '')
    alias = get_school_db_alias_from_session(request)

    # --- CBC grade configuration ---
    grade_configs = {
        "lower": {
            "grades": ["Grade 1", "Grade 2", "Grade 3"],
            "columns": [
                ('Reg No', 15),
                ('Name', 40),
                ('Grade', 15),
                ('Stream', 15),
                ('Maths', 15),
                ('Eng', 15),
                ('Kisw', 15),
                ('Env Act', 15),
                ('Inte/Cre', 15),
                ('Total', 15),
                ('Mean', 15),
                ('Position', 15),
                ('O/Position', 15),
            ],
            "fields": ["mathematics", "english", "kiswahili",
                       "environmental_activities", "integrated_creative"]
        },
        "upper": {
            "grades": ["Grade 4", "Grade 5", "Grade 6"],
            "columns": [
                ('Reg No', 15),
                ('Name', 40),
                ('Grade', 15),
                ('Stream', 15),
                ('Maths', 15),
                ('Eng', 15),
                ('Kisw', 15),
                ('Sci&Tech', 15),
                ('SST/CRE', 15),
                ('Agri&Nutr', 15),
                ('CreArts', 15),
                ('Total', 15),
                ('Mean', 15),
                ('Position', 15),
                ('O/Position', 15),
            ],
            "fields": ["mathematics", "english", "kiswahili",
                       "science_technology", "sst_cre",
                       "agri_nutrition", "creative_arts"]
        },
        "junior": {
            "grades": ["Grade 7", "Grade 8", "Grade 9"],
            "columns": [
                ('Reg No', 15),
                ('Name', 40),
                ('Grade', 15),
                ('Stream', 15),
                ('Maths', 15),
                ('Eng', 15),
                ('Kisw', 15),
                ('SST/CRE', 15),
                ('Agri&Nutr', 15),
                ('CreArts', 15),
                ('Pre/Bs/Comps', 15),
                ('InteSci', 15),
                ('Total', 15),
                ('Mean', 15),
                ('Position', 15),
                ('O/Position', 15),
            ],
            "fields": ["mathematics", "english", "kiswahili",
                       "sst_cre", "agri_nutrition", "creative_arts",
                       "pretech_bs_computer", "integrated_science"]
        }
    }

    # --- Helper: get marks + related students ---
    def get_students_and_marks(g, term, exam_type):
        marks_qs = Marks.objects.select_related('registration_no').filter(
            school_id=school_id,
            registration_no__grade=g,
            term=term,
            type_of_exam=exam_type
        ).exclude(total_marks__isnull=True).exclude(total_marks=0)

        # Build student lookup map
        students = StudentInfo.objects.filter(
            school_id=school_id,
            registration_no__in=marks_qs.values_list('registration_no__registration_no', flat=True)
        )
        student_map = {s.registration_no: s for s in students}
        return marks_qs, student_map

    def write_pdf_to_zip(pdf, filename, zip_file):
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        zip_file.writestr(filename, pdf_bytes)

    # --- PDF generation for each group ---
    def generate_pdf_for_group(group_name, config, zip_file):
        for g in config["grades"]:
            if grade and grade != g:
                continue

            marks_qs, student_map = get_students_and_marks(g, term, exam_type)
            if not marks_qs.exists():
                continue

            pdf = FPDF()
            pdf.add_page()
            pdf_header(request, pdf, 30)

            pdf.ln(5)
            pdf.set_font('Arial', size=10, style='B')
            pdf.cell(0, 10, f"{g}   {exam_type}   {term}")
            pdf.ln(8)

            # --- Table headers ---
            pdf.set_font('Arial', size=6, style='B')
            for col, width in config["columns"]:
                pdf.cell(width, 5, col, border=1, align='C')
            pdf.ln()

            # --- Table data ---
            pdf.set_font('Arial', size=5)
            for mark in marks_qs:
                student = student_map.get(mark.registration_no.registration_no)
                if not student:
                    continue

                row = [
                    student.registration_no,
                    f"{student.first_name} {student.second_name or ''} {student.surname or ''}".strip(),
                    student.grade,
                    student.stream,
                ]
                row += [getattr(mark, field, 0) or 0 for field in config["fields"]]
                row += [
                    mark.total_marks or 0,
                    mark.mean_marks or 0,
                    getattr(mark, 'position', '-'),
                    getattr(mark, 'overall_position', '-')
                ]

                for val, (_, width) in zip(row, config["columns"]):
                    pdf.cell(width, 5, str(val), border=1, align='L')
                pdf.ln()

            filename = f"{g}_{term}_{exam_type}_results.pdf"
            write_pdf_to_zip(pdf, filename, zip_file)

    # --- Build ZIP with all grade-level PDFs ---
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for group, config in grade_configs.items():
            generate_pdf_for_group(group, config, zip_file)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="result_papers.zip"'
    return response

import io
import zipfile
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from ..models import Marks, StudentInfo
from fpdf import FPDF
from datetime import datetime





class PdfReportForm(FPDF):
    def add_watermark(self, text):
        self.set_font('Arial', size=100, style='B')
        self.set_text_color(200, 200, 200)
        self.set_xy(0, 0)
        width = self.get_string_width(text)
        x = (self.w - width) / 2
        y = self.h / 2
        self.text(x, y, text)
        self.rotate(45, x=x, y=y)
        self.rotate(0)

    def add_background_color(self, r, g, b):
        self.set_fill_color(r, g, b)
        self.rect(0, 0, self.w, self.h, style='F')




        


@login_required
def print_report_forms(request):
    school_id = request.session.get('school_id')
    storage = messages.get_messages(request)
    storage.used = True

    term = request.GET.get('term')
    grade = request.GET.get('grade')
    stream = request.GET.get('stream')

    alias = get_school_db_alias_from_session(request)

    # --- Get all marks with valid total marks ---
    marks_qs = Marks.objects.filter(school_id=school_id).exclude(total_marks__isnull=True).exclude(total_marks=0)

    if term:
        marks_qs = marks_qs.filter(term=term)
    if grade:
        marks_qs = marks_qs.filter(registration_no__grade=grade)
    if stream:
        marks_qs = marks_qs.filter(registration_no__stream=stream)

    # --- Students for this grade/stream ---
    reg_nos = marks_qs.values_list('registration_no', flat=True).distinct()
    students = StudentInfo.objects.filter(school_id=school_id, registration_no__in=reg_nos)
    student_map = {s.registration_no: s for s in students}

    lower_grades = ['PP1','PP2','Grade 1', 'Grade 2', 'Grade 3']
    upper_grades = ['Grade 4', 'Grade 5', 'Grade 6']
    junior_grades = ['Grade 7', 'Grade 8', 'Grade 9']

    # --- Compute mean marks per student ---
    student_means = defaultdict(dict)
    for mark in Marks.objects.filter(school_id=school_id).exclude(mean_marks__isnull=True).exclude(mean_marks=0):
        key = (mark.registration_no.registration_no, mark.term, mark.type_of_exam)
        student_means[key] = mark.mean_marks

    avg_mean_marks = {}
    for reg_no in reg_nos:
        student = student_map.get(reg_no)
        if not student:
            continue
        means = []
        for exam_type in ['Opener', 'Mid Term', 'End Term']:
            mean = student_means.get((reg_no, term, exam_type), 0)
            means.append(mean)
        avg_mean_marks[reg_no] = round(sum(means) / len(means), 2) if means else 0

    # --- Ranking: overall and stream-wise ---
    overall_list = [(reg_no, avg_mean_marks[reg_no]) for reg_no in reg_nos]
    overall_sorted = sorted(overall_list, key=lambda x: x[1], reverse=True)
    overall_rank, stream_rank = {}, {}

    current_rank = 1
    prev_mean = None
    for idx, (reg_no, mean) in enumerate(overall_sorted, start=1):
        if prev_mean is not None and mean != prev_mean:
            current_rank = idx
        overall_rank[reg_no] = current_rank
        prev_mean = mean

    streams = set(student_map[reg_no].stream for reg_no in reg_nos if reg_no in student_map)
    for s in streams:
        stream_students = [r for r in reg_nos if student_map.get(r) and student_map[r].stream == s]
        stream_sorted = sorted([(r, avg_mean_marks[r]) for r in stream_students], key=lambda x: x[1], reverse=True)
        rank, prev = 1, None
        for idx, (r, mean) in enumerate(stream_sorted, start=1):
            if prev is not None and mean != prev:
                rank = idx
            stream_rank[r] = rank
            prev = mean

    # --- PDF generation ---
    pdf = PdfReportForm()

    for reg_no in reg_nos:
        student = student_map.get(reg_no)
        if not student:
            continue

        # All exam marks for this student/term
        student_marks = Marks.objects.filter(
            school_id=school_id,
            registration_no=reg_no,
            term=term
        )
        exam_lookup = {m.type_of_exam: m for m in student_marks}

        # --- Subjects per CBC group ---
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
                ('pretech_bs_computer', 'Pretech/Bs/Comps'),
                ('integrated_science', 'Integrated Science'),
            ]
        else:
            subjects = []

        # --- Begin PDF page ---
        pdf.add_page()
        pdf.add_background_color(200, 220, 255)
        pdf.add_watermark(student.first_name.upper())
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', size=10, style='B')
        pdf_header(request, pdf, 30)
        pdf.ln(5)

        pdf.set_font('Arial', size=14, style='BU')
        pdf.cell(0, 5, 'Progressive Report Form', align='C')
        pdf.ln(8)

        full_name = f"{student.first_name} {student.second_name or ''} {student.surname or ''}".strip()
        pdf.set_font('Arial', size=10, style='B')
        pdf.cell(0, 8, f'Reg No: {student.registration_no}', align='L')
        pdf.cell(0, 8, f'Name: {full_name}', align='R', ln=True)
        pdf.cell(0, 8, f'Grade: {student.grade}', align='L')
        pdf.cell(0, 8, f'Stream: {student.stream}', align='R', ln=True)
        pdf.cell(0, 5, f'Term: {term}', align='C')
        pdf.ln(5)

        # --- Table header ---
        pdf.cell(60, 5, 'Learning Area', border=1, align='C')
        pdf.cell(20, 5, 'Opener', border=1, align='C')
        pdf.cell(20, 5, 'Mid Term', border=1, align='C')
        pdf.cell(20, 5, 'End Term', border=1, align='C')
        pdf.cell(20, 5, 'Average', border=1, align='C')
        pdf.cell(25, 5, 'Level', border=1, align='C')
        pdf.cell(25, 5, 'Remark', border=1, align='C')
        pdf.ln(5)
        pdf.set_font('Arial', size=12)

        # --- Subjects & averages ---
        for field, subject in subjects:
            opener = getattr(exam_lookup.get('Opener'), field, 0) if 'Opener' in exam_lookup else 0
            mid_term = getattr(exam_lookup.get('Mid Term'), field, 0) if 'Mid Term' in exam_lookup else 0
            end_term = getattr(exam_lookup.get('End Term'), field, 0) if 'End Term' in exam_lookup else 0
            avg = round((opener or 0 + mid_term or 0 + end_term or 0) / 3, 1)

            pdf.cell(60, 5, subject, border=1)
            for val in [opener, mid_term, end_term, avg]:
                pdf.cell(20, 5, str(round(val or 0, 1)), border=1, align='L')

            if avg >= 80:
                level, remark = 'E.E', 'Excellent'
            elif avg >= 70:
                level, remark = 'M.E', 'Very Good'
            elif avg >= 60:
                level, remark = 'A.E', 'Good'
            elif avg >= 50:
                level, remark = 'B.E', 'Aim Higher'
            else:
                level, remark = 'B.E', 'Improve'

            pdf.cell(25, 5, level, border=1)
            pdf.cell(25, 5, remark, border=1)
            pdf.ln()

        pdf.ln(8)

        # --- Summary Section ---
        pdf.cell(47.5, 5, 'Total Marks', align='L')
        pdf.cell(47.5, 5, 'Mean', align='L')
        pdf.cell(47.5, 5, 'Position', align='L')
        pdf.cell(47.5, 5, 'Overall Position', align='L')
        pdf.ln(5)

        end_term_mark = exam_lookup.get('End Term')
        total_marks = round(sum([m.total_marks or 0 for m in exam_lookup.values()]) / 3, 1) if exam_lookup else 0
        mean_marks = round(sum([m.mean_marks or 0 for m in exam_lookup.values()]) / 3, 1) if exam_lookup else 0
        position = stream_rank.get(reg_no, '-')
        overall_position = overall_rank.get(reg_no, '-')

        pdf.cell(47.5, 5, str(total_marks))
        pdf.cell(47.5, 5, str(mean_marks))
        pdf.cell(47.5, 5, str(position))
        pdf.cell(47.5, 5, str(overall_position))
        pdf.ln(8)

        # --- Fees Section ---
        fees = Fee.objects.filter(registration_no=student.registration_no, term=term)
        amount_billed = get_object_or_404(Grade, school_id=school_id, name=student.grade).expected_fee
        amount_paid = sum(f.amount for f in fees if f.amount)
        balance = amount_billed - Decimal(amount_paid)

        pdf.cell(0, 5, 'Fee Statement', align='C', ln=True)
        pdf.cell(63, 5, 'Amount Billed', align='C')
        pdf.cell(63, 5, 'Amount Paid', align='C')
        pdf.cell(63, 5, 'Balance', align='C', ln=True)
        pdf.cell(63, 5, str(amount_billed), align='C')
        pdf.cell(63, 5, str(amount_paid), align='C')
        pdf.cell(63, 5, str(balance), align='C', ln=True)
        pdf.ln(8)

        # --- Comments Section ---
        current_date = datetime.now().strftime("%d/%m/%Y")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.cell(0, 5, f'Closing Date: {current_date}    Opening Date: ....................', ln=True)
        pdf.cell(0, 5, 'Class Teacher Comment: ..................................................................................', ln=True)
        pdf.cell(0, 5, 'Guardian Comment: ......................................................................................', ln=True)
        pdf.ln(10)
        pdf.cell(0, 5, f'Date: {current_date}    H/T Sign & Stamp: ....................................', ln=True)

    # --- Final response ---
    response = HttpResponse(pdf.output(dest="S").encode('latin1'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{grade}_{stream}_report_forms.pdf"'
    return response


class PdfReciept(FPDF):
        def __init__(self,orientation = 'P', unit = 'mm',format = (110, 150)):
            super().__init__(orientation,unit, format)
        def add_watermark(self,text):
            self.set_font('Arial', size=50, style='B')
            self.set_text_color(200,200,200)
            self.set_xy(0,0)
            width = self.get_string_width(text)
            x = (self.w - width) / 2
            # x = self.w / 4
            y = self.h / 2

            self.text(x, y, text)
            self.rotate(45, x=x , y=y)
            self.rotate(0)
        def add_background_color(self,r,g,b):
            self.set_fill_color(r,g,b)
            self.rect(0,0, self.w, self.h, style='F')
        def add_header(self,request):
            logo = request.session['logo_path']
            name = request.session['school_name']
            address = request.session['address']
            contact = request.session['contact']
            email = request.session['email']
            motto = request.session['motto']
            if logo:
                try:
                    self.image(str(logo), x=10, y=10, w=25)
                    self.ln(20)  
                except Exception as e:
                    print(e)
                    self.image(str("static/images/logo.png"),x=10,y=10,w=25)
            self.ln(5)
            self.set_font("Arial", "B", 16)
            self.cell(0, 5, name, ln=1, align="R")
            self.set_font("Arial", "", 10)
            self.cell(0, 5, f"Address: {address}", ln=1, align="R")
            self.cell(0, 5, f"Tel: {contact}", ln=1, align="R")
            self.cell(0, 5, f"Email: {email}", ln=1, align="R")
            self.cell(0, 5,f"Motto: {motto}",ln=1,align="R")
            self.ln(5)  # space after header  
            self.line(10, self.get_y(), 200, self.get_y())
    












@login_required
def print_fee_reciept(request, fee_id):
    from decimal import Decimal
    from datetime import datetime

    school_id = request.session.get("school_id")
    storage = messages.get_messages(request)
    storage.used = True

    date = datetime.now()
    current_date = date.strftime("%d/%m/%Y")
    current_time = date.strftime("%H:%M:%S")

    alias = get_school_db_alias_from_session(request)

    # ✅ 1. Fetch the specific fee record
    fee = get_object_or_404(Fee.objects.filter(school_id=school_id),id = fee_id)
    personal_data = fee.registration_no
    print("Personal data: ",fee.registration_no)
    

    # ✅ 2. Get expected fee for the student's grade
    grade_fee = get_object_or_404(
        Grade.objects.filter(school_id=school_id), 
        name=personal_data.grade
    )
    expected_fee = Decimal(grade_fee.expected_fee or 0)

    # ✅ 3. Compute totals for that student, grade, stream & term
    all_payments = Fee.objects.filter(
        school_id=school_id,
        registration_no=personal_data.registration_no,
        term=fee.term,
    )

    total_paid = sum(Decimal(p.amount or 0) for p in all_payments)
    balance = expected_fee - total_paid

    # ✅ 4. Generate the PDF
    pdf = PdfReciept()
    pdf.add_page()
    pdf.add_background_color(200, 220, 255)  # light blue
    pdf.add_watermark(personal_data.first_name.upper())
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=10, style="B")
    pdf.add_header(request)

    pdf.set_font("Arial", size=7, style="BU")
    pdf.cell(0, 5, "Fee Payment Statement", align="C")
    pdf.ln(10)

    # ✅ Student Info
    pdf.set_font("Arial", size=7, style="B")
    pdf.cell(0, 5, f"Reg No: {personal_data.registration_no}", align="L")
    pdf.cell(
        0,
        5,
        f"Name: {personal_data.first_name} {personal_data.second_name or ''} {personal_data.surname or ''}",
        align="R",
        ln=True,
    )
    pdf.cell(0, 5, f"Grade: {personal_data.grade}", align="L")
    pdf.cell(0, 5, f"Stream: {personal_data.stream}", align="R", ln=True)
    pdf.ln(5)

    pdf.cell(0, 5, f"Date: {fee.date_of_payment or current_date}", align="L")
    pdf.cell(0, 5, f"Time: {getattr(fee, 'time', current_time)}", align="R", ln=True)
    pdf.cell(0, 5, f"Term: {fee.term}", align="L")
    pdf.ln(5)

    # ✅ Payment summary table
    pdf.set_font("Arial", size=7, style="B")
    pdf.cell(22, 5, "Expected Fee", border=1, align="C")
    pdf.cell(22, 5, "This Payment", border=1, align="C")
    pdf.cell(22, 5, "Total Paid", border=1, align="C")
    pdf.cell(22, 5, "Balance", border=1, align="C", ln=True)

    pdf.set_font("Arial", size=7)
    pdf.cell(22, 5, f"{expected_fee}", border=1, align="C")
    pdf.cell(22, 5, f"{fee.amount}", border=1, align="C")
    pdf.cell(22, 5, f"{total_paid}", border=1, align="C")
    pdf.cell(22, 5, f"{balance}", border=1, align="C", ln=True)
    pdf.ln(10)

    # ✅ Footer
    pdf.set_font("Arial", size=7)
    pdf.cell(80, 10, f"H/T SIGN & STAMP ........................  Date: {current_date}", ln=True)

    # ✅ Get school vision safely
    school = MasterSchool.objects.filter(id=school_id).first()
    vision = getattr(school, "vision", "Excellence in Academic and Moral Standards")

    pdf_footer(pdf, vision)

    # ✅ Return as PDF HTTP response
    response = HttpResponse(pdf.output(dest="S").encode("latin1"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{personal_data.registration_no}_fee_receipt.pdf"'
    return response


@login_required
def print_attendance_sheet(request):
    from datetime import datetime

    school_id = request.session.get('school_id')
    storage = messages.get_messages(request)
    storage.used = True

    grade = request.GET.get('grade', '')
    stream = request.GET.get('stream', '')
    term = request.GET.get('term', '')

    alias = get_school_db_alias_from_session(request)

    # ✅ Fetch all students in the selected grade/stream
    students_qs = StudentInfo.objects.filter(school_id=school_id)
    if grade:
        students_qs = students_qs.filter(grade=grade)
    if stream:
        students_qs = students_qs.filter(stream=stream)

    students = list(students_qs.order_by('registration_no'))

    # ✅ Attendance lookup (only for selected filters)
    attendance_qs = PupilAttendance.objects.filter(school_id=school_id)
    if grade:
        attendance_qs = attendance_qs.filter(registration_no__in = students)
    if stream:
        attendance_qs = attendance_qs.filter(registration_no__in =students) 
    if term:
        attendance_qs = attendance_qs.filter(term=term)

    # Build attendance map → { registration_no: [records] }
    attendance_map = {}
    for att in attendance_qs:
        attendance_map.setdefault(att.registration_no, []).append(att)

    # ✅ PDF generation
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf_header(request, pdf, 30)

    pdf.set_font('Arial', size=14, style='B')
    pdf.cell(0, 10, 'Attendance Sheet', align='C', ln=True)

    pdf.set_font('Arial', size=10)
    pdf.cell(
        0,
        8,
        f"Grade: {grade or '-'}   Stream: {stream or '-'}   Term: {term or '-'}",
        ln=True
    )
    pdf.ln(5)

    # ✅ Table header
    pdf.set_font('Arial', size=9, style='B')
    pdf.cell(25, 8, 'Reg No', border=1, align='C')
    pdf.cell(55, 8, 'Name', border=1, align='C')
    pdf.cell(20, 8, 'Grade', border=1, align='C')
    pdf.cell(20, 8, 'Stream', border=1, align='C')
    pdf.cell(50, 8, 'Date(s) Present', border=1, align='C')
    pdf.cell(20, 8, 'Term', border=1, align='C')
    pdf.ln()

    # ✅ Table body
    pdf.set_font('Arial', size=9)
    for student in students:
        name = " ".join(
            part for part in [student.first_name, student.second_name, student.surname] if part
        )
        records = attendance_map.get(student.registration_no, [])
        dates = ", ".join(
            r.date_of_attendance.strftime('%d/%m') for r in records
        ) if records else "-"

        pdf.cell(25, 8, str(student.registration_no), border=1)
        pdf.cell(55, 8, name or "Unknown", border=1)
        pdf.cell(20, 8, str(student.grade), border=1)
        pdf.cell(20, 8, str(student.stream), border=1)
        pdf.cell(50, 8, dates, border=1)
        pdf.cell(20, 8, str(term or "-"), border=1)
        pdf.ln()

    # ✅ File response
    safe_grade = grade.replace(" ", "_") if grade else "all"
    safe_stream = stream.replace(" ", "_") if stream else "all"
    safe_term = term.replace(" ", "_") if term else "all"

    response = HttpResponse(
        pdf.output(dest="S").encode("latin1"),
        content_type="application/pdf"
    )
    response['Content-Disposition'] = (
        f'attachment; filename="attendance_{safe_grade}_{safe_stream}_{safe_term}.pdf"'
    )
    return response


from datetime import datetime
from decimal import Decimal
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def print_all_fee_reciepts(request):
    school_id = request.session.get('school_id')
    storage = messages.get_messages(request)
    storage.used = True
    date = datetime.now()
    current_date = date.strftime("%d/%m/%Y")
    grade = request.GET.get('grade')
    stream = request.GET.get('stream')

    alias = get_school_db_alias_from_session(request)

    # ✅ Get all students who have fee records
    students = StudentInfo.objects.filter(
        grade=grade,
        stream=stream,
        school_id=school_id,
        registration_no__in=Fee.objects.filter(
            school_id=school_id
        ).values_list('registration_no', flat=True).distinct()
    )

    pdf = PdfReciept()
    pdf.set_auto_page_break(auto=True, margin=15)

    for student in students:
        # ✅ Fetch terms where student has payments
        terms = Fee.objects.filter(
            school_id=school_id,
            registration_no=student.registration_no
        ).values_list('term', flat=True).distinct()

        for term in terms:
            all_payments = Fee.objects.filter(
                school_id=school_id,
                registration_no=student.registration_no,
                term=term
            ).order_by('date_of_payment', 'time')

            total_paid = sum(Decimal(payment.amount) for payment in all_payments)
            grade_fee = get_object_or_404(Grade, school_id=school_id, name=student.grade)
            expected_fee = Decimal(grade_fee.expected_fee)
            balance = expected_fee

            # ✅ New page for each student+term
            pdf.add_page()
            pdf.add_background_color(200, 220, 255)
            pdf.add_watermark(student.first_name.upper())
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', size=10, style='B')
            pdf.add_header(request)

            pdf.set_font('Arial', size=7, style='BU')
            pdf.cell(0, 5, 'Fee Payment Statement', align='C', ln=True)
            pdf.ln(5)

            # ✅ Student info
            pdf.set_font('Arial', size=7, style='B')
            pdf.cell(90, 5, f'Reg No: {student.registration_no}', align='L')
            pdf.cell(0, 5, f'Name: {student.first_name} {student.second_name} {student.surname}', align='R', ln=True)
            pdf.cell(90, 5, f'Grade: {student.grade}', align='L')
            pdf.cell(0, 5, f'Stream: {student.stream}', align='R', ln=True)
            pdf.cell(0, 5, f'Term: {term}', ln=True)
            pdf.ln(3)

            # ✅ Payment table header
            pdf.set_font('Arial', size=7, style='B')
            pdf.cell(18, 6, 'Pay Mode', border=1, align='C')
            pdf.cell(20, 6, 'Amount Paid', border=1, align='C')
            pdf.cell(18, 6, 'Balance', border=1, align='C')
            pdf.cell(18, 6, 'Date', border=1, align='C')
            pdf.cell(16, 6, 'Time', border=1, align='C')
            pdf.ln()

            # ✅ Table body
            pdf.set_font('Arial', size=7)
            for payment in all_payments:
                balance -= Decimal(payment.amount)
                pdf.cell(18, 6, str(payment.mode_of_payment), border=1)
                pdf.cell(20, 6, str(payment.amount), border=1)
                pdf.cell(18, 6, str(balance), border=1)
                pdf.cell(18, 6, payment.date_of_payment.strftime("%d/%m/%Y"), border=1)
                pdf.cell(16, 6, payment.time.strftime("%H:%M:%S"), border=1)
                pdf.ln()

            pdf.ln(5)
            pdf.set_font('Arial', size=7)
            pdf.cell(0, 10, f'H/T SIGN & STAMP: .......................   Date: {current_date}', ln=True)

            # ✅ Footer / Vision
            school = get_object_or_404(MasterSchool, id=school_id)
            vision = getattr(school, 'vision', 'Excellence in Academic and Moral Standards')
            pdf_footer(pdf, vision)

    response = HttpResponse(pdf.output(dest="S").encode('latin1'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{grade}_{stream}_fee_statements.pdf"'
    return response


def print_leave_receipt(request, reg_no):
    school_id = request.session.get('school_id')
    storage = messages.get_messages(request)
    storage.used = True
    alias = get_school_db_alias_from_session(request)

    leave_data = get_object_or_404(
        LeaveManagement.objects.filter(school_id = school_id),
        registration_no=reg_no
    )
    student = leave_data.registration_no

    # Fee balance if leave is fees-related
    all_payments = Fee.objects.filter(
        school_id = school_id,
        registration_no=student.registration_no,
        term=leave_data.term
    )
    total_paid = sum(payment.amount for payment in all_payments)
    total_fees = get_object_or_404(Grade.objects.filter(school_id = school_id), name=student.grade).expected_fee
    balance = total_fees - Decimal(total_paid)

    # Current datetime
    date = datetime.now()
    current_date = date.strftime("%d/%m/%Y")
    current_time = date.strftime("%H:%M:%S")

    # PDF generation
    pdf = PdfReciept()
    pdf.add_page()
    pdf.add_background_color(200, 220, 255)  # light blue
    pdf.add_watermark(student.first_name.upper())
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', size=10, style='B')
    pdf.add_header(request)

    pdf.set_font('Arial', size=12, style='BU')
    pdf.cell(0, 5, 'Leave Out Receipt', align='C')
    pdf.ln(10)

    # Student info
    pdf.set_font('Arial', size=7, style='B')
    pdf.cell(0, 5, f'Reg No: {student.registration_no}', align='L')
    pdf.cell(0, 5, f'Name: {student.first_name} {student.second_name} {student.surname}', align='R', ln=True)
    pdf.cell(0, 5, f'Grade: {student.grade}', align='L')
    pdf.cell(0, 5, f'Stream: {student.stream}', align='R')
    pdf.ln(5)

    pdf.cell(0, 5, f'Date: {leave_data.date_of_leave or current_date}', align='L')
    pdf.cell(0, 5, f'Time: {getattr(leave_data, "time", current_time)}', align='R', ln=True)
    pdf.cell(0, 5, f'Term: {leave_data.term}', align='L')
    pdf.ln(10)

    # Leave confirmation text
    pdf.set_font('Arial', size=8, style='BIU')
    pdf.multi_cell(0,5,"This is a confirmation receipt that student with details stated above has been given permission to be out of school due to:",align='C')
   
    pdf.ln(5)

    # Leave statement table
    pdf.set_font('Arial', size=7, style='B')
    pdf.cell(45, 5, 'Reason For Leave', border=1, align='C')
    pdf.cell(45, 5, 'Details', border=1, ln=True, align='C')

    pdf.set_font('Arial', size=7)
    if leave_data.reason == 'School Fees':
        pdf.cell(45, 5, 'School Fees', border=1, align='L')
        pdf.cell(45, 5, f'Balance: {balance}', border=1, ln=True, align='L')
    else:
        pdf.cell(45, 5, 'Other', border=1, align='L')
        pdf.cell(45, 5, leave_data.other_reason, border=1, ln=True, align='L')

    pdf.ln(10)
    pdf.set_font('Arial', size=7)
    pdf.cell(60, 10, f'H/T SIGN & STAMP .......................   Date: {current_date}', ln=True)

    # Footer with vision
    school = MasterSchool.objects.first()
    vision = getattr(school_id, 'vision', 'Excellence in Academic and Moral Standards')
    pdf_footer(pdf, vision)

    response = HttpResponse(pdf.output(dest="S").encode('latin1'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{reg_no}_leave_receipt.pdf"'
    return response
from django.shortcuts import redirect
def print_leave_receipts(request):
    school_id = request.session.get('school_id')
    grade = request.GET.get('grade')
    stream = request.GET.get('stream')
    alias = get_school_db_alias_from_session(request)

    # Filter leave records by grade & stream
    all_leaves = LeaveManagement.objects.filter(
        school_id=school_id,
        registration_no__in=StudentInfo.objects.filter(
            school_id=school_id,
            grade=grade,
            stream=stream
        ).values_list('registration_no', flat=True)
    ).order_by('registration_no')

    if not all_leaves.exists():
        messages.error(request, f"No leave records found for Grade {grade} - {stream}.")
        return redirect('leave_management')

    # Initialize PDF
    pdf = PdfReciept()

    for leave_data in all_leaves:
        student = leave_data.registration_no

        # Fee balance if leave is fees-related
        all_payments = Fee.objects.filter(
            school_id=school_id,
            registration_no=student.registration_no,
            term=leave_data.term
        )
        total_paid = sum(payment.amount for payment in all_payments)
        total_fees = get_object_or_404(
            Grade.objects.filter(school_id=school_id),
            name=student.grade
        ).expected_fee
        balance = total_fees - Decimal(total_paid)

        # Current datetime
        date = datetime.now()
        current_date = date.strftime("%d/%m/%Y")
        current_time = date.strftime("%H:%M:%S")

        # New page per student
        pdf.add_page()
        pdf.add_background_color(200, 220, 255)
        pdf.add_watermark(student.first_name.upper())
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', size=10, style='B')
        pdf.add_header(request)

        pdf.set_font('Arial', size=12, style='BU')
        pdf.cell(0, 5, 'Leave Out Receipt', align='C')
        pdf.ln(10)

        # Student info
        pdf.set_font('Arial', size=7, style='B')
        pdf.cell(0, 5, f'Reg No: {student.registration_no}', align='L')
        pdf.cell(0, 5, f'Name: {student.first_name} {student.second_name} {student.surname}', align='R', ln=True)
        pdf.cell(0, 5, f'Grade: {student.grade}', align='L')
        pdf.cell(0, 5, f'Stream: {student.stream}', align='R')
        pdf.ln(5)

        pdf.cell(0, 5, f'Date: {leave_data.date_of_leave or current_date}', align='L')
        pdf.cell(0, 5, f'Time: {getattr(leave_data, "time", current_time)}', align='R', ln=True)
        pdf.cell(0, 5, f'Term: {leave_data.term}', align='L')
        pdf.ln(5)

        # Leave confirmation text
        pdf.set_font('Arial', size=7, style='IU')
        pdf.multi_cell(0,5,"This is a confirmation receipt that student with details stated above has been given permission to be out of school due to:",align='C')
        pdf.ln(5)

        # Leave statement table
        pdf.set_font('Arial', size=7, style='B')
        pdf.cell(45, 5, 'Reason For Leave', border=1, align='C')
        pdf.cell(45, 5, 'Details', border=1, ln=True, align='C')

        pdf.set_font('Arial', size=7)
        if leave_data.reason == 'School Fees':
            pdf.cell(45, 5, 'School Fees', border=1, align='L')
            pdf.cell(45, 5, f'Balance: {balance}', border=1, ln=True, align='L')
        else:
            pdf.cell(45, 5, 'Other', border=1, align='L')
            pdf.cell(45, 5, leave_data.other_reason, border=1, ln=True, align='L')

        pdf.ln(10)
        pdf.set_font('Arial', size=7)
        pdf.cell(60, 10, f'H/T SIGN & STAMP .......................   Date: {current_date}', ln=True)

        # Footer
        school = MasterSchool.objects.first()
        vision = getattr(school_id, 'vision', 'Excellence in Academic and Moral Standards')
        pdf_footer(pdf, vision)

    # Return merged PDF
    response = HttpResponse(pdf.output(dest="S").encode('latin1'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="leave_receipts for {grade}_{stream}.pdf"'
    return response
