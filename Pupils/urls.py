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


from django.conf.urls.static import static



urlpatterns = [

    path('home/', home, name='home'),
    path('contact/',contact_view,name = 'contact'),
    path('', dashboard, name='dashboard'),
    path('get-streams/', get_streams, name='get_streams'),
    path('gradestream_config/', gradestream_config, name='gradestream_config'),
    path('manage/',manage_details,name = 'manage_details'),
    path('pupils/',pupil_list,name = 'pupil_list'),
    path('promote-students/',promote_students,name = 'promote_students'),
 
    path('update/<str:reg_no>/',update_pupil,name = 'update_pupil'),
    path('delete/<str:reg_no>/',delete_pupil,name = 'delete_pupil'),
    path('fee-payment/',fee_payment, name='fee_payment'),
    path('fee-dashboard/', fee_dashboard, name='fee_dashboard'),

    path('fee-list/<str:reg_no>/', individual_fee_list, name='individual_fee_list'),
    path('leave_statement/<str:reg_no>/', leave_statement, name='leave_statement'),
    path('receipt/<int:fee_id>/', print_fee_reciept, name='generate_receipt'),
    path('all_receipt/', print_all_fee_reciepts, name='generate_all_receipt'),
    path('leave/', approve_leave, name='leave_home'),
    path('bulk-approval',bulk_leave_approval,name = 'bulk_leave_approval'),
    path('update_leave/<str:reg_no>/',update_leave, name = 'update_leave'),
    path('leave-reciept/pdf/<str:reg_no>/',print_leave_receipt,name = 'leave_reciept'),
    path('leave-reciepts/',print_leave_receipts,name = 'leave_reciepts'),
    path('academic/', academic_home, name='academic_home'),
    path('academic-dashboard/', academic_dashboard, name='academic_dashboard'),
    path('other_exams/<str:reg_no>/', other_exams, name='other_exams'),
    path('report_forms/', print_report_forms, name='report_forms'),
    path('generate_result_papers/', generate_result_papers, name='generate_result_papers'),
    path('attendance/', pupil_attendance_list, name='pupil_attendance'),
    path('attendance-dashboard/', attendance_dashboard, name='attendance_dashboard'),
    path('attendance/print/', print_attendance_sheet, name='print_attendance_sheet'),
    path('register_teachers/', register_teacher, name='register_teacher'),
    
    path('teachers-dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher-attendance/', teacher_attendance, name='teacher_attendance'),
    path('role-management/', role_management, name='role_management'),
    path('approve-role/', approve_role, name='approve_role'),
    path('delete-teacher/<str:reg_no>/', delete_teacher, name='delete_teacher'),
    
    path('remove-role/', remove_role, name='remove_role'),

    
    path('teacher-portal/', teacher_portal, name='teacher_portal'),
    path('student-attendance/', attendance, name='attendance'),
    path('record-marks/', record_marks, name='record_marks'),
    path('manage-strands',strand_list,name = "strand_list"),
    path('manage-strands/',strand_add,name = "strand_add"),
    # path('record_scores/<int:strand_id>/',record_scores,name ='record_scores'),
    path('edit_strands<int:pk>/',strand_edit,name = 'strand_edit'),
    path('sub_strands/<int:strand_id>/',sub_strands_view, name='sub_strands'),
    path('record_substrand_scores/<int:sub_strand_id>/',record_substrand_scores, name='record_substrand_scores'),

    path('teaching-progress',teaching_progress,name = 'teaching_progress'),
    path("account",teacher_account,name = "teacher_account"),


    path('login/', unified_login, name='login'),
    path('reset-password/',reset_password,name = 'reset_password'),
    path('change-password/', change_user_password, name='change_password'),
    path('logout/', logout_view, name='logout'),

    path('school-registration/', school_registration, name='school_registration'),
    path('update-details/', update_school, name='update_school'),

    path('school-account/', school_account, name='account'),
    
] + static(settings.MEDIA_URL,document_root = settings.MEDIA_ROOT)
