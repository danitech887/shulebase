from django.db import models
from django.conf import settings
from django.utils import timezone

from .utils.manager import SchoolManager
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# Utility functions
def current_time_str():
    return timezone.now().strftime("%H:%M:%S")


# ---------------- Master School ----------------
class MasterSchool(models.Model):
    school_name = models.CharField(max_length=100)
    po_box = models.CharField(max_length=50)
    address = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    email_address = models.EmailField()

    logo_path = models.ImageField(upload_to='school_logos/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    motto = models.CharField(max_length=255, blank=True, null=True)
    vision = models.TextField(blank=True, null=True)
    status_choices = ['Approved', 'Pending', 'Rejected']
    status = models.CharField(max_length=20, choices=[(status, status) for status in status_choices], default='Pending')

    class Meta:
        verbose_name = "Master School"

    def __str__(self):
        return self.school_name


# ---------------- Core Models ----------------

class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field is required")
        
        email = self.normalize_email(email)
        
        # --- FIX: Convert school ID to School Instance ---
        school_val = extra_fields.get('school')
        if school_val and not isinstance(school_val, MasterSchool):
            try:
                # This converts the "1" you typed in the terminal into the actual School object
                extra_fields['school'] = MasterSchool.objects.get(pk=school_val)
            except MasterSchool.DoesNotExist:
                raise ValueError(f"MasterSchool with id {school_val} does not exist.")
        # ------------------------------------------------
        
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        
        # Ensure role is set for superuser
        if "role" not in extra_fields:
            extra_fields["role"] = "SystemOwner"

        return self.create_user(username, email, password, **extra_fields)
class Users(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="users")
    school_name = models.CharField(max_length=100)
    role = models.CharField(max_length=30)
    registration_no = models.CharField(max_length=30, default="") 
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "role", "school"]

    objects = UserManager()

    class Meta:
        # Let Django manage the table name 'students_users'
        pass

    def __str__(self):
        return f"{self.username} ({self.role})"


class StudentInfo(models.Model):
    registration_no = models.CharField(primary_key=True, max_length=20)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="students")
    first_name = models.CharField(max_length=20)
    second_name = models.CharField(max_length=20)
    surname = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    date_of_registration = models.DateField(blank=True, null=True)
    parent_name = models.CharField(max_length=20, blank=True, null=True)
    grade = models.CharField(max_length=10)
    stream = models.CharField(max_length=10)
    phone = models.BigIntegerField()
    email = models.EmailField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=20)

    parent_portal_user = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)

    objects = SchoolManager()

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


    class Meta:
        verbose_name = "Student Information"
        unique_together = ('school', 'registration_no')

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password

@receiver(post_save, sender=StudentInfo)
def manage_parent_account(sender, instance, created, **kwargs):
    if created:
        # Step A: Find or Create the Parent User
        parent_user, p_created = Users.objects.get_or_create(
            username=instance.phone,
            defaults={
                'role': 'Parent', 
                'password': make_password(str(instance.phone)),
                'school': instance.school
            }
        )
        
        # Step B: Link the parent to this student
        # We use .update() here to avoid triggering this signal again (infinite loop)
        StudentInfo.objects.filter(registration_no=instance.registration_no).update(parent_portal_user=parent_user)
class Fee(models.Model):
    registration_no = models.ForeignKey(StudentInfo,on_delete = models.CASCADE)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="fees")
    mode_of_payment = models.CharField(max_length=10, blank=True, null=True)
    transaction_code = models.CharField(max_length=30, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    date_of_payment = models.DateField(blank=True, null=True,default = timezone.now())
    time = models.TimeField(blank=True, null=True, auto_now_add=True)
    term = models.CharField(max_length=6, blank=True, null=True)    
    year = models.IntegerField(blank=True, null=True, default=timezone.now().year)

    status_choices = ['Pending','Confirmed']
    status = models.CharField(max_length=10, choices=[(status, status) for status in status_choices], default='Pending')
    objects = SchoolManager()

    class Meta:
        # Let Django manage the table name 'students_fee'
        pass

class LeaveManagement(models.Model):
    registration_no = models.ForeignKey(StudentInfo,on_delete = models.CASCADE)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="leaves")
    reason = models.CharField(max_length=50, blank=True, null=True)
    other_reason = models.CharField(max_length=50, blank=True, null=True)
    term = models.CharField(max_length=10)
    status = models.CharField(max_length=10, blank=True, null=True)
    phone = models.BigIntegerField()
    date_of_leave = models.DateField(blank=True, null=True)
    return_date = models.DateField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True, default=timezone.now().year)
    time = models.TimeField(blank=True, null=True, default=timezone.now)

    objects = SchoolManager()

    class Meta:
        # Let Django manage the table name 'students_leavemanagement'
        pass

class Marks(models.Model):
    id = models.AutoField(primary_key=True)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="marks")
    registration_no = models.ForeignKey(StudentInfo,on_delete = models.CASCADE)
    
    mathematics = models.IntegerField(blank=True, null=True)
    english = models.IntegerField(blank=True, null=True)
    kiswahili = models.IntegerField(blank=True, null=True)
    science_technology = models.IntegerField(blank=True, null=True)
    social_studies = models.IntegerField(blank=True, null=True)
    cre = models.IntegerField(blank=True, null=True)
    sst_cre = models.IntegerField(blank=True, null=True)
    agri_nutrition = models.IntegerField(blank=True, null=True)
    creative_arts = models.IntegerField(blank=True, null=True)
    pretech_bs_computer = models.IntegerField(blank=True, null=True)
    integrated_science = models.IntegerField(blank=True, null=True)
    environmental_activities = models.IntegerField(blank=True, null=True)
    integrated_creative = models.IntegerField(blank=True, null=True)
    total_marks = models.IntegerField(blank=True, null=True)
    mean_marks = models.FloatField(blank=True, null=True)
    term = models.CharField(max_length=10, blank=True, null=True)
    type_of_exam = models.CharField(max_length=10, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True, default=timezone.now().year)

  

    class Meta:
        # Let Django manage the table name 'students_marks'
        pass

class LearningArea(models.Model):
    # The name of the subject (e.g., Mathematics, English, Home Science)
    name = models.CharField(max_length=100)
    
    # The code used for reports or IDs (e.g., MATH, ENG)
    
    # Link to the Grade level (Assuming you have a Grade model)
    # If you don't have a Grade model, use a CharField with choices
    grade_level = models.CharField(max_length=20) 

    # Track which school this belongs to in a multi-tenant system
    school = models.ForeignKey("MasterSchool",on_delete = models.CASCADE)

    # Optional: Category for grouping (e.g., Sciences, Humanities)
    category = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        # Prevent adding the same subject to the same grade twice
        unique_together = ('name', 'grade_level', 'school_id')

    def __str__(self):
        return f"{self.name} - {self.grade}"

class Strand(models.Model):
    school = models.ForeignKey("MasterSchool",on_delete = models.CASCADE)
    grade = models.CharField(max_length = 10,default = '')
    stream = models.CharField(max_length = 10,default = '')
    subject = models.CharField(max_length = 100,default = '')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.name}"

class SubStrand(models.Model):
    strand = models.ForeignKey(Strand, on_delete=models.CASCADE, related_name='sub_strands')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.strand.name} - {self.name}"

class SubStrandMark(models.Model):
    student = models.ForeignKey('StudentInfo', on_delete=models.CASCADE)
    sub_strand = models.ForeignKey(SubStrand, on_delete=models.CASCADE)
    term = models.CharField(max_length=20)
    year = models.IntegerField()
    raw_score = models.FloatField(default=0)
    score = models.FloatField()
    remark = models.CharField(max_length = 300,default="Good")
    level = models.PositiveSmallIntegerField(choices=[(1,'Level 1'),(2,'Level 2'),(3,'Level 3')],default=1) 
    assessment_type = models.CharField(max_length=100,default='SBA-Written') 
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_recorded = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'sub_strand', 'term', 'year')

    def __str__(self):
        return f"{self.student.registration_no} - {self.sub_strand.name} ({self.term})"


# --------------- CBC Assessment Models (non-breaking) ---------------
class AssessmentEvent(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name='cbc_events')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date = models.DateField(default=timezone.now)
    term = models.CharField(max_length=20)
    year = models.IntegerField(default=timezone.now().year)
    grade = models.CharField(max_length=20)
    stream = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=100)
    strand = models.ForeignKey(Strand, on_delete=models.SET_NULL, null=True, blank=True)
    sub_strand = models.ForeignKey(SubStrand, on_delete=models.SET_NULL, null=True, blank=True)
    activity = models.CharField(max_length=255, help_text='Assessment activity/task')
    method = models.CharField(max_length=100, blank=True, null=True, help_text='e.g., Observation, Project, Checklist')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.subject} - {self.activity} ({self.term} {self.year})"


class OutcomeDescriptor(models.Model):
    sub_strand = models.ForeignKey(SubStrand, on_delete=models.CASCADE, related_name='cbc_descriptors')
    level = models.PositiveSmallIntegerField(choices=[(1,'Level 1'),(2,'Level 2'),(3,'Level 3'),(4,'Level 4')])
    descriptor = models.TextField()

    class Meta:
        unique_together = ('sub_strand', 'level')
        ordering = ['sub_strand_id', 'level']

    def __str__(self):
        return f"{self.sub_strand.name} - L{self.level}"


class Observation(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name='cbc_observations')
    student = models.ForeignKey(StudentInfo, on_delete=models.CASCADE, related_name='cbc_observations')
    sub_strand = models.ForeignKey(SubStrand, on_delete=models.CASCADE, related_name='cbc_observations')
    event = models.ForeignKey(AssessmentEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name='observations')

    term = models.CharField(max_length=20)
    year = models.IntegerField(default=timezone.now().year)
    level = models.PositiveSmallIntegerField(choices=[(1,'Level 1'),(2,'Level 2'),(3,'Level 3'),(4,'Level 4')])
    comment = models.CharField(max_length=300, blank=True, null=True)
    evidence_link = models.URLField(blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['student','sub_strand','term','year']),
        ]
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.student.registration_no} - {self.sub_strand.name} L{self.level}"


class LearnerCompetency(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name='cbc_competencies')
    student = models.ForeignKey(StudentInfo, on_delete=models.CASCADE, related_name='cbc_competencies')
    grade = models.CharField(max_length=20,default='')
    stream = models.CharField(max_length=20,default='')
    subject = models.CharField(max_length=100,default='')
    term = models.CharField(max_length=20)
    year = models.IntegerField(default=timezone.now().year)

    competency = models.CharField(max_length=100)  # e.g., Communication, Critical thinking...
    level = models.PositiveSmallIntegerField(choices=[(1,'Level 1'),(2,'Level 2'),(3,'Level 3'),(4,'Level 4')])
    comment = models.CharField(max_length=300, blank=True, null=True)

    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student','term','year','competency')
        ordering = ['student_id','competency']

    def __str__(self):
        return f"{self.student.registration_no} - {self.competency} L{self.level}"



class StudentAttendance(models.Model):
    id = models.AutoField(primary_key=True)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="attendance")
    registration_no = models.ForeignKey(StudentInfo,on_delete=models.CASCADE)
    
    date_of_attendance = models.DateField(blank=True, null=True)
    term = models.CharField(max_length=20, blank=True, null=True)
    time = models.TimeField(blank=True, null=True, default=timezone.now)
    year = models.IntegerField(blank=True, null=True, default=timezone.now().year)
    status = models.CharField(max_length=10, blank=True, null=True)

    objects = SchoolManager()

    class Meta:
        # Let Django manage the table name 'students_pupilattendance'
        pass

class TeacherInfo(models.Model):
    registration_no = models.CharField(max_length=20, primary_key=True)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="teachers")
    first_name = models.CharField(max_length=30)
    second_name = models.CharField(max_length=30, blank=True)
    surname = models.CharField(max_length=30)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    date_of_registration = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.CharField(max_length=100, blank=True)

    objects = SchoolManager()

    def __str__(self):
        return f"{self.first_name} {self.second_name} {self.surname} ({self.registration_no})"

    class Meta:
        verbose_name = "Teacher Information"
        unique_together = ('school', 'registration_no')


class TeacherAttendance(models.Model):
    registration_no = models.ForeignKey(TeacherInfo, on_delete=models.CASCADE, db_column='registration_no')
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="teacher_attendance")
    date_of_attendance = models.DateField(blank=True, null=True)
    term = models.CharField(max_length=6, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True, default=timezone.now().year)
    status = models.CharField(max_length=7, blank=True, null=True)
    time_in = models.TimeField(blank=True, null=True, default=timezone.now)

    objects = SchoolManager()

    class Meta:
        # Let Django manage the table name 'students_teacherattendance'
        pass

class TeachersRole(models.Model):
    registration_no = models.ForeignKey(TeacherInfo, on_delete=models.CASCADE, db_column='registration_no')
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="teacher_roles")
    type_of_teacher = models.CharField(max_length=20, blank=True, null=True)
    grade = models.CharField(max_length=10, blank=True, null=True)
    stream = models.CharField(max_length=10, blank=True, null=True)
    subject = models.CharField(max_length=200, blank=True, null=True)

    objects = SchoolManager()

    class Meta:
        # Let Django manage the table name 'students_teachersrole'
        pass

class TeachingProgress(models.Model):
    registration_no = models.ForeignKey(TeacherInfo, on_delete=models.CASCADE, db_column='registration_no')
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="teaching_progress")
    grade = models.CharField(max_length=20)
    stream = models.CharField(max_length=20)
    subject = models.CharField(max_length=355, blank=True, null=True)
    no_of_topics = models.IntegerField(blank=True, null=True)
    topic = models.CharField(max_length=500, blank=True, null=True)
    sub_topic = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=9, blank=True, null=True)
    date_of_teaching = models.DateTimeField(blank=True, null=True)
    date_finished = models.DateField(blank=True, null=True)

    objects = SchoolManager()

    class Meta:
        # Let Django manage the table name 'students_teachingprogress'
        pass

class LoginDetails(models.Model):
    username = models.CharField(unique=True, max_length=20, blank=True, null=True)
    type_of_user = models.CharField(max_length=20)
    teacher_no = models.ForeignKey(TeacherInfo, on_delete=models.CASCADE, db_column='teacher_no')
    email = models.CharField(max_length=50)

    objects = SchoolManager()

    def __str__(self):
        return f"{self.username} ({self.teacher_no})"

    class Meta:
        # This model appears to be legacy and may conflict with the custom Users model.
        # Consider removing it if it's no longer in use.
        db_table = 'logindetails'


class GradeStream(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="streams")
    grade = models.CharField(max_length=20)
    stream = models.CharField(max_length=20)

    objects = SchoolManager()

    class Meta:
        unique_together = ('school', 'grade', 'stream')
        verbose_name_plural = "Grade Streams"

class Grade(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="grades")
    name = models.CharField(max_length=50)
    expected_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    term = models.CharField(max_length=10, default='Term 1')

    objects = SchoolManager()

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return self.name


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, default='')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contact Message"

    def __str__(self):
        return f"{self.name} - {self.subject}"


# announcement model
class Announcement(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_audience = models.CharField(max_length=50, choices=[('All', 'All'), ('Students', 'Students'), ('Teachers', 'Teachers')], default='All')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Announcement"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d')})"


from django.db import models

class Testimonial(models.Model):
    USER_TYPES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('parent', 'Parent'),
        ('Admin', 'School Admin'),
    )

    full_name = models.CharField(max_length=100)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="reviews")
    location = models.CharField(max_length=100, help_text="e.g. Nairobi, Kenya")
    content = models.TextField(verbose_name="Review Message")
    rating = models.IntegerField(default=5)  # Scale of 1-5
    is_approved = models.BooleanField(default=False)  # Admin must approve
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.school}"
    





from django.db import models
from django.contrib.auth.models import User

class Resource(models.Model):
    TYPES = (('video', 'Video'), ('book', 'e-Book'))
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE,default=1)
    
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=100)
    grade = models.CharField(max_length=10)  # e.g., 7 for Grade 7
    stream = models.CharField(max_length=19,default='A')
    term = models.CharField(max_length=10,choices=[('Term 1','Term 1'),('Term 2','Term 2'),('Term 3','Term 3')],default='Term 3')
    year = models.IntegerField(default=timezone.now().year)
    resource_type = models.CharField(max_length=10, choices=TYPES)
    url_or_file = models.CharField(max_length=500, help_text="YouTube ID or File URL")
    thumbnail = models.ImageField(upload_to='thumbs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
class StudentNote(models.Model):
    student = models.ForeignKey(StudentInfo, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'resource')
class LearningLog(models.Model):
    student = models.ForeignKey(StudentInfo, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    watched_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False) # For tracking if they finished it

    class Meta:
        unique_together = ('student', 'resource') # Prevents double counting the same resource
