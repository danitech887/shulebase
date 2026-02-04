from django.urls import path


from django.conf import settings

from .views.dashboard_views import*
from .views.authentication_view import*
from .views.pupils_views import*
from .views.pdf_views import*
from .views.portal_views import*
from .views.school_views import*
from .views.teachers_views import*
from .views.home_view import home
from .views.contact import contact_view
from .views.student_portal_views import*
from .views.announcement import*
from .views.waiting import waiting_page
from . views.parent_portal import *
from .views.testimonial import testimonials_view
from .views.track_learning import *

 
from django.conf.urls.static import static



urlpatterns = [

    path('home/', home, name='home'),
    path('contact/',contact_view,name = 'contact'),
    path('', dashboard, name='dashboard'),
    path('get-streams/', get_streams, name='get_streams'),
    path('gradestream_config/', gradestream_config, name='gradestream_config'),
    path('manage/',manage_details,name = 'manage_details'),
    path('students/',pupil_list,name = 'pupil_list'),
    path('promote-students/',promote_students,name = 'promote_students'),

    path('grade-stream-delete/<int:id>/',delete_grade_stream,name = 'delete_grade_stream'),
    path('grade-stream-edit/<int:id>/',edit_grade_stream,name = 'edit_grade_stream'),
    path('reg-config/',reg_config,name = 'reg_config'),
 
    path('update/<str:reg_no>/',update_pupil,name = 'update_pupil'),
    path('delete/<str:reg_no>/',delete_pupil,name = 'delete_pupil'),
    path('fee-payment/',fee_payment, name='fee_payment'),
    path('fee-dashboard/', fee_dashboard, name='fee_dashboard'),
    path('fee-verification/',verify_mpesa_payments,name = 'mpesa_payments_verification'),

    path('fee-list/<str:reg_no>/', individual_fee_list, name='individual_fee_list'),
    path('leave_statement/<str:reg_no>/', leave_statement, name='leave_statement'),
    path('receipt/<int:fee_id>/', print_fee_reciept, name='generate_receipt'),
    path('all_receipt/', print_all_fee_reciepts, name='generate_all_receipt'),
    path('leave/', approve_leave, name='leave_home'),
    path('bulk-approval',bulk_leave_approval,name = 'bulk_leave_approval'),
    path('update_leave/<str:reg_no>/',update_leave, name = 'update_leave'),
    path('leave-reciept/pdf/<str:reg_no>/',print_leave_receipt,name = 'leave_reciept'),
    path('leave-reciepts/',print_leave_receipts,name = 'leave_reciepts'),
    path('approve-leave/<int:leave_id>/',leave_application_approval, name = 'approve_leave_request'),
    path('reject-leave/<int:leave_id>/',reject_leave_request, name = 'reject_leave_request'),

    # ajax.. 
    path('ajax/approve/<int:leave_id>/', approve_leave_request_ajax, name='approve_leave_request_ajax'),
    path('ajax/reject/<int:leave_id>/',reject_leave_request_ajax, name='reject_leave_request_ajax'),


    path('academic/', academic_home, name='academic_home'), 
    path('academics-leaning-area-config',manage_learning_areas,name = 'manage_learning_areas'),
    path('academic-dashboard/', academic_dashboard, name='academic_dashboard'),
    path('other_exams/<path:reg_no>/', other_exams, name='other_exams'),
    path('report_forms/', print_report_forms_cbc, name='report_forms'),
    path('report_forms_cbc/', print_report_forms_cbc, name='report_forms_cbc'),
    path('generate_result_papers/', generate_result_papers_cbc, name='generate_result_papers'),
    path('attendance/', pupil_attendance_list, name='pupil_attendance'),
    path('attendance-dashboard/', attendance_dashboard, name='attendance_dashboard'),
    path('attendance/print/', print_attendance_sheet, name='print_attendance_sheet'),
    path('register_teachers/', register_teacher, name='register_teacher'),
    
    path('teachers-dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher-attendance/', teacher_attendance, name='teacher_attendance'),
    path('role-management/', role_management, name='role_management'),
    path('approve-role/', approve_role, name='approve_role'),
    path('delete-teacher/<path:reg_no>/', delete_teacher, name='delete_teacher'),
    path('teacher-reg-config/',teacher_reg_config,name = 'teacher_reg_config'),
    
    path('remove-role/', remove_role, name='remove_role'),

    
    path('teacher-portal/', teacher_portal, name='teacher_portal'),
    path('student-attendance/', attendance, name='attendance'),
    path('student-grade-stream-attendance-sheet',print_grade_stream_attendance_sheet,name = 'grade_stream_attendance'),
    path('record-marks/', record_marks, name='record_marks'),
    path('manage-strands',strand_list,name = "strand_list"),
    path('get-subjects<str:grade>/<str:stream>/', get_subjects, name='get_subjects'),
    path('manage-strands/',strand_add,name = "strand_add"),
    # path('record_scores/<int:strand_id>/',record_scores,name ='record_scores'),
    path('edit_strands<int:pk>/',strand_edit,name = 'strand_edit'),
    path('strand_delete/<int:pk>/', strand_delete, name='strand_delete'),
    path('sub_strands/<int:strand_id>/<str:grade>/<str:stream>/',sub_strands_view, name='sub_strands'),
    path('record_substrand_scores/<int:sub_strand_id>/<str:grade>/<str:stream>/', record_substrand_scores, name='record_substrand_scores'),
    path("edit_substrand/<int:sub_strand_id>/", edit_substrand_view, name="edit_substrand"),
    path('delete_substrand/<int:sub_strand_id>/', delete_substrand, name='delete_substrand'),
    path('reports/substrand/<int:substrand_id>',substrand_report_view, name='substrand_report'),
    path("student-competency/",competency,name = "competency"),
    path('competency/edit/<int:pk>/', edit_competency, name='edit_competency'),
    path('competency/delete/<int:pk>/', delete_competency, name='delete_competency'),
    path('ajax/get-students/', get_students, name='get_students'),
    path('export-strand-marks-pdf/', export_strand_marks_pdf, name='export_strand_marks_pdf'),
    path('export-strand-marks-csv/', export_strand_marks_csv, name='export_strand_marks_csv'),


    path('resource/update/<int:resource_id>/', update_resource, name='update_resource'),
    path('manage-resource/', manage_resources, name='manage_resources'),
    path('resource/delete/<int:resource_id>/', delete_resource, name='delete_resource'),
    path('api/resource-progress/<int:resource_id>/', resource_progress, name='resource_progress'),
    path('api/resource-progress/<int:resource_id>/', get_resource_progress, name='api_resource_progress'),
    path(
        'student-portal/learning-area-breakdown/<str:subject>/',
        view_learning_area_breakdown,
        name='view_learning_area_breakdown'
    ),
 
    # CBC endpoints
    path('cbc_record_substrand/<int:sub_strand_id>/<str:grade>/<str:stream>/', cbc_record_substrand, name='cbc_record_substrand'),
    path('cbc_events/', cbc_events, name='cbc_events'),
    path('cbc_report_student/<path:reg_no>/', cbc_report_student, name='cbc_report_student'),



    path('teaching-progress/',teaching_progress,name = 'teaching_progress'),
    path("account/",teacher_account,name = "teacher_account"),
    path('teachers/announcements/',teacher_announcements, name='teacher_announcements'),



    # Student Portal URLs
    path('student-portal/dashboard/', student_portal_dashboard, name='student_portal_dashboard'),
    path('student-portal/fee-payment/', student_portal_fee_payment, name = 'student_portal_fee_payment'),
    path('student-portal/attendance/', student_portal_attendance, name='student_portal_attendance'),
    path('student-portal/leave-statement/', student_portal_leave_statement, name='student_portal_leave_statement'),
    path('student-portal.leave-application/', student_leave_application, name='student_leave_application'),
    path('student-portal/academic-reports/', student_portal_academics, name='student_portal_academics'),
    path('student-portal/report-card/', print_individual_report_form, name='report_card'),
    path('student-portal/announcements/', students_announcements, name='students_announcements'),
    path('learning-hub/', learning_hub_view, name='learning_hub'),
    path('track-resource-ajax/<int:resource_id>/', track_resource_ajax, name='track_resource_ajax'),
    path('track-resource/<int:resource_id>/', track_and_open_resource, name='track_resource'),
    path('update-video-progress/<int:resource_id>/', update_video_progress, name='update_video_progress'),

    path('api/save-note/<int:resource_id>/', save_student_note, name='save_student_note'),
    
    # URL to retrieve the existing note for a resource
    path('api/get-note/', get_student_note, name='get_student_note'),
    path('api/student-notes/', get_student_notes, name='get_student_notes'),

    # parent portal urls 
    path('parent-portal/dashboard/', parent_portal_dashboard, name='parent_portal_dashboard'),
    path('parent-portal/fee-payment/', parent_student_portal_fee_payment, name = 'parent_student_portal_fee_payment'),
    path('parent-portal/attendance/', parent_portal_student_attendance, name='parent_portal_student_attendance'),
    path('parent-portal/leave-statement/', parent_student_portal_leave_statement, name='parent_student_portal_leave_statement'),
    path('parent-portal/leave-application/', parent_student_portal_leave_application, name='parent_student_portal_leave_application'),
    path('parent-portal/academic/', parent_student_portal_academics, name='parent_student_portal_academics'),
    path('parent-portal/learning-area-breakdown/<path:reg_no>/', parent_student_view_learning_area_breakdown, name='parent_student_view_learning_area_breakdown'),
    path('parent-portal/announcements/', parents_announcements, name='parents_announcements'),
    


    # announcements
    path('announcements/', announcement_list, name='announcement_list'),
    path('announcements/create/', create_announcement, name='create_announcement'),
    path('announcement/edit/<int:id>/',edit_announcement, name='edit_announcement'),
    path('announcement/delete/<int:id>/', delete_announcement, name='delete_announcement'),
 

    path('login/', unified_login, name='login'),
    path('login/student/', student_login, name='student_login'),
    path('login/teacher/', teacher_login, name='teacher_login'),
    path('login/parent/', parent_login, name='parent_login'),
    path('login/admin/', admin_login, name='admin_login'),
    path('reset-password/',reset_password,name = 'reset_password'),
    path('change-password/', change_user_password, name='change_password'),
    path('change_username/',change_username,name = 'change_username'),
    path('logout/student/', student_logout_view, name='student_logout'),
    path('logout/teacher/', teacher_logout_view, name='teacher_logout'),
    path('logout/parent/', parent_logout_view, name='parent_logout'),
    path('logout/admin/', admin_logout_view, name='admin_logout'),

    path('school-registration/', school_registration, name='school_registration'),
    path('update-details/', update_school, name='update_school'),

    path('school-account/', school_account, name='account'),

    path('waiting/', waiting_page, name='waiting_page'),

    path('reviews/',testimonials_view,name  ='reviews'),
    
] + static(settings.MEDIA_URL,document_root = settings.MEDIA_ROOT)
