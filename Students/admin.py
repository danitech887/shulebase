from django.contrib import admin
from .models import *

from django.contrib import admin

# Change the text on the Login screen and the top of every admin page
admin.site.site_header = "ShuleBase Administration Panel"

# Change the text in the Browser Tab (Title)
admin.site.site_title = "ShuleBase Admin Portal"

# Change the text on the Admin Index page (the "Welcome" section)
admin.site.index_title = "Welcome to ShuleBase Management"

@admin.register(MasterSchool)
class SchoolAdmin(admin.ModelAdmin):
    # What you see in the table list
    list_display = ('school_name', 'email_address', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('school_name', 'email_address')
    
    # Custom Actions for Bulk Approval
    actions = ['approve_schools', 'reject_schools']

    @admin.action(description='Approve selected schools')
    def approve_schools(self, request, queryset):
        count = queryset.update(status='Approved')
        self.message_user(request, f"{count} schools were successfully approved.")

    @admin.action(description='Reject selected schools')
    def reject_schools(self, request, queryset):
        queryset.update(status='Rejected')

@admin.register(Users)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'school', 'is_active')
    list_filter = ('role', 'is_active', 'school')
    search_fields = ('username', 'email')


@admin.register(StudentInfo)
class Students(admin.ModelAdmin):
    list_display = ('registration_no', 'surname', 'first_name','grade', 'stream', 'school')
    list_filter = ('registration_no', 'stream', 'school')
    search_fields = ('registration_no', 'surname', 'first_name')

@admin.register(TeacherInfo)
class Teachers(admin.ModelAdmin):
    list_display = ('registration_no', 'surname', 'first_name','address', 'school')
    list_filter = ('registration_no', 'address', 'school')
    search_fields = ('registration_no', 'surname', 'first_name')

@admin.register(Fee)
class Fees(admin.ModelAdmin):
    list_display = ('registration_no_id', 'amount', 'date_of_payment', 'school')
    list_filter = ('date_of_payment', 'school')
    search_fields = ('registration_no_id',)

@admin.register(LeaveManagement)
class LeaveM(admin.ModelAdmin):
    list_display = ('registration_no', 'reason', 'date_of_leave', 'return_date', 'status', 'school')
    list_filter = ('reason', 'status', 'school')
    search_fields = ('registration_no', 'reason')

@admin.register(StudentAttendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'date_of_attendance', 'status', 'school')
    list_filter = ('date_of_attendance', 'status', 'school')
    search_fields = ('registration_no',)

@admin.register(TeacherAttendance)
class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'date_of_attendance', 'status', 'school')
    list_filter = ('date_of_attendance', 'status', 'school')
    search_fields = ('registration_no',)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_audience', 'created_at', 'school')
    list_filter = ('target_audience', 'created_at', 'school')
    search_fields = ('title', 'content')


@admin.register(Strand)
class StrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade', 'school')
    list_filter = ('grade', 'school')
    search_fields = ('name',)


@admin.register(TeachersRole)
class TeachersRoleAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'type_of_teacher', 'school')
    list_filter = ('type_of_teacher', 'school')
    search_fields = ('teachers__surname', 'teachers__first_name') 


@admin.register(Testimonial)
class TestimonialAprroval(admin.ModelAdmin):
    list_display = ('user_type','school','content')
    list_filter = ('is_approved','content')
    search_fields = ('school','user_type')

    actions = ['approve_schools', 'reject_schools']

    @admin.action(description='Approve selected reviews')
    def approve_schools(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f"{count} schools were successfully approved.")

    @admin.action(description='Reject selected schools')
    def reject_schools(self, request, queryset):
        queryset.update(is_approved=False)


from django.contrib import admin
from .models import Resource, LearningLog

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    # This controls the columns shown in the list view
    list_display = ('title', 'subject', 'grade', 'resource_type', 'created_at')
    
    # Adds a sidebar filter for easy navigation
    list_filter = ('subject', 'grade', 'resource_type')
    
    # Allows you to search by title or subject
    search_fields = ('title', 'subject')
    
    # Groups fields logically when editing
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subject', 'grade', 'resource_type')
        }),
        ('Content & Media', {
            'fields': ('url_or_file', 'thumbnail'),
            'description': 'Enter the YouTube Video ID or the URL to the hosted PDF.'
        }),
    )

@admin.register(LearningLog)
class LearningLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'resource', 'watched_at', 'completed')
    list_filter = ('completed', 'watched_at', 'resource__subject')
    search_fields = ('student__username', 'resource__title')
    
    # Makes the log read-only so admins don't accidentally "fake" student progress
    readonly_fields = ('watched_at',)

@admin.register(RegConfig)
class RegConfigAdmin(admin.ModelAdmin):
    list_display = ('school', 'reg_format', 'target_type')

@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'term', 'year', 'total_marks', 'mean_marks', 'school')
    list_filter = ('term', 'year', 'school')
    search_fields = ('registration_no__registration_no',)

@admin.register(LearningArea)
class LearningAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_level', 'school')
    list_filter = ('grade_level', 'school')
    search_fields = ('name',)

@admin.register(SubStrand)
class SubStrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'strand', 'created_by')
    list_filter = ('strand__subject', 'strand__grade')
    search_fields = ('name', 'strand__name')

@admin.register(SubStrandMark)
class SubStrandMarkAdmin(admin.ModelAdmin):
    list_display = ('student', 'sub_strand', 'score', 'level', 'term', 'year')
    list_filter = ('term', 'year', 'level')
    search_fields = ('student__registration_no', 'sub_strand__name')

@admin.register(AssessmentEvent)
class AssessmentEventAdmin(admin.ModelAdmin):
    list_display = ('activity', 'subject', 'grade', 'term', 'year', 'date', 'school')
    list_filter = ('term', 'year', 'grade', 'school')
    search_fields = ('activity', 'subject')

@admin.register(OutcomeDescriptor)
class OutcomeDescriptorAdmin(admin.ModelAdmin):
    list_display = ('sub_strand', 'level', 'descriptor')
    list_filter = ('level',)
    search_fields = ('sub_strand__name', 'descriptor')

@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sub_strand', 'level', 'term', 'year', 'school')
    list_filter = ('term', 'year', 'level', 'school')
    search_fields = ('student__registration_no', 'sub_strand__name')

@admin.register(LearnerCompetency)
class LearnerCompetencyAdmin(admin.ModelAdmin):
    list_display = ('student', 'competency', 'level', 'term', 'year', 'school')
    list_filter = ('term', 'year', 'level', 'school')
    search_fields = ('student__registration_no', 'competency')

@admin.register(TeachingProgress)
class TeachingProgressAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'subject', 'topic', 'status', 'date_of_teaching', 'school')
    list_filter = ('status', 'school', 'grade')
    search_fields = ('topic', 'sub_topic')

@admin.register(LoginDetails)
class LoginDetailsAdmin(admin.ModelAdmin):
    list_display = ('username', 'type_of_user', 'teacher_no', 'email')
    search_fields = ('username', 'email')

@admin.register(GradeStream)
class GradeStreamAdmin(admin.ModelAdmin):
    list_display = ('grade', 'stream', 'school')
    list_filter = ('grade', 'school')
    search_fields = ('grade', 'stream')

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'expected_fee', 'term', 'school')
    list_filter = ('term', 'school')
    search_fields = ('name',)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)

@admin.register(StudentNote)
class StudentNoteAdmin(admin.ModelAdmin):
    list_display = ('student', 'resource', 'updated_at')
    search_fields = ('student__registration_no', 'resource__title')