import os
import uuid
from decimal import Decimal
from datetime import datetime, date, time, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import SchoolSetting, AuditLog
from accounts.models import User, UserRole
from academics.models import AcademicYear, Department, ClassLevel, Section, Subject, ClassSubject, SubjectTeacherAllocation
from staff.models import Designation, StaffMember
from students.models import Student, StudentEnrollment, StudentHealthRecord
from parents.models import ParentProfile, ParentStudent
from timetable.models import TimeSlot, ClassTimetable
from attendance.models import StudentAttendanceSheet, StudentAttendanceRecord, StaffAttendanceRecord
from examinations.models import GradeScale, ExamTerm, ExamSchedule, ExamMarkEntry
from assignments.models import Assignment, AssignmentSubmission
from fees.models import FeeCategory, FeeStructure, StudentFeeInvoice, StudentFeePayment
from library.models import BookCategory, Book, BookCirculation
from admissions.models import AdmissionsApplication
from leave.models import LeaveType, LeaveRequest
from documents.models import DocumentCategory, SchoolDocument
from communication.models import Notice, InAppNotification
from inventory.models import AssetCategory, InventoryItem, AssetAllocation
from expenses.models import ExpenseCategory, Expense


class Command(BaseCommand):
    help = 'Seeds a rich, realistic, production-ready demonstration database across all 18 school management modules.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Beginning comprehensive demo data seeding...'))
        
        # 1. School Setting Singleton
        setting, _ = SchoolSetting.objects.get_or_create(id=1, defaults={
            'name': 'Horizon Public School',
            'code': 'HPS-DELHI',
            'tagline': 'Excellence in Leadership, Academics & Global Citizenship',
            'email': 'admissions@horizonpublicschool.edu.in',
            'phone': '+91 (011) 2748-9012',
            'address': 'Sector 14, Urban Estate, Rohini',
            'city': 'New Delhi',
            'state': 'Delhi (NCT)',
            'country': 'India',
            'currency_symbol': '₹',
            'currency_code': 'INR',
            'date_format': 'd M Y',
            'attendance_threshold_percentage': 75.00,
        })
        self.stdout.write(self.style.SUCCESS('[1/18] School Setting configured.'))


        # 2. Academic Years
        today = timezone.now().date()
        year_current, _ = AcademicYear.objects.get_or_create(
            name='2025-2026',
            defaults={
                'start_date': date(2025, 8, 1),
                'end_date': date(2026, 6, 30),
                'is_current': True,
            }
        )
        year_next, _ = AcademicYear.objects.get_or_create(
            name='2026-2027',
            defaults={
                'start_date': date(2026, 8, 1),
                'end_date': date(2027, 6, 30),
                'is_current': False,
            }
        )
        self.stdout.write(self.style.SUCCESS('[2/18] Academic Sessions created.'))

        # 3. Departments
        departments = {}
        dept_names = [
            ('Mathematics & Computer Science', 'Mathematics, Algebra, Calculus, Coding & Informatics'),
            ('Natural Sciences', 'Physics, Chemistry, Biology & Laboratory Sciences'),
            ('Humanities & Social Sciences', 'World History, Geography, Civics & Economics'),
            ('Languages & Literature', 'English Literature, World Languages & Linguistics'),
            ('Arts & Physical Education', 'Fine Arts, Music, Drama, Physical Fitness & Sports'),
        ]
        for name, desc in dept_names:
            dept, _ = Department.objects.get_or_create(name=name, defaults={'code': name[:4].upper(), 'description': desc})
            departments[name] = dept

        # 4. Designations
        designations = {}
        desig_data = [
            ('Principal & Head of School', 'Academic & Administrative Leadership'),
            ('Vice Principal', 'Curriculum & Student Affairs'),
            ('Senior Faculty Head', 'Departmental Teaching Lead'),
            ('High School Teacher', 'Senior Grade Classroom Instruction'),
            ('Middle School Teacher', 'Secondary Grade Instruction'),
            ('Primary Teacher', 'Elementary Instruction'),
            ('Senior Accountant', 'Fiscal Management & Financial Invoicing'),
            ('Chief Librarian', 'Library Resource Cataloging & Circulation'),
            ('Operations Officer', 'Facility & Support Staff Supervision'),
        ]
        for title, desc in desig_data:
            desig, _ = Designation.objects.get_or_create(title=title, defaults={'description': desc})
            designations[title] = desig

        # 5. Master Persona Users
        default_pwd = 'Password@123'
        
        users_data = [
            # Standard Fast-Fill Personas
            ('admin@school.edu', 'Super', 'Admin', UserRole.SUPERADMIN, True, True),
            ('principal@school.edu', 'Arthur', 'Pendleton', UserRole.PRINCIPAL, True, False),
            ('teacher@school.edu', 'Alan', 'Turing', UserRole.TEACHER, False, False),
            ('accountant@school.edu', 'Franklin', 'Richards', UserRole.ACCOUNTANT, False, False),
            ('student@school.edu', 'Clark', 'Kent', UserRole.STUDENT, False, False),
            ('parent@school.edu', 'Jonathan', 'Kent', UserRole.PARENT, False, False),

            # Institutional Extended Personas
            ('superadmin@horizonacademy.edu', 'Eleanor', 'Vance', UserRole.SUPERADMIN, True, True),
            ('principal@horizonacademy.edu', 'Arthur', 'Pendleton', UserRole.PRINCIPAL, True, False),
            ('admin@horizonacademy.edu', 'Marcus', 'Brody', UserRole.ADMIN, True, False),
            ('teacher.math@horizonacademy.edu', 'Alan', 'Turing', UserRole.TEACHER, False, False),
            ('teacher.science@horizonacademy.edu', 'Marie', 'Curie', UserRole.TEACHER, False, False),
            ('teacher.english@horizonacademy.edu', 'William', 'Shakespeare', UserRole.TEACHER, False, False),
            ('accountant@horizonacademy.edu', 'Franklin', 'Richards', UserRole.ACCOUNTANT, False, False),
            ('librarian@horizonacademy.edu', 'Alexandria', 'Page', UserRole.LIBRARIAN, False, False),
            ('parent@horizonacademy.edu', 'Jonathan', 'Kent', UserRole.PARENT, False, False),
            ('student@horizonacademy.edu', 'Clark', 'Kent', UserRole.STUDENT, False, False),
            ('staff@horizonacademy.edu', 'Alfred', 'Pennyworth', UserRole.STAFF, False, False),
        ]

        created_users = {}
        for email, first, last, role, is_staff, is_super in users_data:
            u = User.objects.filter(email=email).first()
            if not u:
                u = User.objects.create_user(
                    email=email,
                    username=email,
                    password=default_pwd,
                    first_name=first,
                    last_name=last,
                    user_type=role,
                    is_staff=is_staff,
                    is_superuser=is_super
                )
            else:
                u.set_password(default_pwd)
                u.is_active = True
                u.save()
            created_users[email] = u

        # 6. Staff Members (1:1 with Teacher/Staff Users)
        staff_records = {}
        staff_map = [
            (created_users['teacher.math@horizonacademy.edu'], 'TCH-001', designations['Senior Faculty Head'], departments['Mathematics & Computer Science'], 'M.Sc. Mathematics, Stanford University'),
            (created_users['teacher.science@horizonacademy.edu'], 'TCH-002', designations['High School Teacher'], departments['Natural Sciences'], 'Ph.D. Physics, Sorbonne University'),
            (created_users['teacher.english@horizonacademy.edu'], 'TCH-003', designations['High School Teacher'], departments['Languages & Literature'], 'M.A. English Literature, Oxford'),
            (created_users['accountant@horizonacademy.edu'], 'ACC-001', designations['Senior Accountant'], None, 'CPA, B.Sc. Accounting & Finance'),
            (created_users['librarian@horizonacademy.edu'], 'LIB-001', designations['Chief Librarian'], None, 'Master of Library & Information Science'),
            (created_users['staff@horizonacademy.edu'], 'OPS-001', designations['Operations Officer'], None, 'Facility & Logistics Operations Diploma'),
        ]

        for u, emp_id, desig, dept, quals in staff_map:
            sm, _ = StaffMember.objects.get_or_create(
                user=u,
                defaults={
                    'employee_id': emp_id,
                    'designation': desig,
                    'department': dept,
                    'joining_date': date(2022, 1, 15),
                    'qualification': quals,
                    'emergency_contact_name': 'Emergency Contact',
                    'emergency_contact_phone': '+1 555-9000',
                    'status': StaffMember.Status.ACTIVE
                }
            )
            staff_records[u.email] = sm

        self.stdout.write(self.style.SUCCESS('[3/18] Core Personas & Staff Profiles seeded.'))

        # 7. Class Levels & Sections (Grades 1 to 12)
        classes = {}
        sections = {}
        for num in range(1, 13):
            name = f"Grade {num}"
            cl, _ = ClassLevel.objects.get_or_create(numeric_level=num, defaults={'name': name})
            classes[num] = cl

            for sec_char in ['A', 'B']:
                sec, _ = Section.objects.get_or_create(class_level=cl, name=sec_char, defaults={'room_number': f'Room {num}0{sec_char}'})
                sections[f"{num}-{sec_char}"] = sec

        # 8. Subjects & Subject Allocations
        subjects_data = [
            ('Advanced Mathematics', 'MATH-101', departments['Mathematics & Computer Science']),
            ('Computer Science & Python', 'CS-101', departments['Mathematics & Computer Science']),
            ('General Physics', 'PHY-101', departments['Natural Sciences']),
            ('Chemistry Lab & Theory', 'CHEM-101', departments['Natural Sciences']),
            ('English Literature', 'ENG-101', departments['Languages & Literature']),
            ('World History & Civics', 'HIST-101', departments['Humanities & Social Sciences']),
        ]
        created_subjects = {}
        for sub_name, code, dept in subjects_data:
            subj, _ = Subject.objects.get_or_create(code=code, defaults={'name': sub_name, 'department': dept})
            created_subjects[code] = subj

        # Map subjects to Grade 9, 10, 11, 12
        for g in [9, 10, 11, 12]:
            cl = classes[g]
            for code, subj in created_subjects.items():
                ClassSubject.objects.get_or_create(class_level=cl, subject=subj)

        # Subject Teacher Allocation
        t_math = staff_records['teacher.math@horizonacademy.edu']
        t_sci = staff_records['teacher.science@horizonacademy.edu']
        t_eng = staff_records['teacher.english@horizonacademy.edu']

        sec_10a = sections['10-A']
        SubjectTeacherAllocation.objects.get_or_create(
            academic_year=year_current, section=sec_10a, subject=created_subjects['MATH-101'], defaults={'teacher': t_math}
        )
        SubjectTeacherAllocation.objects.get_or_create(
            academic_year=year_current, section=sec_10a, subject=created_subjects['PHY-101'], defaults={'teacher': t_sci}
        )
        SubjectTeacherAllocation.objects.get_or_create(
            academic_year=year_current, section=sec_10a, subject=created_subjects['ENG-101'], defaults={'teacher': t_eng}
        )

        self.stdout.write(self.style.SUCCESS('[4/18] Class Structure & Subject Allocations established.'))

        # 9. Students & Student Enrollments (25 Realistic Student Profiles)
        first_names = ['Clark', 'Diana', 'Bruce', 'Barry', 'Hal', 'Arthur', 'Victor', 'Selina', 'Barbara', 'Dick', 'Jason', 'Tim', 'Damian', 'Kara', 'Oliver', 'Dinah', 'Roy', 'Zatanna', 'John', 'Shayera', 'Wally', 'Kyle', 'Donna', 'Garth', 'Cassandra']
        last_names = ['Kent', 'Prince', 'Wayne', 'Allen', 'Jordan', 'Curry', 'Stone', 'Kyle', 'Gordon', 'Grayson', 'Todd', 'Drake', 'Wayne', 'Zor-El', 'Queen', 'Lance', 'Harper', 'Zatara', 'Stewart', 'Hol', 'West', 'Rayner', 'Troy', 'Bernstein', 'Cain']

        student_records = []
        enrollment_records = []
        for i in range(len(first_names)):
            fn = first_names[i]
            ln = last_names[i]
            adm_num = f"ADM-2025-{1000 + i}"
            stu_id = f"STU-{1000 + i}"
            
            # Link primary demo student to Clark Kent
            linked_user = created_users['student@horizonacademy.edu'] if i == 0 else None
            gender = 'MALE' if i % 2 == 0 else 'FEMALE'

            s, _ = Student.objects.get_or_create(
                admission_number=adm_num,
                defaults={
                    'user': linked_user,
                    'student_id': stu_id,
                    'first_name': fn,
                    'last_name': ln,
                    'gender': gender,
                    'date_of_birth': date(2010, 1 + (i % 12), 1 + (i % 25)),
                    'admission_date': date(2025, 8, 1),
                    'blood_group': 'O+' if i % 3 == 0 else 'A+',
                    'residential_address': f"{100 + i} Metropolis Avenue, District 4",
                    'emergency_contact_name': f"{ln} Guardian",
                    'emergency_contact_phone': f"+1 (555) 010-{1000 + i}",
                    'emergency_contact_relation': 'Parent / Guardian',
                    'status': Student.Status.ACTIVE
                }
            )
            student_records.append(s)

            # Enroll in Grade 10 Section A
            roll = i + 1
            enr, _ = StudentEnrollment.objects.get_or_create(
                student=s,
                academic_year=year_current,
                section=sec_10a,
                defaults={'roll_number': roll, 'is_current': True}
            )
            enrollment_records.append(enr)

        # Health record for Clark Kent
        StudentHealthRecord.objects.get_or_create(
            student=student_records[0],
            defaults={
                'blood_group': 'O+',
                'allergies_summary': 'Sensitive to green minerals',
                'chronic_conditions': 'None - Excellent physical constitution',
                'additional_notes': 'Authorized for all advanced physical education athletics.'
            }
        )

        # 10. Parent Profile & Parent-Student Links
        parent_user = created_users['parent@horizonacademy.edu']
        parent_prof, _ = ParentProfile.objects.get_or_create(
            user=parent_user,
            defaults={
                'first_name': 'Jonathan',
                'last_name': 'Kent',
                'occupation': 'Agronomist & Farmer',
                'primary_phone': '+1 (555) 444-1234',
                'email': 'parent@horizonacademy.edu',
                'residential_address': 'Rural Route 3, Smallville'
            }
        )
        # Link Clark Kent and Kara Zor-El to parent
        ParentStudent.objects.get_or_create(
            parent=parent_prof, student=student_records[0],
            defaults={'relationship_type': ParentStudent.RelationshipType.FATHER, 'is_primary_contact': True}
        )
        ParentStudent.objects.get_or_create(
            parent=parent_prof, student=student_records[13],
            defaults={'relationship_type': ParentStudent.RelationshipType.LEGAL_GUARDIAN, 'is_primary_contact': True}
        )

        self.stdout.write(self.style.SUCCESS('[5/18] 25 Students, Enrollments, Health & Parent Portfolios created.'))

        # 11. Timetable Bell Schedule & Period Allocation
        slots_data = [
            (1, 'Period 1', time(8, 30), time(9, 20), False),
            (2, 'Period 2', time(9, 25), time(10, 15), False),
            (3, 'Period 3', time(10, 30), time(11, 20), False),
            (4, 'Period 4', time(11, 25), time(12, 15), False),
            (5, 'Lunch Break', time(12, 15), time(13, 0), True),
            (6, 'Period 5', time(13, 0), time(13, 50), False),
            (7, 'Period 6', time(13, 55), time(14, 45), False),
        ]
        created_slots = {}
        for p_num, name, st, et, is_brk in slots_data:
            ts, _ = TimeSlot.objects.get_or_create(
                academic_year=year_current, period_number=p_num,
                defaults={'name': name, 'start_time': st, 'end_time': et, 'is_break': is_brk}
            )
            created_slots[p_num] = ts

        # Timetable for Grade 10-A on Monday to Friday (days 1 to 5)
        for day in [1, 2, 3, 4, 5]:
            ClassTimetable.objects.get_or_create(
                academic_year=year_current, section=sec_10a, day_of_week=day, time_slot=created_slots[1],
                defaults={'subject': created_subjects['MATH-101'], 'teacher': t_math, 'room_number': 'Room 101'}
            )
            ClassTimetable.objects.get_or_create(
                academic_year=year_current, section=sec_10a, day_of_week=day, time_slot=created_slots[2],
                defaults={'subject': created_subjects['PHY-101'], 'teacher': t_sci, 'room_number': 'Physics Lab 1'}
            )
            ClassTimetable.objects.get_or_create(
                academic_year=year_current, section=sec_10a, day_of_week=day, time_slot=created_slots[3],
                defaults={'subject': created_subjects['ENG-101'], 'teacher': t_eng, 'room_number': 'Room 101'}
            )

        self.stdout.write(self.style.SUCCESS('[6/18] Timetable engine & period allocations seeded.'))

        # 12. Attendance Registers (Historical Past 5 School Days)
        for offset in range(5):
            att_date = today - timedelta(days=offset)
            if att_date.weekday() < 5: # Monday to Friday
                sheet, _ = StudentAttendanceSheet.objects.get_or_create(
                    academic_year=year_current, section=sec_10a, date=att_date,
                    defaults={'taken_by': t_math.user}
                )
                for enr in enrollment_records:
                    status = StudentAttendanceRecord.Status.PRESENT
                    if enr.student.admission_number == 'ADM-2025-1002' and offset == 1:
                        status = StudentAttendanceRecord.Status.ABSENT
                    elif enr.student.admission_number == 'ADM-2025-1005' and offset == 2:
                        status = StudentAttendanceRecord.Status.LATE

                    StudentAttendanceRecord.objects.get_or_create(
                        sheet=sheet, student_enrollment=enr,
                        defaults={'status': status}
                    )

        # 13. Examinations, Grading Scale & Gradebook Records
        grades = [
            ('A+', 4.0, 90.0, 100.0, 'Outstanding Academic Mastery'),
            ('A', 3.75, 80.0, 89.99, 'Excellent Performance'),
            ('B', 3.0, 70.0, 79.99, 'Good Solid Competence'),
            ('C', 2.0, 50.0, 69.99, 'Satisfactory Progression'),
            ('F', 0.0, 0.0, 49.99, 'Needs Academic Remediation'),
        ]
        for ltr, pts, min_p, max_p, desc in grades:
            GradeScale.objects.get_or_create(grade_letter=ltr, defaults={'grade_point': Decimal(str(pts)), 'min_percentage': Decimal(str(min_p)), 'max_percentage': Decimal(str(max_p)), 'description': desc})

        term_mid, _ = ExamTerm.objects.get_or_create(
            academic_year=year_current, title='Term 1 Midterm Examinations',
            defaults={'start_date': date(2025, 10, 15), 'end_date': date(2025, 10, 25), 'is_published': True}
        )

        sched_math, _ = ExamSchedule.objects.get_or_create(
            exam_term=term_mid, class_level=classes[10], subject=created_subjects['MATH-101'],
            defaults={'exam_date': date(2025, 10, 16), 'start_time': time(9, 0), 'theory_marks_max': Decimal('80.00'), 'practical_marks_max': Decimal('20.00'), 'max_marks': Decimal('100.00'), 'pass_marks': Decimal('35.00')}
        )

        for idx, enr in enumerate(enrollment_records):
            th_marks = 70 + (idx % 10)
            pr_marks = 18 + (idx % 3)
            ExamMarkEntry.objects.get_or_create(
                exam_schedule=sched_math, student_enrollment=enr,
                defaults={'theory_marks_obtained': Decimal(str(th_marks)), 'practical_marks_obtained': Decimal(str(pr_marks)), 'entered_by': t_math.user}
            )

        self.stdout.write(self.style.SUCCESS('[7/18] Attendance matrices & Examination gradebooks populated.'))

        # 14. Assignments & Homework Submissions
        hw, _ = Assignment.objects.get_or_create(
            academic_year=year_current, section=sec_10a, subject=created_subjects['MATH-101'],
            title='Quadratic Functions & Parabolic Modeling',
            defaults={
                'teacher': t_math,
                'description': 'Solve problem set 4.2 (Questions 1 through 15). Graph parabolas and calculate vertex coordinates.',
                'assigned_date': today - timedelta(days=7),
                'due_date': timezone.now() + timedelta(days=3),
                'max_points': Decimal('50.00'),
            }
        )
        # Clark Kent submission
        AssignmentSubmission.objects.get_or_create(
            assignment=hw, student_enrollment=enrollment_records[0],
            defaults={
                'submission_text': 'All 15 questions solved with graph illustrations attached.',
                'score_obtained': Decimal('48.00'),
                'feedback': 'Excellent geometric accuracy and clear algebraic methodology.',
                'graded_at': timezone.now(),
                'graded_by': t_math.user,
                'status': AssignmentSubmission.Status.GRADED
            }
        )

        # 15. Fees & Invoices
        fee_cat_tuition, _ = FeeCategory.objects.get_or_create(name='Tuition Fee', defaults={'description': 'Core instructional fee'})
        fee_cat_lab, _ = FeeCategory.objects.get_or_create(name='Science Lab Fee', defaults={'description': 'Laboratory chemicals & apparatus'})

        FeeStructure.objects.get_or_create(
            academic_year=year_current, class_level=classes[10], fee_category=fee_cat_tuition, frequency=FeeStructure.Frequency.QUARTERLY,
            defaults={'amount': Decimal('1500.00'), 'due_date': date(2025, 9, 30)}
        )

        for idx, enr in enumerate(enrollment_records):
            inv_num = f"INV-2025-{2000 + idx}"
            inv, _ = StudentFeeInvoice.objects.get_or_create(
                invoice_number=inv_num,
                defaults={
                    'student_enrollment': enr,
                    'academic_year': year_current,
                    'title': 'Grade 10 Term 1 Tuition Fee',
                    'issue_date': date(2025, 8, 15),
                    'due_date': date(2025, 9, 30),
                    'total_amount': Decimal('1500.00'),
                    'balance_amount': Decimal('1500.00'),
                    'status': StudentFeeInvoice.Status.UNPAID
                }
            )
            if idx < 15: # First 15 students paid
                StudentFeePayment.objects.get_or_create(
                    invoice=inv,
                    receipt_number=f"REC-2025-{3000 + idx}",
                    defaults={
                        'payment_date': date(2025, 9, 10),
                        'amount_paid': Decimal('1500.00'),
                        'payment_method': StudentFeePayment.PaymentMethod.BANK_TRANSFER,
                        'transaction_id': f"TXN-WIRE-{4000 + idx}",
                        'collected_by': created_users['accountant@horizonacademy.edu']
                    }
                )

        # 16. Library Books & Circulation
        cat_sci, _ = BookCategory.objects.get_or_create(name='Science & Astrophysics')
        cat_lit, _ = BookCategory.objects.get_or_create(name='World Literature')
        cat_comp, _ = BookCategory.objects.get_or_create(name='Computer Science')

        b1, _ = Book.objects.get_or_create(
            isbn='978-0143127741', title='Cosmos: A Personal Voyage', author='Carl Sagan',
            defaults={'category': cat_sci, 'total_copies': 5, 'available_copies': 4, 'shelf_location': 'Aisle 2, Rack A'}
        )
        b2, _ = Book.objects.get_or_create(
            isbn='978-0262033848', title='Introduction to Algorithms', author='Thomas H. Cormen',
            defaults={'category': cat_comp, 'total_copies': 3, 'available_copies': 2, 'shelf_location': 'Aisle 4, Rack B'}
        )

        # Active Loan to Clark Kent
        BookCirculation.objects.get_or_create(
            book=b1, user=created_users['student@horizonacademy.edu'],
            defaults={
                'borrow_date': today - timedelta(days=7),
                'due_date': today + timedelta(days=7),
                'status': BookCirculation.Status.BORROWED,
                'issued_by': created_users['librarian@horizonacademy.edu']
            }
        )

        # 17. Admissions, Leave, Documents & Inventory
        AdmissionsApplication.objects.get_or_create(
            application_number='APP-2026-9001',
            defaults={
                'academic_year': year_next,
                'applying_for_class': classes[1],
                'first_name': 'Timothy',
                'last_name': 'Hunter',
                'gender': 'MALE',
                'date_of_birth': date(2020, 5, 12),
                'parent_name': 'James Hunter',
                'parent_phone': '+1 (555) 777-8899',
                'parent_email': 'james.hunter@example.com',
                'residential_address': '42 Magic Lane, London St',
                'status': AdmissionsApplication.Stage.ACCEPTED
            }
        )

        leave_sick, _ = LeaveType.objects.get_or_create(name='Sick Leave', defaults={'allocated_days_per_year': 12})
        LeaveRequest.objects.get_or_create(
            user=created_users['teacher.science@horizonacademy.edu'], leave_type=leave_sick,
            start_date=today - timedelta(days=2), end_date=today - timedelta(days=1),
            defaults={'reason': 'Recovering from fever', 'status': LeaveRequest.Status.APPROVED, 'reviewed_by': created_users['admin@horizonacademy.edu']}
        )

        doc_cat_pol, _ = DocumentCategory.objects.get_or_create(name='Institutional Policies & Charters')
        dummy_file = SimpleUploadedFile("student_code_of_conduct.pdf", b"Horizon Academy Student Code of Conduct 2025-2026", content_type="application/pdf")
        SchoolDocument.objects.get_or_create(
            title='Student Code of Conduct 2025-2026',
            defaults={'category': doc_cat_pol, 'document_file': dummy_file, 'access_level': SchoolDocument.AccessLevel.PUBLIC, 'uploaded_by': created_users['admin@horizonacademy.edu']}
        )

        inv_cat_it, _ = AssetCategory.objects.get_or_create(name='IT & Computing Hardware')
        inv_item_lap, _ = InventoryItem.objects.get_or_create(
            item_code='IT-LAP-5500', name='Dell Latitude 5500 Laptop',
            defaults={'category': inv_cat_it, 'quantity_total': 30, 'quantity_in_use': 15, 'unit': 'Units', 'reorder_threshold': 5, 'cost_per_unit': Decimal('750.00'), 'location': 'IT Lab 1'}
        )
        AssetAllocation.objects.get_or_create(
            item=inv_item_lap, allocated_to_user=created_users['teacher.math@horizonacademy.edu'],
            defaults={'quantity': 1, 'allocated_date': date(2025, 8, 10), 'status': AssetAllocation.Status.ACTIVE}
        )

        # 18. Notices & Expenses
        Notice.objects.get_or_create(
            title='Welcome to the 2025-2026 Academic Session',
            defaults={
                'content': 'We warmly welcome all new and returning students, faculty, and families to Horizon Academy. Let us embark on another year of academic excellence and global leadership.',
                'target_audience': Notice.Audience.ALL,
                'is_pinned': True,
                'is_published': True,
                'created_by': created_users['principal@horizonacademy.edu']
            }
        )

        exp_cat_util, _ = ExpenseCategory.objects.get_or_create(name='Utilities & Maintenance')
        Expense.objects.get_or_create(
            voucher_number='EXP-202509-0001',
            defaults={
                'academic_year': year_current,
                'category': exp_cat_util,
                'title': 'Campus High-Speed Fiber Optic Internet',
                'amount': Decimal('850.00'),
                'expense_date': date(2025, 9, 5),
                'payment_method': Expense.PaymentMethod.BANK_TRANSFER,
                'vendor_name': 'Enterprise Telecom Corp',
                'approved_by': created_users['accountant@horizonacademy.edu']
            }
        )

        self.stdout.write(self.style.SUCCESS('[18/18] Notices, Documents, Inventory, and Operating Expenses seeded.'))
        self.stdout.write(self.style.SUCCESS('\n================================================================='))
        self.stdout.write(self.style.SUCCESS('SUCCESS: Demonstration seed data generated successfully!'))
        self.stdout.write(self.style.SUCCESS('Default password for all demo accounts: Password123!'))
        self.stdout.write(self.style.SUCCESS('=================================================================\n'))
