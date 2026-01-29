from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from django.http import JsonResponse, HttpResponse
from django.contrib import messages

from ..models import*
from django.db.models import Sum, Avg, Count
from django.utils.timezone import now
from datetime import datetime
from reportlab.pdfgen import canvas

import zipfile, io
import io
import zipfile
from collections import defaultdict

from decimal import Decimal


import pymysql
import os

import os
import pymysql







from fpdf import FPDF
import os
from django.conf import settings 
# NOTE: Ensure 'os' and 'settings' are imported in the file where this function resides.

def pdf_header(request, pdf, x):
    school_logo_relative_path = request.session.get('logo_path')
    name = request.session.get('school_name')
    address = request.session.get('address')
    contact = request.session.get('contact')
    email = request.session.get('email')
    motto = request.session.get('motto')
    
    # 1. Define Absolute Paths
    
    # System Logo (Static file, Left side)
    # Correctly resolve the static path components to prevent mixed-slash errors
    system_logo_absolute_path = os.path.join('', 'static', 'images', 'logo.png')
    
    # --- Placement Variables ---
    LOGO_WIDTH = 25  # Standard width for both logos
    LEFT_X = 10      # Far left side of the page (10mm margin)
    RIGHT_X = 210 - 10 - LOGO_WIDTH # Right side: Page Width (210) - Margin (10) - Logo Width (25) = 175
    TOP_Y = 10       # Top margin
    
    # --- 2. Place Logos ---
    
    # Place the System Logo (Left Side)
    try:
        pdf.image(system_logo_absolute_path, x=LEFT_X, y=TOP_Y, w=LOGO_WIDTH)
    except Exception as e:
        print(f"Error loading system logo: {e}")
        # On failure, leave the space blank or print a placeholder
    
    # Place the School Logo (Right Side)
    if school_logo_relative_path:
        
        # 2a. Resolve the absolute path for the school logo (from database/MEDIA_ROOT)
        # We strip the MEDIA_URL prefix if it exists to join correctly with MEDIA_ROOT
        if school_logo_relative_path.startswith(settings.MEDIA_URL):
            relative_path_to_join = school_logo_relative_path[len(settings.MEDIA_URL):]
        else:
            relative_path_to_join = school_logo_relative_path

        school_logo_absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path_to_join)

        try:
            pdf.image(school_logo_absolute_path, x=RIGHT_X, y=TOP_Y, w=LOGO_WIDTH)
        except Exception as e:
            print(f"Error loading school logo: {e}")
            # On failure, this space remains blank
    
    # Common vertical position adjustment after logo placement
    pdf.ln(10)

    # --- 3. Center Text Continuation ---
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 5, name, ln=1, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Address: {address}", ln=1, align="C")
    pdf.cell(0, 5, f"Tel: {contact} | Email: {email}", ln=1, align="C")
    pdf.cell(0, 5, f"Motto: {motto}", ln=1, align="C")
    pdf.ln(5) # space after header  
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
from collections import defaultdict
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.contrib import messages

# --- IMPORT YOUR CUSTOM MODELS AND UTILS ---
from ..models import (
    StudentInfo, SubStrandMark, Strand, GradeStream # Assuming GradeStream exists
)
# Assuming FPDF and your utility functions are available
from fpdf import FPDF 
# from your_app.utils import pdf_header, get_school_db_alias_from_session 
# from your_app.pdf_utils import PdfReportForm 

# --- CBC Constants (Defined for the utility function) ---


def get_cbc_level_and_remark(avg_level):
    """Determines the CBC level and remark based on the calculated average level."""
    if avg_level is None or avg_level <= 0:
        return {'level': '-', 'remark': 'No Data'}
    capped_avg = min(avg_level, 4.0) 
    for code, data in sorted(CBC_LEVEL_MAP.items(), key=lambda item: item[1]['min_avg'], reverse=True):
        if capped_avg >= data['min_avg']:
            return {'level': code, 'remark': data['remark']}
    return {'level': 'BE', 'remark': CBC_LEVEL_MAP['BE']['remark']}

# --- Utility Functions (Placeholders, assume they work) ---
# NOTE: Replace with your actual utility function implementations
# -----------------------------------------------------
def write_pdf_to_zip(pdf, filename, zip_file):
    """
    Converts the PDF object content into bytes and writes it to the zip file.
    """
    # 1. Output the PDF object content as raw bytes (dest='S')
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    
    # 2. Add the bytes to the zip archive with the specified filename
    zip_file.writestr(filename, pdf_bytes)
from django.http import HttpResponse
from django.db.models import Avg, Count, Q
from django.contrib import messages
from collections import defaultdict
import io # Restored for zip file structure
import zipfile # Restored for zip file structure
# Placeholder imports - Replace with your actual model/utility imports
# from .models import SubStrandMark, GradeStream, StudentInfo, Strand 
# from .utils import get_school_db_alias_from_session, pdf_header, get_cbc_level_and_remark
# from fpdf import FPDF # Assuming FPDF is used

# NOTE: The implementation of FPDF is complex. I am using placeholders (FPDF, pdf_header)
# and assuming you have a utility function for CBC level mapping (get_cbc_level_and_remark).


# --- DUMMY UTILITY FUNCTIONS FOR DEBUGGING ---
# Retaining dummy functions just in case the error was transient or environmental

# ---------------------------------------------

# Restored original PDF writing function for ZIP output
def write_pdf_to_zip(pdf, filename, zip_file):
    """
    Converts the PDF object content into bytes and writes it to the zip file.
    """
    # 1. Output the PDF object content as raw bytes (dest='S')
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    
    # 2. Add the bytes to the zip archive with the specified filename
    zip_file.writestr(filename, pdf_bytes)


def generate_result_papers_cbc(request):
    school_id = request.session.get("school_id")
    messages.get_messages(request).used = True

    grade_filter = request.GET.get('grade', '')
    stream_filter = request.GET.get('stream','')
    term_filter = request.GET.get('term', '')
    assessment_type_filter = request.GET.get('assessment_type', '') # RENAMED filter variable, assuming 'exam_type' was renamed
    # If the user still uses 'exam_type' in the request, fall back to it:
    if not assessment_type_filter:
        assessment_type_filter = request.GET.get('exam_type', '')
    

    # --- Data Retrieval (Modified to group by Subject) ---
    
    # 1. --- Define Target Grades and Streams (Used for Student Filtering) ---
    grade_stream_qs = GradeStream.objects.filter(school_id=school_id)
    if grade_filter:
        grade_stream_qs = grade_stream_qs.filter(grade=grade_filter, stream=stream_filter)

    # 2. --- Aggregate ALL Marks by Student and Subject ---
    
    # Base filters for marks (StudentInfo linkage for school_id, plus term/assessment filters)
    base_mark_filters = Q(student__school_id=school_id, sub_strand__strand__isnull=False)
    if term_filter:
        base_mark_filters &= Q(term=term_filter)
    
    # Filter by the assessment type (formerly exam_type)
    if assessment_type_filter:
        base_mark_filters &= Q(assessment_type=assessment_type_filter)
    
    # AGGREGATE BY SUBJECT: Group by student and sub_strand__strand__subject
    subject_averages_qs = SubStrandMark.objects.filter(base_mark_filters).values(
        'student__registration_no', 
        'sub_strand__strand__subject' # <-- KEY CHANGE: Group by Subject Name (Learning Area)
    ).annotate(
        avg_level=Avg('level'),
        avg_score=Avg('score'),
        total_sub_strand_marks=Count('id')
    )
    
    student_subject_data = defaultdict(lambda: defaultdict(lambda: {'level': None, 'score': None, 'count': 0}))
    for data in subject_averages_qs:
        reg_no = data['student__registration_no']
        # Retrieve the Learning Area (Subject) name
        subject_name = data.get('sub_strand__strand__subject') # <-- Changed key
        
        if subject_name:
            student_subject_data[reg_no][subject_name]['level'] = data['avg_level']
            student_subject_data[reg_no][subject_name]['score'] = data['avg_score']
            student_subject_data[reg_no][subject_name]['count'] = data['total_sub_strand_marks']

    # 3. --- Aggregate Overall Student Mean for Ranking (Uses Subject Averages) ---
    reg_nos_with_marks = subject_averages_qs.values_list('student__registration_no', flat=True).distinct()
    overall_mean_level = {}
    overall_mean_score = {}
    
    for reg_no in reg_nos_with_marks:
        subject_data = student_subject_data[reg_no].values()
        levels = [d['level'] for d in subject_data if d['level'] is not None]
        scores = [d['score'] for d in subject_data if d['score'] is not None]
        
        if levels:
            overall_avg_level = sum(levels) / len(levels)
            overall_mean_level[reg_no] = round(min(overall_avg_level, 3.0), 2)
        if scores:
            overall_mean_score[reg_no] = round(sum(scores) / len(scores), 2)

    # 3c. Ranking Logic (Simplified Placeholder)
    overall_list = [(reg_no, overall_mean_level.get(reg_no, 0)) for reg_no in reg_nos_with_marks]
    overall_sorted = sorted(overall_list, key=lambda x: x[1], reverse=True)
    overall_rank, stream_rank = {}, defaultdict(dict)
    current_rank = 1
    prev_mean = None
    
    # Calculate global rank based on average level
    for idx, (reg_no, mean) in enumerate(overall_sorted, start=1):
        if prev_mean is not None and mean != prev_mean: current_rank = idx
        overall_rank[reg_no] = current_rank
        prev_mean = mean
    # --- End Ranking Placeholder ---

    # 4. --- Get Student Info and Subject List ---
    
    students_query = StudentInfo.objects.filter(
        school_id=school_id, 
        registration_no__in=reg_nos_with_marks
    )
    # MODIFIED: Only filter by grade if a grade filter is provided.
    if grade_filter:
        students_query = students_query.filter(grade=grade_filter)
        
    students = students_query
    student_map = {s.registration_no: s for s in students}
    
    # Get list of unique subjects (Learning Areas) for the PDF header
    subject_query = Strand.objects.all()
    # MODIFIED: Only filter subject list by grade if a grade filter is provided.
    if grade_filter:
        subject_query = subject_query.filter(grade=grade_filter)
        
    all_subjects_in_grade = list(subject_query.values_list('subject', flat=True).distinct()) # <-- Cast to list for safety
    
    # Group students by grade and stream
    students_by_group = defaultdict(lambda: defaultdict(list))
    for s in students:
        # Check if the student actually has marks being processed
        if s.registration_no in reg_nos_with_marks:
            students_by_group[s.grade][s.stream].append(s)

    # --- Debugging Check ---
    print(f"Total students found matching criteria: {students_query.count()}")
    print(f"Subjects found: {all_subjects_in_grade}")
    if not students_by_group:
        messages.error(request, "No student data found for the selected filters.")
        # If no students are found, return an empty response gracefully
        return HttpResponse("No student data found for the selected filters.", status=204) # 204 No Content


    # 5. --- PDF Generation Loop (FIXED ALIGNMENT) ---
    zip_buffer = io.BytesIO()
    
    # Define Column Widths and Constants
    WIDTH_REGNO = 15.0
    WIDTH_NAME = 30.0
    WIDTH_MEAN_RANK = 12.0
    WIDTH_TOTAL_FIXED = WIDTH_REGNO + WIDTH_NAME + WIDTH_MEAN_RANK * 2 # 69mm
    
    # NOTE: Retaining 210.0mm (Portrait A4 width) based on your original working code, 
    # even though later requests suggested Landscape (297.0mm). Reverting for stability.
    PDF_PAGE_WIDTH = 210.0 
    MARGIN_LEFT_RIGHT = 10.0
    
    # Available width for dynamic subjects
    SUBJECTS_AREA_WIDTH = PDF_PAGE_WIDTH - (MARGIN_LEFT_RIGHT * 2) - WIDTH_TOTAL_FIXED # ~131mm available
    
    # Ensure safe division if no subjects are found (should be caught by the data checks, but safety first)
    num_subjects = max(len(all_subjects_in_grade), 1)
    subject_width = SUBJECTS_AREA_WIDTH / num_subjects
    
    ROW_HEIGHT_TOTAL = 5.0 
    ROW_HEIGHT_HALF = 2.5
    
    # PDF generation starts
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        
        for g, streams in students_by_group.items():
            for s, student_list in streams.items():
                
                # FPDF setup for each PDF (as in your original ZIP code)
                pdf = FPDF() # Assuming Landscape for content fit
                pdf.add_page()
                pdf.set_left_margin(MARGIN_LEFT_RIGHT)
                pdf.set_right_margin(MARGIN_LEFT_RIGHT)
                
                # --- Header Content (Appealing Style Maintained) ---
                pdf_header(request, pdf, 30)

                # --- PDF Page Title/Group Header ---
                pdf.ln(5)
                pdf.set_font('Arial', size=12, style='B')
                # Updated text to use assessment_type
                pdf.cell(0, 10, f"Grade: {g} \tStream: {s} \tTerm: {term_filter} \tAssessment: {assessment_type_filter}", align='C')
                pdf.ln(15)

                # -----------------------------------------------------------------
                # 6. --- TABLE HEADER CREATION (Fixed) ---
                # -----------------------------------------------------------------
                pdf.set_font('Arial', size=8, style='B')
                
                start_table_x = pdf.get_x()
                
                # A. Fixed Columns Header 
                pdf.cell(WIDTH_REGNO, 10, 'Reg No', border=1, align='C')
                pdf.cell(WIDTH_NAME, 10, 'Name', border=1, align='C')
                pdf.cell(WIDTH_MEAN_RANK, 10, 'Avg Level', border=1, align='C')
                pdf.cell(WIDTH_MEAN_RANK, 10, 'Rank', border=1, align='C')
                
                # B. Dynamic Subject Headers (Subject Name/Learning Area)
                pdf.set_xy(start_table_x + WIDTH_TOTAL_FIXED, pdf.get_y())
                
                for subject in all_subjects_in_grade:
                    # Print Subject Name spanning both score and level rows
                    pdf.cell(subject_width, 10, subject, border=1, align='C')

                pdf.ln(10) # Move cursor to the Y position below the header

                # -----------------------------------------------------------------
                # 7. --- STUDENT DATA ROWS (Fixed Alignment) ---
                # -----------------------------------------------------------------
                pdf.set_font('Arial', size=5)
                
                for student in student_list:
                    reg_no = student.registration_no
                    
                    current_y = pdf.get_y()
                    
                    # Row 1: Print Fixed Student Info (Takes up 100% of the row height, 5mm)
                    pdf.cell(WIDTH_REGNO, ROW_HEIGHT_TOTAL, reg_no, border=1, align='L')
                    pdf.cell(WIDTH_NAME, ROW_HEIGHT_TOTAL, f"{student.first_name} {student.surname}".strip(), border=1, align='L')
                    pdf.cell(WIDTH_MEAN_RANK, ROW_HEIGHT_TOTAL, str(overall_mean_level.get(reg_no, '-')), border=1, align='C')
                    pdf.cell(WIDTH_MEAN_RANK, ROW_HEIGHT_TOTAL, str(overall_rank.get(reg_no, '-')), border=1, align='C')
                    
                    start_dynamic_x = pdf.get_x() 
                    
                    
                    # --- A. Dynamic Subject Data: Score Row (Top Half) ---
                    pdf.set_xy(start_dynamic_x, current_y) # Set cursor to start of score block
                    
                    for subject_name in all_subjects_in_grade:
                        data = student_subject_data[reg_no].get(subject_name, {})
                        avg_score = data.get('score')
                        score_text = str(round(avg_score, 1)) + "%" if avg_score is not None else '-'
                        
                        pdf.cell(subject_width, ROW_HEIGHT_HALF, score_text, border='LTR', align='C')
                    
                    
                    # --- B. Dynamic Subject Data: Level Row (Bottom Half) ---
                    pdf.set_xy(start_dynamic_x, current_y + ROW_HEIGHT_HALF) # Set cursor to start of level block
                    
                    for subject_name in all_subjects_in_grade:
                        data = student_subject_data[reg_no].get(subject_name, {})
                        
                        avg_level = data.get('level')
                        # Using the DUMMY utility function
                        report = get_cbc_level_and_remark(avg_level) 
                        level_text = report['level']
                        
                        pdf.cell(subject_width, ROW_HEIGHT_HALF, level_text, border='LBR', align='C') 

                    # Move cursor to the start of the next student row
                    pdf.ln(ROW_HEIGHT_HALF) 
                    pdf.set_x(start_table_x) # Reset X to the very start of the table


                # --- File Naming ---
                filename = f"{g}_{s}_{term_filter}_results.pdf"
                

    response = HttpResponse(pdf.output(dest="S").encode('latin1'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{grade_filter}_{stream_filter}_results.pdf"'
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




        


import operator
from collections import defaultdict
from functools import reduce
from decimal import Decimal
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, F, Q
from django.http import HttpResponse

# --- IMPORT YOUR CUSTOM MODELS AND UTILS ---
# NOTE: Ensure these imports point to your actual models and utility files
from ..models import ( 
    StudentInfo, SubStrand, SubStrandMark, Fee, Grade, Strand, LearnerCompetency
)
# Assuming PdfReportForm is a custom class 
# from your_app.pdf_utils import PdfReportForm 

# --- CBC Constants (Levels) ---
CBC_LEVEL_MAP = {
    # Sorted descending by min_avg
    'EE': {'min_avg': 3.50, 'label': 'Exceeding Expectations', 'remark': 'Excellent Mastery'},
    'ME': {'min_avg': 2.50, 'label': 'Meeting Expectations', 'remark': 'Good Progress'},
    'AE': {'min_avg': 1.50, 'label': 'Approaching Expectations', 'remark': 'Needs Improvement'},
    'BE': {'min_avg': 0.00, 'label': 'Below Expectations', 'remark': 'Critical Intervention'},
}

core_competencies = [
        'Communication Skills',
        'Critical Thinking',
        'Creativity',
        'Collaboration',
        'Digital Literacy',
        'Learning to Learn',
        'Citizenship',
        'Self-Efficacy',
    ]
def get_cbc_level_and_remark(avg_level):
    """
    Determines the CBC level and remark based on the calculated average level (0-3).
    Handles None/No Data explicitly.
    """
    if avg_level is None or avg_level <= 0:
        return {'level': '-', 'remark': '-'}
    
    # CRITICAL GUARD: Cap the average at 3.0 before mapping
    capped_avg = min(avg_level, 4.0) 
        
    for code, data in sorted(CBC_LEVEL_MAP.items(), key=lambda item: item[1]['min_avg'], reverse=True):
        if capped_avg >= data['min_avg']:
            return {'level': code, 'remark': data['remark']}
            
    return {'level': 'BE', 'remark': CBC_LEVEL_MAP['BE']['remark']}


def print_report_forms_cbc(request):
    school_id = request.session.get('school_id')
    messages.get_messages(request).used = True

    term = request.GET.get('term')
    grade = request.GET.get('grade')
    stream = request.GET.get('stream')

    # 1. --- Base Query Filter for SubStrand Marks ---
    mark_filter_args = Q(
        sub_strand__strand__isnull=False, 
        term=term,
        sub_strand__strand__grade=grade 
    )
    if stream:
        mark_filter_args &= Q(student__stream=stream)


    # 2. --- Aggregate Average Level AND Score per Student and Subject ---
    
    all_marks_qs = SubStrandMark.objects.filter(mark_filter_args)
    
    # Group by student and the top-level Learning Area name
    student_subject_averages = all_marks_qs.values(
        'student__registration_no', 
        'sub_strand__strand__subject' # Grouping by the main Learning Area name
    ).annotate(
        avg_subject_level=Avg('level'),
        avg_subject_score=Avg('score'), # 🎯 CHANGE 1: CALCULATE AVERAGE NUMERIC SCORE
        total_sub_strand_marks=Count('id'),
        project_score=Avg('level', filter=Q(assessment_type='SBA-Project')),
        practical_score=Avg('level', filter=Q(assessment_type='SBA-Practical')),
        written_score=Avg('level', filter=Q(assessment_type='SBA-Written')),
    ).filter(total_sub_strand_marks__gt=0)
    
    # Store aggregated data: {reg_no: {subject_name: {'level': avg_level, 'score': avg_score}}}
    subject_data_lookup = defaultdict(lambda: defaultdict(lambda: {
        'level': None, 'score': None,
        'project': None, 'practical': None, 'written': None
    }))

    for data in student_subject_averages:
        reg_no = data['student__registration_no']
        subject_name = data.get('sub_strand__strand__subject') 
        
        if subject_name:
            subject_data_lookup[reg_no][subject_name]['level'] = data['avg_subject_level']
            subject_data_lookup[reg_no][subject_name]['score'] = data['avg_subject_score'] # Store the score
            subject_data_lookup[reg_no][subject_name]['project'] = data['project_score']
            subject_data_lookup[reg_no][subject_name]['practical'] = data['practical_score']
            subject_data_lookup[reg_no][subject_name]['written'] = data['written_score']

    # 3. --- Get Students and Compute Overall Mean (for Ranking) ---
    reg_nos_with_marks = student_subject_averages.values_list('student__registration_no', flat=True).distinct()
    students = StudentInfo.objects.filter(school_id=school_id, registration_no__in=reg_nos_with_marks)
    student_map = {s.registration_no: s for s in students}
    
    # Calculate overall average level AND overall average score for ranking/display
    avg_mean_level = {} 
    overall_avg_score = {} # Store overall score for the summary section
    
    for reg_no in reg_nos_with_marks:
        subject_data = subject_data_lookup[reg_no].values()
        
        if subject_data:
            # Separate lists for levels and scores across all subjects
            levels = [d['level'] for d in subject_data if d['level'] is not None]
            scores = [d['score'] for d in subject_data if d['score'] is not None]

            # Calculate overall average level (for ranking)
            if levels:
                overall_avg_level = sum(levels) / len(levels)
                capped_overall_avg = min(overall_avg_level, 3.0) 
                capped_overall_avg = min(overall_avg_level, 4.0) 
                avg_mean_level[reg_no] = round(capped_overall_avg, 2)
            else:
                avg_mean_level[reg_no] = 0
            
            # Calculate overall average score (for display)
            if scores:
                overall_score = sum(scores) / len(scores)
                overall_avg_score[reg_no] = round(overall_score, 2)
            else:
                overall_avg_score[reg_no] = 0
        else:
            avg_mean_level[reg_no] = 0
            overall_avg_score[reg_no] = 0

    # 4. --- Ranking Logic (Uses avg_mean_level for CBC ranking) ---
    overall_list = [(reg_no, avg_mean_level[reg_no]) for reg_no in reg_nos_with_marks]
    overall_sorted = sorted(overall_list, key=lambda x: x[1], reverse=True)
    overall_rank, stream_rank = {}, {}

    current_rank = 1
    prev_mean = None
    for idx, (reg_no, mean) in enumerate(overall_sorted, start=1):
        if prev_mean is not None and mean != prev_mean:
            current_rank = idx
        overall_rank[reg_no] = current_rank
        prev_mean = mean
        
    streams = set(student_map[reg_no].stream for reg_no in reg_nos_with_marks if reg_no in student_map)
    for s in streams:
        stream_students = [r for r in reg_nos_with_marks if student_map.get(r) and student_map[r].stream == s]
        stream_sorted = sorted([(r, overall_avg_score.get(r, 0)) for r in stream_students], key=lambda x: x[1], reverse=True)
        rank, prev = 1, None 
        for idx, (r, mean) in enumerate(stream_sorted, start=1):
            if prev is not None and mean != prev:
                rank = idx
            stream_rank[r] = rank
            prev = mean
            
    # 5. --- Subject List based on Grade Group ---
    # Fetch all unique Learning Area names for this grade to ensure the report prints all rows
    # NOTE: Using 'subject' field on Strand model.
    subjects_in_grade = Strand.objects.filter(grade=grade).values_list('subject', flat=True).distinct()
    
    # 6. --- PDF generation ---
    pdf = PdfReportForm()

    for reg_no in reg_nos_with_marks:
        student = student_map.get(reg_no)
        if not student:
            continue

        student_data = subject_data_lookup[reg_no]

        # competency ratings
        competency_summary = LearnerCompetency.objects.filter(
            student=student,
            term=term,
        ).values('competency').annotate(avg_level=Avg('level'))
        
        avg_level_map = {item['competency']: item['avg_level'] for item in competency_summary}


        # --- Begin PDF page (Unchanged) ---
        pdf.add_page()
        pdf.add_background_color(200, 220, 255)
        pdf.add_watermark(student.first_name.upper())
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', size=10, style='B')
        pdf_header(request, pdf, 30)
        pdf.ln(5)

        pdf.set_font('Arial', size=14, style='BU')
        pdf.cell(0, 5, 'Learner Competency Report', align='C') 
        pdf.ln(8)

        # Student Details (Unchanged)
        full_name = f"{student.first_name} {student.second_name or ''} {student.surname or ''}".strip()
        pdf.set_font('Arial', size=10, style='B')
        pdf.cell(0, 8, f'Reg No: {student.registration_no}', align='L')
        pdf.cell(0, 8, f'Name: {full_name}', align='R', ln=True)
        pdf.cell(0, 8, f'Grade: {student.grade}', align='L')
        pdf.cell(0, 8, f'Stream: {student.stream}', align='R', ln=True)
        pdf.cell(0, 5, f'Term: {term}', align='C')
        pdf.ln(5)

        # --- Table header: ADDED AVG SCORE COLUMN ---
        pdf.set_font('Arial', size=8, style='B')
        pdf.cell(40, 5, 'Learning Area', border=1, align='C')
        pdf.cell(20, 5, 'SBA-Proj', border=1, align='C')
        pdf.cell(20, 5, 'SBA-Prac', border=1, align='C')
        pdf.cell(20, 5, 'SBA-Writ', border=1, align='C')
        pdf.cell(20, 5, 'Avg Score', border=1, align='C')
        pdf.cell(20, 5, 'Avg Level', border=1, align='C')
        pdf.cell(20, 5, 'CBC Level', border=1, align='C')
        pdf.cell(30, 5, 'Remark', border=1, align='C', ln=True)
        
        pdf.set_font('Arial', size=8) # Reduced font size for more columns

        # --- Subject Levels, Scores, & Remarks ---
        for subject_name in subjects_in_grade:
            data = student_data.get(subject_name, {})
            avg_level = data.get('level')
            avg_score = data.get('score')
            proj = data.get('project')
            prac = data.get('practical')
            writ = data.get('written')
            
            # --- Get Level and Remark (handles None/No Data) ---
            report_data = get_cbc_level_and_remark(avg_level)
            
            pdf.cell(40, 5, subject_name, border=1)
            pdf.cell(20, 5, f"{round(proj, 1)}" if proj is not None else "-", border=1, align='C')
            pdf.cell(20, 5, f"{round(prac, 1)}" if prac is not None else "-", border=1, align='C')
            pdf.cell(20, 5, f"{round(writ, 1)}" if writ is not None else "-", border=1, align='C')
            pdf.cell(20, 5, f"{round(avg_score, 1)}" if avg_score is not None else "-", border=1, align='C')
            pdf.cell(20, 5, f"{round(avg_level, 2)}" if avg_level is not None else "-", border=1, align='C')
            pdf.cell(20, 5, report_data['level'], border=1, align='C')
            pdf.cell(30, 5, report_data['remark'], border=1, align='C', ln=True)

        pdf.ln(4)

        # --- Summary Section (Adjusted to reflect both Level and Score) ---
        pdf.set_font('Arial', size=10, style='B')
        pdf.cell(47.5, 5, 'Average Competency', border=1, align='L') # Avg Level
        pdf.cell(47.5, 5, 'Average Score (%)', border=1, align='L') # 🎯 CHANGE 4: Overall Score
        pdf.ln(5)

        overall_avg_level = avg_mean_level.get(reg_no, 0)
        overall_score = overall_avg_score.get(reg_no, 0) # Get overall score
        overall_position = overall_rank.get(reg_no, '-')

        pdf.set_font('Arial', size=10)
        pdf.cell(47.5, 5, str(round(overall_avg_level, 2)), border=1)
        pdf.cell(47.5, 5, str(round(overall_score, 1)), border=1) # 🎯 CHANGE 5: Display Overall Score
        pdf.ln(8)

        # --- Competency Breakdown by Learning Area ---
        # core_competencies = [
        #     'Communication Skills', 'Critical Thinking', 'Creativity', 'Collaboration',
        #     'Digital Literacy', 'Learning to Learn', 'Citizenship', 'Self-Efficacy'
        # ]
        
        comp_qs = LearnerCompetency.objects.filter(student=student, term=term).values('subject', 'competency', 'level')
        comp_map = defaultdict(dict)
        for c in comp_qs:
            comp_map[c['subject']][c['competency']] = c['level']
        

        pdf.set_font('Arial', size=10, style='B')
        pdf.cell(0, 5, 'Competency Breakdown by Learning Area', align='L', ln=True)
        pdf.ln(2)
        
        pdf.set_font('Arial', size=5, style='B')
        pdf.cell(35, 5, 'Learning Area', border=1)
        col_w = (190 - 35) / len(core_competencies)
        for comp in core_competencies:
            pdf.cell(col_w, 5, comp, border=1, align='C')
        pdf.ln()
        
        pdf.set_font('Arial', size=5)
        for subj in subjects_in_grade:
            pdf.cell(35, 5, subj, border=1)
            for comp in core_competencies:
                val = comp_map.get(subj, {}).get(comp)
                print(comp,val)
                pdf.cell(col_w, 5, str(round(val, 1)) if val else "-", border=1, align='C')
                
            pdf.ln()
        
        pdf.ln(5)

        
        pdf.ln(5)

        # Competency Level Summary
        pdf.set_font('Arial', size=10, style='B')
        pdf.cell(0, 5, 'Aggregated Learning Area Competency', align='L', ln=True)
        pdf.ln(2)
        
        pdf.set_font('Arial', size=6, style='B')
        for competency_name in core_competencies:
            pdf.cell(23, 5, competency_name, border=1, align="C", ln=0)
        pdf.ln(5)

        pdf.set_font('Arial', size=6)
        for competency_name in core_competencies:
            val = avg_level_map.get(competency_name, 0.0)
            pdf.cell(23, 5, str(round(val, 2)) if val else "-", border=1, align="C", ln=0)
        pdf.ln(8)

        
        
        # --- Fees section and closing remarks (Unchanged) ---
        fees = Fee.objects.filter(registration_no=student.registration_no, term=term)
        amount_billed = get_object_or_404(Grade, school_id=school_id, name=student.grade).expected_fee
        amount_paid = sum(f.amount for f in fees if f.amount)
        balance = amount_billed - Decimal(amount_paid)

        pdf.set_font('Arial', size=8, style='B')
        pdf.cell(0, 5, 'Fee Statement', align='C', ln=True)
        pdf.cell(63, 5, 'Amount Billed', align='C')
        pdf.cell(63, 5, 'Amount Paid', align='C')
        pdf.cell(63, 5, 'Balance', align='C', ln=True)
        pdf.set_font('Arial', size=8)
        pdf.cell(63, 5, str(amount_billed), align='C')
        pdf.cell(63, 5, str(amount_paid), align='C')
        pdf.cell(63, 5, str(balance), align='C', ln=True)
        pdf.ln(5)

        # --- Comments Section ---
        current_date = datetime.now().strftime("%d/%m/%Y")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_font('Arial', size=8, style='B')
        pdf.cell(0, 5, f'Closing Date: {current_date}                                                                                                  Opening Date: ..............................', ln=True)
        pdf.ln(4)
        pdf.cell(0, 5, 'Class Teacher Comment: ..............................................................................................................................................................................', ln=True)
        pdf.ln(4)
        pdf.cell(0, 5, 'Guardian Comment: ......................................................................................................................................................................................', ln=True)
        pdf.ln(4)
        pdf.cell(0, 5, f'Date: {current_date}                                                                                                         H/T Sign & Stamp: ....................................', ln=True)


    # --- Final response ---
    response = HttpResponse(pdf.output(dest="S").encode('latin1'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{grade}_{stream}_report_forms_cbc.pdf"'
    return response


def print_individual_report_form(request):
    school_id = request.session.get('school_id')

    # --- 1. Get student registration number and term ---
    registration_no = request.GET.get('registration_no')
    term = request.GET.get('term')

    if not registration_no:
        return HttpResponse("Missing registration_no", status=400)

    # --- 2. Fetch Student ---
    student = get_object_or_404(
        StudentInfo,
        school_id=school_id,
        registration_no=registration_no
    )

    grade = student.grade
    stream = student.stream

    # --- 3. Get Marks for this learner only ---
    marks_qs = SubStrandMark.objects.filter(
        student__registration_no=registration_no,
        term=term,
        sub_strand__strand__grade=grade
    )

    # Aggregate subject scores and levels
    subject_averages = marks_qs.values(
        'sub_strand__strand__subject'
    ).annotate(
        avg_level=Avg('level'),
        avg_score=Avg('score'),
        project_score=Avg('level', filter=Q(assessment_type='SBA-Project')),
        practical_score=Avg('level', filter=Q(assessment_type='SBA-Practical')),
        written_score=Avg('level', filter=Q(assessment_type='SBA-Written')),
        total_items=Count('id')
    ).filter(total_items__gt=0)

    # Build lookup {subject: {level, score}}
    subject_data = defaultdict(lambda: {'level': None, 'score': None})
    subject_data = defaultdict(lambda: {'level': None, 'score': None, 'project': None, 'practical': None, 'written': None})
    for record in subject_averages:
        subj = record['sub_strand__strand__subject']
        subject_data[subj]['level'] = record['avg_level']
        subject_data[subj]['score'] = record['avg_score']
        subject_data[subj]['project'] = record['project_score']
        subject_data[subj]['practical'] = record['practical_score']
        subject_data[subj]['written'] = record['written_score']

    # --- 4. Get all subjects in this grade ---
    subjects_in_grade = (
        Strand.objects.filter(grade=grade)
        .values_list('subject', flat=True)
        .distinct()
    )

    # --- 5. Compute overall score & level for this ONE learner ---
    levels = [d['level'] for d in subject_data.values() if d['level'] is not None]
    scores = [d['score'] for d in subject_data.values() if d['score'] is not None]

    overall_level = round(sum(levels) / len(levels), 2) if levels else 0
    overall_score = round(sum(scores) / len(scores), 2) if scores else 0

    # --- 5b. Calculate Overall Position (Rank) in Grade ---
    # Fetch marks for ALL students in this grade/term to determine rank
    all_grade_marks = SubStrandMark.objects.filter(
        student__school_id=school_id,
        student__grade=grade,
        term=term,
        sub_strand__strand__grade=grade
    ).values(
        'student__registration_no', 
        'sub_strand__strand__subject'
    ).annotate(
        avg_subj_score=Avg('score')
    )

    student_totals = defaultdict(list)
    for entry in all_grade_marks:
        if entry['avg_subj_score'] is not None:
            student_totals[entry['student__registration_no']].append(entry['avg_subj_score'])
    
    student_final_scores = {}
    for reg, s_scores in student_totals.items():
        if s_scores:
            student_final_scores[reg] = sum(s_scores) / len(s_scores)
        else:
            student_final_scores[reg] = 0
            
    sorted_grade_scores = sorted(student_final_scores.items(), key=lambda x: x[1], reverse=True)
    overall_position = '-' 
    current_rank = 1
    prev_score = None
    
    for idx, (reg, score) in enumerate(sorted_grade_scores, start=1):
        if prev_score is not None and score != prev_score:
            current_rank = idx
        if reg == registration_no:
            overall_position = current_rank
            break
        prev_score = score

    # competency ratings
    filtered_qs = LearnerCompetency.objects.filter(
    student__registration_no=registration_no,
    term=term,
    )

    # 2. Group the QuerySet by the 'competency' field using values().
    #    This is the equivalent of SQL's GROUP BY competency.
    # 3. Annotate the QuerySet with the average of the 'level' for each group.
    competency_summary = filtered_qs.values('competency').annotate(
        # F() is used here to reference the model field 'level'
        avg_level=Avg('level') 
    ).order_by('competency') 
    
    # --- 6. Initialize PDF ---
    pdf = PdfReportForm()
    pdf.add_page()
    pdf.add_background_color(200, 220, 255)
    pdf.add_watermark(student.first_name.upper())
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', size=10, style='B') 
    pdf_header(request, pdf, 30)
    pdf.ln(5)

    pdf.set_font('Arial', size=14, style='BU')
    pdf.cell(0, 5, 'Learner Competency Report', align='C') 
    pdf.ln(8)

    # --- 7. Student Details ---
    full_name = f"{student.first_name} {student.second_name or ''} {student.surname or ''}".strip()
    pdf.set_font('Arial', size=10, style='B')
    pdf.cell(0, 8, f'Reg No: {student.registration_no}', align='L')
    pdf.cell(0, 8, f'Name: {full_name}', align='R', ln=True)
    pdf.cell(0, 8, f'Grade: {student.grade}', align='L')
    pdf.cell(0, 8, f'Stream: {student.stream}', align='R', ln=True)
    pdf.cell(0, 5, f'Term: {term}', align='C')
    pdf.ln(5)

    # --- 8. Table Header ---
    pdf.set_font('Arial', size=10, style='B')
    
    pdf.set_font('Arial', size=8, style='B')
    pdf.cell(40, 5, 'Learning Area', border=1, align='C')
    pdf.cell(20, 5, 'SBA-Project', border=1, align='C')
    pdf.cell(20, 5, 'SBA-Practical', border=1, align='C')
    pdf.cell(20, 5, 'SBA-Written', border=1, align='C')
    pdf.cell(20, 5, 'Avg Score', border=1, align='C')
    pdf.cell(20, 5, 'Avg Level', border=1, align='C')
    pdf.cell(20, 5, 'CBC Level', border=1, align='C')
    pdf.cell(30, 5, 'Remark', border=1, align='C', ln=True)

    
    pdf.set_font('Arial', size=8)

    # --- 9. Populate Table ---
    for subject_name in subjects_in_grade:
        
        data = subject_data.get(subject_name, {'level': None, 'score': None, 'project': None, 'practical': None, 'written': None})
        avg_level = data['level']
        avg_score = data['score']
        proj = data['project']
        prac = data['practical']
        writ = data['written']

        # CBC mapping
        report = get_cbc_level_and_remark(avg_level)

        
        pdf.cell(40, 5, subject_name, border=1)
        pdf.cell(20, 5, f"{round(proj,1)}" if proj is not None else "-", border=1, align='C')
        pdf.cell(20, 5, f"{round(prac,1)}" if prac is not None else "-", border=1, align='C')
        pdf.cell(20, 5, f"{round(writ,1)}" if writ is not None else "-", border=1, align='C')
        pdf.cell(20, 5, f"{round(avg_score,1)}" if avg_score is not None else "-", border=1, align='C')
        pdf.cell(20, 5, f"{round(avg_level,2)}" if avg_level is not None else "-", border=1, align='C')
        pdf.cell(20, 5, report['level'], border=1, align='C')
        pdf.cell(30, 5, report['remark'], border=1, align='C', ln=True)

    pdf.ln(5)

    pdf.set_font('Arial', size=8, style='B')
    pdf.cell(47.5, 5, 'Average Competency', border=1)
    pdf.cell(47.5, 5, 'Average Score (%)', border=1,ln=True)

    pdf.set_font('Arial', size=12)
    pdf.cell(47.5, 5, str(overall_level), border=1)
    pdf.cell(47.5, 5, str(overall_score), border=1)
    pdf.ln(8)

    # --- Competency Breakdown by Learning Area ---
    # core_competencies = [
    #     'Communication Skills', 'Critical Thinking', 'Creativity', 'Collaboration',
    #     'Digital Literacy', 'Learning to Learn', 'Citizenship', 'Self-Efficacy'
    # ]
    
    comp_qs = LearnerCompetency.objects.filter(student=student, term=term).values('subject', 'competency', 'level')
    comp_map = defaultdict(dict)
    for c in comp_qs:
        comp_map[c['subject']][c['competency']] = c['level']

    pdf.set_font('Arial', size=10, style='B')
    pdf.cell(0, 5, 'Competency Breakdown by Learning Area', align='L', ln=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', size=5, style='B')
    pdf.cell(35, 5, 'Learning Area', border=1)
    col_w = (190 - 35) / len(core_competencies)
    for comp in core_competencies:
        pdf.cell(col_w, 5, comp, border=1, align='C')
    pdf.ln()
    
    pdf.set_font('Arial', size=5)
    for subj in subjects_in_grade:
        pdf.cell(35, 5, subj, border=1)
        for comp in core_competencies:
            val = comp_map.get(subj, {}).get(comp)
            pdf.cell(col_w, 5, str(round(val, 1)) if val else "-", border=1, align='C')
        pdf.ln()
    
    pdf.ln(5)

    # --- 10. Summary Section ---
    

    # --- core competency section ---
    avg_level_map = {
    item['competency']: item['avg_level'] 
    for item in competency_summary
    }
    
    pdf.set_font('Arial', size=10, style='B')
    pdf.cell(0, 5, 'Aggregated Learning Area Competency', align='L', ln=True)
    pdf.ln(2)
    
    pdf.set_font('Arial',size = 6,style='B') 
    for competency_name in core_competencies:
    # Print the Competency Name (Header)
    # The last cell will need to move to the next line (ln=1) IF it's the last competency
    # But for a full row, we keep ln=0 to continue horizontally.
        pdf.cell(23, 5, competency_name, border=1, align="C", ln=0)

    # Move the cursor to the next line after printing all headers
    # We use a large cell width here to ensure we push past the edge of the previous cells' cumulative width
    pdf.ln(5) # Or use pdf.cell(0, 0, ln=1) if preferred.


    # --- Step 2: Print the Values (Average Levels) ---

    # Reset the cursor to the same starting horizontal position for the values row
    pdf.set_xy(10, pdf.get_y()) 

    for competency_name in core_competencies:
        # 1. Use .get() for safe dictionary lookup.
        avg_level = avg_level_map.get(competency_name, 0.0)
        
        # 2. Print the Average Level (Value)
        # Ensure this cell width matches the header cell width (23 or 23.5).
        # Keep ln=0 to continue horizontally.
        pdf.cell(23, 5, str(round(avg_level, 2)), align="C", border=1, ln=0)

    # Move the cursor to the next line after printing all values
    pdf.ln(5)
    
        
    pdf.ln(5) 
    # list all competency values..
    
     

    # --- 11. Fee Section ---
    fees = Fee.objects.filter(registration_no=registration_no, term=term)
    amount_billed = Grade.objects.get(name=grade, school_id=school_id).expected_fee
    paid = sum(f.amount for f in fees)
    balance = amount_billed - paid

    pdf.set_font('Arial', size=8, style='B')
    pdf.cell(0, 5, 'Fee Statement', align='C', ln=True)

    pdf.set_font('Arial', size=8)
    pdf.cell(63, 5, f'Billed: {amount_billed}', border=1)
    pdf.cell(63, 5, f'Paid: {paid}', border=1)
    pdf.cell(63, 5, f'Balance: {balance}', border=1, ln=True)

    current_date = datetime.now().strftime("%d/%m/%Y")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font('Arial', size=8, style='B')
    pdf.cell(0, 5, f'Closing Date: {current_date}                                                                                       Opening Date: ..............................', ln=True)
    pdf.ln(4)
    pdf.cell(0, 5, 'Class Teacher Comment: ....................................................................................................................................................................', ln=True)
    pdf.ln(4)
    pdf.cell(0, 5, 'Guardian Comment: ............................................................................................................................................................................', ln=True)
    pdf.ln(5)
    pdf.cell(0, 5, f'Date: {current_date}      H/T Sign & Stamp: ....................................', ln=True)


    # --- 12. Output PDF ---
    response = HttpResponse(pdf.output(dest="S").encode('latin1'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{registration_no} {term}_report.pdf"'
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

from django.db.models import Q

@login_required
def print_attendance_sheet(request):
    from datetime import datetime, timedelta

    school_id = request.session.get('school_id')
    storage = messages.get_messages(request)
    storage.used = True

    grade = request.GET.get('grade', '')
    stream = request.GET.get('stream', '')
    term = request.GET.get('term', '')
    date_filter = request.GET.get('date_filter', 'term')


    # ✅ Fetch all students in the selected grade/stream
    students_qs = StudentInfo.objects.filter(school_id=school_id)
    if grade:
        students_qs = students_qs.filter(grade=grade)
    if stream:
        students_qs = students_qs.filter(stream=stream)
   

    students = list(students_qs.order_by('registration_no'))

    # ✅ Attendance lookup (only for selected filters)
    attendance_qs = StudentAttendance.objects.filter(Q(status='Present') | Q(status='Absent'),school_id=school_id)

    if grade:
        attendance_qs = attendance_qs.filter(registration_no__in = students)
    if stream:
        attendance_qs = attendance_qs.filter(registration_no__in =students) 
    if term:
        attendance_qs = attendance_qs.filter(term=term)
   

    today = datetime.now().date()
    if date_filter == 'today':
        attendance_qs = attendance_qs.filter(date_of_attendance=today)
    elif date_filter == 'week':
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        attendance_qs = attendance_qs.filter(date_of_attendance__range=[start_week, end_week])

    # Build attendance map → { registration_no: [records] }
    attendance_map = {}
    for att in attendance_qs:
        attendance_map.setdefault(att.registration_no_id, []).append(att)
    print(attendance_map) 
    # ✅ PDF generation
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf_header(request, pdf, 30)

    pdf.set_font('Arial', size=14, style='B')
    pdf.cell(0, 10, 'Attendance Sheet', align='C', ln=True)

    pdf.set_font('Arial', size=10)

    subtitle = f"Grade: {grade or '-'}   Stream: {stream or '-'}   Term: {term or '-'}"
    if date_filter == 'today':
        subtitle += f" (Date: {today.strftime('%d/%m/%Y')})"
    elif date_filter == 'week':
        subtitle += " (This Week)"

    pdf.cell(
        0,
        8,
        subtitle,
        ln=True
    )
    pdf.ln(5)

    # ✅ Table header
    pdf.set_font('Arial', size=9, style='B')
    pdf.cell(25, 8, 'Reg No', border=1, align='C')
    pdf.cell(50, 8, 'Name', border=1, align='C')
    pdf.cell(20, 8, 'Grade', border=1, align='C')
    pdf.cell(20, 8, 'Stream', border=1, align='C')
    pdf.cell(25, 8, 'Date', border=1, align='C')
    pdf.cell(25, 8, 'Status', border=1, align='C')
    pdf.cell(25, 8, 'Term', border=1, align='C')
    pdf.ln()

    # ✅ Table body
    pdf.set_font('Arial', size=9)
    
    
        
    for student in students:
        name = " ".join(
            part for part in [student.first_name, student.second_name, student.surname] if part
        )
        records = attendance_map.get(student.registration_no, [])
        
        if records:
            for r in records:
                pdf.cell(25, 8, str(student.registration_no), border=1)
                pdf.cell(50, 8, name or "Unknown", border=1)
                pdf.cell(20, 8, str(student.grade), border=1, align='C')
                pdf.cell(20, 8, str(student.stream), border=1, align='C')
                pdf.cell(25, 8, r.date_of_attendance.strftime("%d/%m/%Y"), border=1, align='C')
                pdf.cell(25, 8, str(r.status), border=1, align='C')
                pdf.cell(25, 8, str(r.term), border=1, align='C')
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

def print_grade_stream_attendance_sheet(request):
    from datetime import datetime, timedelta

    school_id = request.session.get('school_id')
    storage = messages.get_messages(request)
    storage.used = True

    grade = request.GET.get('grade', '')
    stream = request.GET.get('stream', '')
    term = request.GET.get('term', '')
    date_filter = request.GET.get('date_filter', 'term')


    # ✅ Fetch all students in the selected grade/stream
    students_qs = StudentInfo.objects.filter(school_id=school_id)
    if grade:
        students_qs = students_qs.filter(grade=grade)
    if stream:
        students_qs = students_qs.filter(stream=stream)

    students = list(students_qs.order_by('registration_no'))

    # ✅ Attendance lookup (only for selected filters)
    attendance_qs = StudentAttendance.objects.filter(school_id=school_id)
    if grade:
        attendance_qs = attendance_qs.filter(registration_no__in = students)
    if stream:
        attendance_qs = attendance_qs.filter(registration_no__in =students) 
    if term:
        attendance_qs = attendance_qs.filter(term=term)

    today = datetime.now().date()
    if date_filter == 'today':
        attendance_qs = attendance_qs.filter(date_of_attendance=today)
    elif date_filter == 'week':
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        attendance_qs = attendance_qs.filter(date_of_attendance__range=[start_week, end_week])

    # Build attendance map → { registration_no: [records] }
    attendance_map = {}
    for att in attendance_qs:
        attendance_map.setdefault(att.registration_no_id, []).append(att)
    print(attendance_map) 
    # ✅ PDF generation
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf_header(request, pdf, 30)

    pdf.set_font('Arial', size=14, style='B')
    pdf.cell(0, 10, 'Attendance Sheet', align='C', ln=True)

    pdf.set_font('Arial', size=10)

    subtitle = f"Grade: {grade or '-'}   Stream: {stream or '-'}   Term: {term or '-'}"
    if date_filter == 'today':
        subtitle += f" (Date: {today.strftime('%d/%m/%Y')})"
    elif date_filter == 'week':
        subtitle += " (This Week)"

    pdf.cell(
        0,
        8,
        subtitle,
        ln=True
    )
    pdf.ln(5)

    # ✅ Table header
    pdf.set_font('Arial', size=9, style='B')
    pdf.cell(25, 8, 'Reg No', border=1, align='C')
    pdf.cell(50, 8, 'Name', border=1, align='C')
    pdf.cell(20, 8, 'Grade', border=1, align='C')
    pdf.cell(20, 8, 'Stream', border=1, align='C')
    pdf.cell(25, 8, 'Date', border=1, align='C')
    pdf.cell(25, 8, 'Status', border=1, align='C')
    pdf.cell(25, 8, 'Term', border=1, align='C')
    pdf.ln()

    # ✅ Table body
    pdf.set_font('Arial', size=9)
    
    for student in students:
        name = " ".join(
            part for part in [student.first_name, student.second_name, student.surname] if part
        )
        records = attendance_map.get(student.registration_no, [])
        
        if records:
            for r in records:
                pdf.cell(25, 8, str(student.registration_no), border=1)
                pdf.cell(50, 8, name or "Unknown", border=1)
                pdf.cell(20, 8, str(student.grade), border=1, align='C')
                pdf.cell(20, 8, str(student.stream), border=1, align='C')
                pdf.cell(25, 8, r.date_of_attendance.strftime("%d/%m/%Y"), border=1, align='C')
                pdf.cell(25, 8, str(r.status), border=1, align='C')
                pdf.cell(25, 8, str(r.term), border=1, align='C')
                pdf.ln()
        else:
            pdf.cell(25, 8, str(student.registration_no), border=1)
            pdf.cell(50, 8, name or "Unknown", border=1)
            pdf.cell(20, 8, str(student.grade), border=1, align='C')
            pdf.cell(20, 8, str(student.stream), border=1, align='C')
            pdf.cell(25, 8, "-", border=1, align='C')
            pdf.cell(25, 8, "-", border=1, align='C')
            pdf.cell(25, 8, str(term or "-"), border=1, align='C')
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
    term = request.GET.get('term')


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

@login_required
def export_strand_marks_pdf(request):
    school_id = request.session.get('school_id')
    grade = request.GET.get("agg_grade")
    stream = request.GET.get("agg_stream")
    term = request.GET.get("agg_term")
    subject = request.GET.get("agg_subject")

    pdf = FPDF()
    pdf.add_page()
    
    # Use reusable header
    pdf_header(request, pdf, 30)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    subject_text = f" - {subject}" if subject else ""
    pdf.cell(0, 10, f"Student Performance Report - {grade} {stream} {term}{subject_text}", ln=1, align="C")
    pdf.ln(5)

    # Table Header
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 10, "Reg No", 1, 0, "C", 1)
    pdf.cell(60, 10, "Name", 1, 0, "C", 1)
    pdf.cell(30, 10, "Avg Score", 1, 0, "C", 1)
    pdf.cell(30, 10, "Avg Level", 1, 0, "C", 1)
    pdf.cell(30, 10, "Subjects", 1, 1, "C", 1)

    # Data
    pdf.set_font("Arial", "", 10)
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
            pdf.cell(40, 10, item['student__registration_no'], 1, 0, "C")
            pdf.cell(60, 10, f"{item['student__first_name']} {item['student__surname']}", 1, 0, "L")
            pdf.cell(30, 10, str(round(item['avg_score'], 2)) if item['avg_score'] else "0", 1, 0, "C")
            pdf.cell(30, 10, str(round(item['avg_level'], 2)) if item['avg_level'] else "0", 1, 0, "C")
            pdf.cell(30, 10, str(item['subjects_count']), 1, 1, "C")

    response = HttpResponse(pdf.output(dest='S').encode('latin1'), content_type='application/pdf')
    filename_subject = f"_{subject}" if subject else ""
    response['Content-Disposition'] = f'attachment; filename="student_performance_{grade}_{stream}_{term}{filename_subject}.pdf"'
    return response
