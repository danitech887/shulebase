from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from ..models import MasterSchool,Users

from django.shortcuts import render, redirect
from ..forms import SchoolRegistrationForm
from django.db import connection


import pymysql
import os

import os
import pymysql

def create_school_db_and_user(db_name, db_user, db_password):
    admin_user = os.environ.get('MYSQL_ADMIN_USER', 'root')
    admin_pass = os.environ.get('MYSQL_ADMIN_PASS', 'daenicel')

    # 1. Connect as admin and create DB and user
    admin_conn = pymysql.connect(
        host='localhost',
        user=admin_user,
        password=admin_pass,
        database='mysql',
        autocommit=True
    )
    admin_cursor = admin_conn.cursor()
    try:
        admin_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        admin_cursor.execute(
            "CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s;",
            (db_user, db_password)
        )
        admin_cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%';")
        admin_cursor.execute("FLUSH PRIVILEGES;")
        admin_conn.commit()
    finally:
        admin_cursor.close()
        admin_conn.close()
    # Use Django migrations to create schema; stop here.
    return

    # 2. Connect as the new db user to the new DB and create tables
    tables = [
        """CREATE TABLE IF NOT EXISTS studentinfo (
            registration_no VARCHAR(20) PRIMARY KEY,
            first_name VARCHAR(20) NOT NULL,
            second_name VARCHAR(20) NOT NULL,
            surname VARCHAR(20) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            date_of_birth DATE NOT NULL,
            date_of_registration DATE,
            parent_name VARCHAR(20),
            grade VARCHAR(10) NOT NULL,
            stream VARCHAR(10) NOT NULL,
            phone BIGINT NOT NULL,
            email VARCHAR(50),
            address VARCHAR(20) NOT NULL,
            age INTEGER
        );""",
        """CREATE TABLE IF NOT EXISTS fee (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(10) NOT NULL,
            mode_of_payment VARCHAR(10),
            transaction_code VARCHAR(30),
            amount FLOAT,
            date_of_payment DATE,
            time VARCHAR(20),
            term VARCHAR(6),
            year VARCHAR(10)
        );""",
        """CREATE TABLE IF NOT EXISTS leavemanagement (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(10) NOT NULL,
            reason VARCHAR(50),
            other_reason VARCHAR(50),
            term VARCHAR(10),
            phone BIGINT NOT NULL,
            date_of_leave DATE,
            year VARCHAR(10),
            time VARCHAR(10),
            return_date DATE
        );""",
        """CREATE TABLE IF NOT EXISTS marks (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(10) NOT NULL,
            grade VARCHAR(10) NOT NULL,
            stream VARCHAR(10) NOT NULL,
            mathematics INTEGER,
            english INTEGER,
            kiswahili INTEGER,
            science_technology INTEGER,
            social_studies INTEGER,
            cre INTEGER,
            sst_cre INTEGER,
            agri_nutrition INTEGER,
            creative_arts INTEGER,
            pretech_bs_computer INTEGER,
            integrated_science INTEGER,
            environmental_activities INTEGER,
            integrated_creative INTEGER,
            total_marks INTEGER,
            mean_marks FLOAT,
            term VARCHAR(10),
            type_of_exam VARCHAR(10),
            year VARCHAR(10)
        );""",
        """CREATE TABLE IF NOT EXISTS pupilattendance (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(20) NOT NULL,
            grade VARCHAR(10) NOT NULL,
            stream VARCHAR(10) NOT NULL,
            date_of_attendance DATE,
            term VARCHAR(20),
            time VARCHAR(20),
            year VARCHAR(10),
            status VARCHAR(10)
        );""",
        """CREATE TABLE IF NOT EXISTS teacherinfo (
            registration_no VARCHAR(20) PRIMARY KEY,
            first_name VARCHAR(30) NOT NULL,
            second_name VARCHAR(30),
            surname VARCHAR(30) NOT NULL,
            gender VARCHAR(10) CHECK (gender IN ('Male', 'Female')) NOT NULL,
            date_of_registration TIMESTAMP NOT NULL,
            phone VARCHAR(20) NOT NULL,
            email VARCHAR(254) NOT NULL,
            address VARCHAR(100)
        );""",
        """CREATE TABLE IF NOT EXISTS teacherattendance (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(20) NOT NULL,
            date_of_attendance VARCHAR(10),
            term VARCHAR(6),
            year VARCHAR(10),
            status VARCHAR(7),
            time_in VARCHAR(30),
            CONSTRAINT teacherattendance_registration_no_fk FOREIGN KEY (registration_no) REFERENCES teacherinfo(registration_no)
        );""",
        """CREATE TABLE IF NOT EXISTS teachersrole (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(20) NOT NULL,
            type_of_teacher VARCHAR(20),
            grade VARCHAR(10),
            stream VARCHAR(10),
            subject VARCHAR(200),
            CONSTRAINT teachersrole_registration_no_fk FOREIGN KEY (registration_no) REFERENCES teacherinfo(registration_no)
        );""",
        """CREATE TABLE IF NOT EXISTS teachingprogress (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(20) NOT NULL,
            grade VARCHAR(20) NOT NULL,
            stream VARCHAR(20) NOT NULL,
            subject VARCHAR(355),
            no_of_topics INTEGER,
            topic VARCHAR(500),
            sub_topic VARCHAR(500),
            status VARCHAR(9),
            date_of_teaching TIMESTAMP,
            date_finished DATE,
            CONSTRAINT teachingprogress_registration_no_fk FOREIGN KEY (registration_no) REFERENCES teacherinfo(registration_no)
        );""",
        """CREATE TABLE IF NOT EXISTS logindetails (
            id SERIAL PRIMARY KEY,
            username VARCHAR(20) UNIQUE,
            type_of_user VARCHAR(20) NOT NULL,
            teacher_no VARCHAR(20) NOT NULL,
            email VARCHAR(50) NOT NULL,
            CONSTRAINT logindetails_teacher_no_fk FOREIGN KEY (teacher_no) REFERENCES teacherinfo(registration_no)
        );""",
        """
            CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            school_name VARCHAR(100) NOT NULL,
            role VARCHAR(30) NOT NULL,
            password VARCHAR(255) NOT NULL,
            email VARCHAR(254),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]

    db_conn = pymysql.connect(
        host='localhost',
        user=db_user,
        password=db_password,
        database=db_name,
        autocommit=True
    )
    db_cursor = db_conn.cursor()
    try:
        for table_sql in tables:
            db_cursor.execute(table_sql)
        db_conn.commit()
    finally:
        db_cursor.close()
        db_conn.close()

def change_db_password(db_user, new_password):
    admin_user = os.environ.get('MYSQL_ADMIN_USER', 'root')
    admin_pass = os.environ.get('MYSQL_ADMIN_PASS', 'daenicel')

    # 1. Connect as admin and create DB and user
    admin_conn = pymysql.connect(
        host='localhost',
        user=admin_user,
        password=admin_pass,
        database='mysql',
        autocommit=True
    )
    admin_cursor = admin_conn.cursor()
    try:
        admin_cursor.execute(
            "ALTER USER %s@'%%' IDENTIFIED BY %s;",
            (db_user, new_password)
        )
        admin_cursor.execute("FLUSH PRIVILEGES;")
        admin_conn.commit()
    except Exception:
        pass


def delete_school_database(db_name):
    with connection.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")


from ..utils.per_school_db_utils import*
from django.contrib.auth.models import User


# Helper for normalized aliasing
def standardize_alias(db_name):
    return db_name if db_name.startswith('school_') else f"school_{db_name}"


from datetime import datetime
from django.contrib.auth.hashers import make_password
def school_registration(request):
    if request.method == 'POST':
        form = SchoolRegistrationForm(request.POST, request.FILES)
        for _ in messages.get_messages(request):
            pass

        if form.is_valid():
            email = form.cleaned_data.get('email_address')
            username = form.cleaned_data.get('username')

            # Prevent duplicate school emails
            if MasterSchool.objects.filter(email_address=email).exists():
                messages.error(request, "❌ Email is already registered to another school.")
            elif Users.objects.filter(username=username).exists():
                messages.error(request,"Username is already taken")
            else:
                    admin_username = request.POST.get('username')
                    admin_email = email
                    admin_password = request.POST.get("confirm_password") 
                
                
                    # Save the new school
                    school = form.save()

                    # Generate admin credentials for this school
                     # from your form
                    school_instance = MasterSchool.objects.get(id=school.id)
                    # Create school admin in Users table
                    Users.objects.create_user(
                        school=school_instance,
                        username=admin_username,
                        email=admin_email,
                        password=admin_password,  # UserManager will hash
                        role='Admin',
                        school_name=school.school_name,
                    )

                    messages.success(
                        request,
                        f"✅ School '{school.school_name}' registered successfully. "
                        f"Admin username: {admin_username}"
                    )
                    return redirect('login')

                # except Exception as e:
                #     if school.id:
                #         school.delete()
                    messages.error(request, f"⚠️ Failed to register school: {str(e)}")
    else:
        form = SchoolRegistrationForm()

    return render(request, 'school/school_registration.html', {'form': form})

@login_required
def update_school(request):
    for _ in messages.get_messages(request):
        pass
    school = get_object_or_404(MasterSchool, id = request.session['school_id'])

    if request.method == "POST":
        form = SchoolRegistrationForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
                form.save()
                messages.success(request, "School details updated successfully ✅")
                return redirect("dashboard")  # or redirect to dashboard
        else:
            messages.error(request, "Please correct the errors below ❌")
    else:
        form = SchoolRegistrationForm(instance=school)
    return render(request, "school/update_school.html", {"form": form, "school": school})

def school_account(request):
    return render(request,'school/account.html')
