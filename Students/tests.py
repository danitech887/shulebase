from .models import Users, MasterSchool,StudentInfo
from django.contrib.auth.hashers import make_password
# for school in MasterSchool.objects.all():
#     school_id = school.id
#     school_instance = MasterSchool.objects.get(id=school_id)

#     parents = StudentInfo.objects.filter(school_id=school_id)
#     for parent in parents:
#         type_of_user = "parent"
#         school_name = school_instance.school_name
#         email = parent.email if parent.email else ''

#         Users.objects.create(
#             school=school_instance,
#             username=parent.phone,
#             school_name=school_name,
#             role=type_of_user,
#             password=make_password(str(parent.phone)),
#             email=email,
#             registration_no='',
#         )
#         print(f"Created user for parent: {parent.first_name} in school: {school_name}")

# create superuser 
# Users.objects.create_superuser(
#     school = MasterSchool.objects.first(),
#     username = "shulebase",
#     school_name = "Admin School",
#     role = "admin",
#     password = make_password("daenicel"),
#     email = "",
#     registration_no = "",

# )
# print the exact passowrd..
# user =Users.objects.filter(username = 'shulebase').first()
# print("superuser: shulebase:  ",user.password)
# # unhashed password
# import hashlib
# from django.conf import settings
# def unhash(password):
#     salt = settings.PASSWORD_SALT
#     return hashlib.sha256.new((salt + password).encode('utf-8')).hexdigest()
# print("Unhashed password:", unhash(user.password))

# import mysql.connector

# connection = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="daenicel",    
#     database="shulebase"
# )

# def update_student_info():
#     cursor = connection.cursor()

#     select_query = "SELECT registration_no FROM Students_studentinfo"
#     cursor.execute(select_query)
#     students = cursor.fetchall()

#     no_of_students = len(students)

#     for no in range( no_of_students):
#         parent_no = F"SCH1PT0{no+1}"
#         query = "UPDATE Students_studentinfo SET parent_no = %s WHERE registration_no = %s"
#         cursor.execute(query, (parent_no, students[no][0]))
#         print(f"Updated parent_no for student ID {students[no][0]} to {parent_no}")

#     connection.commit()
#     cursor.close()

# update_student_info()


#  update student info..
names_list = [
    "Liam Smith", "Noah Johnson", "Oliver Williams", "James Brown", "Elijah Jones", 
    "William Garcia", "Henry Miller", "Lucas Davis", "Benjamin Rodriguez", "Theodore Martinez",
    "Mateo Hernandez", "Levi Lopez", "Sebastian Gonzalez", "Daniel Wilson", "Jack Anderson", 
    "Wyatt Thomas", "Alexander Taylor", "Owen Moore", "Asher Jackson", "Samuel Martin",
    "Ethan Lee", "Leo Perez", "Jackson Thompson", "Mason White", "Ezra Harris", 
    "John Sanchez", "Hudson Clark", "Luca Ramirez", "Aiden Lewis", "Joseph Robinson",
    "David Walker", "Jacob Young", "Logan Allen", "Luke King", "Julian Wright", 
    "Gabriel Scott", "Grayson Torres", "Isaac Nguyen", "Anthony Hill", "Josiah Flores",
    "Dylan Green", "Elias Adams", "Caleb Nelson", "Thomas Baker", "Christopher Hall", 
    "Ezekiel Rivera", "Miles Campbell", "Nathan Mitchell", "Isaiah Carter", "Olivia Roberts",
    "Emma Gomez", "Charlotte Phillips", "Amelia Evans", "Sophia Turner", "Mia Diaz", 
    "Isabella Parker", "Ava Cruz", "Evelyn Edwards", "Luna Collins", "Harper Reyes",
    "Sofia Stewart", "Scarlett Morris", "Amara Morales", "Layla Murphy", "Gianna Cook", 
    "Alice Rogers", "Aurora Gutierrez", "Hazel Ortiz", "Isla Morgan", "Elena Cooper",
    "Eliana Peterson", "Eleanor Gray", "Willow Reed", "Ivy Watson", "Grace Brooks", 
    "Chloe Kelly", "Penelope Sanders", "Maya Price", "Aria Bennett", "Lily Wood",
    "Nora Barnes", "Zoe Ross", "Mila Henderson", "Violet Coleman", "Emilia Jenkins", 
    "Stella Perry", "Isabel Powell", "Leilani Long", "Zuri Patterson", "Amina Hughes",
    "Nala Flores", "Kai Washington", "Sloane Butler", "Quinn Simmons", "Remi Foster", 
    "Parker Gonzales", "Jordan Bryant", "Sawyer Alexander", "Ellis Russell", "Rowan Griffin",
    "Skyler Diaz", "Finley Hayes", "Blake Myers", "River Ford", "Charlie Hamilton", 
    "Emerson Graham", "Elliott Sullivan", "Sage Wallace", "Amaris Woods", "Felix West",
    "Soren Cole"
]
import mysql.connector

connection = mysql.connector.connect(
    host="localhost",
    user='root',
    password='daenicel',
    database='shulebase'
)
cursor = connection.cursor()

# # Make sure students list is populated correctly
# # students = [(reg_no1,), (reg_no2,)]
# students = list(StudentInfo.objects.values_list('registration_no',flat=True).distinct())
# if len(students) == len(names_list):
#     for i in range(len(names_list)):
        
#         # Use parameterized queries (%s) to prevent crashes/hacks
#         query = f"UPDATE students_studentinfo SET parent_name = '{names_list[i]}' WHERE registration_no = '{students[i][0]}' "
#         cursor.execute(query)
        
#     connection.commit()
#     print("All updates committed successfully.")
# else:
#     print("NO MATCH: Student count doesn't match names_list count.")

# # Close ONLY once at the very end
# cursor.close()
# connection.close()

from django.db import transaction

with transaction.atomic(): # This makes it fast and safe
    for i, student in enumerate(StudentInfo.objects.all().order_by('registration_no')):
        student.parent_name = names_list[i]
        student.save()