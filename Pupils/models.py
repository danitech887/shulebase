from django.db import models
from django.conf import settings
from datetime import *
from django.utils import timezone

from .utils.manager import SchoolManager

# Utility functions
def current_year_str():
    return str(timezone.now().year)

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

    class Meta:
        db_table = 'MasterSchool'

    def __str__(self):
        return self.school_name


# ---------------- Core Models ----------------
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
    email = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=20)
    age = models.IntegerField(blank=True, null=True)

    objects = SchoolManager()

    class Meta:
        
        db_table = 'studentinfo'
        unique_together = ('school', 'registration_no')

class Fee(models.Model):
    registration_no = models.ForeignKey(StudentInfo,on_delete = models.CASCADE)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="fees")
    mode_of_payment = models.CharField(max_length=10, blank=True, null=True)
    transaction_code = models.CharField(max_length=30, blank=True, null=True)
    amount = models.FloatField(blank=True, null=True)
    date_of_payment = models.DateField(blank=True, null=True)
    time = models.TimeField(blank=True, null=True, auto_now_add=True)
    term = models.CharField(max_length=6, blank=True, null=True)
    year = models.CharField(max_length=10, blank=True, null=True, default=current_year_str)

    objects = SchoolManager()

    class Meta:
        db_table = 'fee'

    def get_pupil_details(self):
        return StudentInfo.objects.filter(registration_no=self.registration_no).first()


class LeaveManagement(models.Model):
    registration_no = models.ForeignKey(StudentInfo,on_delete = models.CASCADE)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="leaves")
    reason = models.CharField(max_length=50, blank=True, null=True)
    other_reason = models.CharField(max_length=50, blank=True, null=True)
    term = models.CharField(max_length=10)
    phone = models.BigIntegerField()
    date_of_leave = models.DateField(blank=True, null=True)
    return_date = models.DateField(blank=True, null=True)
    year = models.CharField(max_length=10, blank=True, null=True, default=current_year_str)
    time = models.CharField(max_length=10, blank=True, null=True, default=current_time_str)

    objects = SchoolManager()

    class Meta:
        db_table = 'leavemanagement'

    def get_pupil_details(self):
        return StudentInfo.objects.filter(registration_no=self.registration_no).first()


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
    year = models.CharField(max_length=10, blank=True, null=True, default=current_year_str)

  

    class Meta:
        db_table = 'marks'


from django.db import models
from django.conf import settings



class Strand(models.Model):
    school = models.ForeignKey("MasterSchool",on_delete = models.CASCADE)
    subject = models.CharField(max_length = 100,default = '')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.name} - {self.name}"
    



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
    year = models.CharField(max_length=10)
    score = models.FloatField()
    remark = models.CharField(max_length = 300,default="Good")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_recorded = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'sub_strand', 'term', 'year')

    def __str__(self):
        return f"{self.student.registration_no} - {self.sub_strand.name} ({self.term})"




class PupilAttendance(models.Model):
    id = models.AutoField(primary_key=True)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="attendance")
    registration_no = models.ForeignKey(StudentInfo,on_delete=models.CASCADE)
    
    date_of_attendance = models.DateField(blank=True, null=True)
    term = models.CharField(max_length=20, blank=True, null=True)
    time = models.CharField(max_length=20, blank=True, null=True, default=current_time_str)
    year = models.CharField(max_length=10, blank=True, null=True, default=current_year_str)
    status = models.CharField(max_length=10, blank=True, null=True)

    objects = SchoolManager()

    class Meta:
        db_table = 'pupilattendance'


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
        db_table = 'teacherinfo'
        unique_together = ('school', 'registration_no')


class TeacherAttendance(models.Model):
    registration_no = models.ForeignKey(TeacherInfo, on_delete=models.CASCADE, db_column='registration_no')
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="teacher_attendance")
    date_of_attendance = models.DateField(blank=True, null=True)
    term = models.CharField(max_length=6, blank=True, null=True)
    year = models.CharField(max_length=10, blank=True, null=True, default=current_year_str)
    status = models.CharField(max_length=7, blank=True, null=True)
    time_in = models.CharField(max_length=30, blank=True, null=True, default=current_time_str)

    objects = SchoolManager()

    class Meta:
        db_table = 'teacherattendance'


class TeachersRole(models.Model):
    registration_no = models.ForeignKey(TeacherInfo, on_delete=models.CASCADE, db_column='registration_no')
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="teacher_roles")
    type_of_teacher = models.CharField(max_length=20, blank=True, null=True)
    grade = models.CharField(max_length=10, blank=True, null=True)
    stream = models.CharField(max_length=10, blank=True, null=True)
    subject = models.CharField(max_length=200, blank=True, null=True)

    objects = SchoolManager()

    class Meta:
        db_table = 'teachersrole'


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
        db_table = 'teachingprogress'


class LoginDetails(models.Model):
    username = models.CharField(unique=True, max_length=20, blank=True, null=True)
    type_of_user = models.CharField(max_length=20)
    teacher_no = models.ForeignKey(TeacherInfo, on_delete=models.CASCADE, db_column='teacher_no')
    email = models.CharField(max_length=50)

    objects = SchoolManager()

    def __str__(self):
        return f"{self.username} ({self.teacher_no})"

    class Meta:
        db_table = 'logindetails'


# ---------------- Other Models ----------------
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field is required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)  # encrypts password
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Only you will be the superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "SystemOwner")  # optional custom role

        return self.create_user(username, email, password, **extra_fields)

class Users(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="users")
    school_name = models.CharField(max_length=100)
    role = models.CharField(max_length=30)
    teacher_no = models.CharField(max_length=30, default="TCH00")
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.username} ({self.role})"


class GradeStream(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="streams")
    grade = models.CharField(max_length=20)
    stream = models.CharField(max_length=20)

    objects = SchoolManager()

    class Meta:
        db_table = 'gradestream'
        unique_together = ('school', 'grade', 'stream')


class Grade(models.Model):
    school = models.ForeignKey(MasterSchool, on_delete=models.CASCADE, related_name="grades")
    name = models.CharField(max_length=50)
    expected_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    term = models.CharField(max_length=10, default='Term 1')

    objects = SchoolManager()

    class Meta:
        db_table = 'grade'
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
        db_table = 'contactmessage'

    def __str__(self):
        return f"{self.name} - {self.subject}"
