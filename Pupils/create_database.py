import os
# import pymysql
import mysql.connector

def create_school_db_and_user(db_name, db_user, db_password):
    admin_user = os.environ.get('MYSQL_ADMIN_USER', 'root')
    admin_pass = os.environ.get('MYSQL_ADMIN_PASS', 'daenicel')

    # 1. Connect as admin and create DB and user
    admin_conn = pymysql.connect(
        host='localhost',
        user=admin_user,
        password=admin_pass,
        database='mysql'
    )
    admin_cursor = admin_conn.cursor()
    try:
        admin_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        admin_cursor.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY %s;", (db_password,))
        admin_cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%';")
        admin_cursor.execute("FLUSH PRIVILEGES;")
        admin_conn.commit()
    finally:
        admin_cursor.close()
        admin_conn.close()

    # 2. Connect as the new db user to the new DB and create tables
    tables = [
        """CREATE TABLE studentinfo (
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
        """CREATE TABLE fee (
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
        """CREATE TABLE leavemanagement (
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
        """CREATE TABLE marks (
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
        """CREATE TABLE pupilattendance (
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
        """CREATE TABLE teacherinfo (
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
        """CREATE TABLE teacherattendance (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(20) NOT NULL,
            date_of_attendance VARCHAR(10),
            term VARCHAR(6),
            year VARCHAR(10),
            status VARCHAR(7),
            time_in VARCHAR(30),
            CONSTRAINT teacherattendance_registration_no_fk FOREIGN KEY (registration_no) REFERENCES teacherinfo(registration_no)
        );""",
        """CREATE TABLE teachersrole (
            id SERIAL PRIMARY KEY,
            registration_no VARCHAR(20) NOT NULL,
            type_of_teacher VARCHAR(20),
            grade VARCHAR(10),
            stream VARCHAR(10),
            subject VARCHAR(200),
            CONSTRAINT teachersrole_registration_no_fk FOREIGN KEY (registration_no) REFERENCES teacherinfo(registration_no)
        );""",
        """CREATE TABLE teachingprogress (
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
        """CREATE TABLE logindetails (
            id SERIAL PRIMARY KEY,
            username VARCHAR(20) UNIQUE,
            type_of_user VARCHAR(20) NOT NULL,
            teacher_no VARCHAR(20) NOT NULL,
            email VARCHAR(50) NOT NULL,
            CONSTRAINT logindetails_teacher_no_fk FOREIGN KEY (teacher_no) REFERENCES teacherinfo(registration_no)
        );"""
    ]

    db_conn = mysql.connector.connect(
        host='localhost',
        user=db_user,
        password=db_password,
        database=db_name
    )
    db_cursor = db_conn.cursor()
    try:
        for table_sql in tables:
            db_cursor.execute(table_sql)
        db_conn.commit()
    finally:
        db_cursor.close()
        db_conn.close()
# create_school_db_and_user('danitech', 'danitech', 'danitech')

admin_user = os.environ.get('MYSQL_ADMIN_USER', 'root')
admin_pass =  os.environ.get('MYSQL_ADMIN_PASS', 'daenicel')
database = os.environ.get('MYSQL_DATABASE', 'ShuleBase')

admin_cursor = mysql.connector.connect(
    host='localhost',
    user=admin_user,
    password=admin_pass,
    database=database
).cursor()

admin_cursor.execute("create table is not exists User (id INT AUTO_INCREMENT PRIMARY KEY, role VARCHAR(50), school VARCHAR(50))")
admin_cursor.close()
