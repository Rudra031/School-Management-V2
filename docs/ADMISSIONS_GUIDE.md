# 🎓 Student Admissions Management Guide

This guide details the **Dual Admissions Pipeline** in Horizon SMS, designed for high-speed enrollment as well as comprehensive statutory record-keeping.

---

## 📑 Table of Contents
1. [Overview of Admissions Modes](#1-overview-of-admissions-modes)
2. [Mode 1: Quick Admission (Fast Track)](#2-mode-1-quick-admission-fast-track)
3. [Continuing into the Full Admission Dossier](#3-continuing-into-the-full-admission-dossier)
4. [Mode 2: Full 10-Step Admission Wizard](#4-mode-2-full-10-step-admission-wizard)
5. [Document Uploads & Verification](#5-document-uploads--verification)
6. [Admissions Pipeline Directory & Review](#6-admissions-pipeline-directory--review)

---

## 1. Overview of Admissions Modes

```text
                  +--------------------------------+
                  |    ADMISSIONS CONTROL HUB      |
                  +---------------+----------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
  [ MODE 1: QUICK ADMISSION ]                 [ MODE 2: FULL 10-STEP ]
  - 1-Page Rapid Entry                        - 10-Step Comprehensive Dossier
  - Core Demographics & Class Placement       - Family, Medical & Statutory IDs
  - Instant Class & Section Enrollment        - Document Uploads (TC, Marksheets)
  - Continue Full Dossier Option              - Transport & Fee Configurations
```

---

## 2. Mode 1: Quick Admission (Fast Track)

Accessible at `/admissions/quick/`:
- Designed for busy admission counters during peak enrollment seasons.
- Requires only mandatory student information:
  - First Name, Last Name, Date of Birth, Gender.
  - Academic Session, Class Level, and Section.
  - Primary Parent/Guardian Name, Phone, Email, and Address.
- **Action Choices**:
  1. **"Save & Finish Quick Admission"**: Enrolls the student immediately and renders the printable confirmation receipt.
  2. **"✨ Save & Continue Full Admission Process &rarr;"**: Enrolls the student instantly and immediately opens the 10-step full wizard pre-loaded with this student's data.

---

## 3. Continuing into the Full Admission Dossier

Administrators can continue or expand a quick admission record at any point:
- **Direct from Quick Admission**: Click *"Save & Continue Full Admission Process"*.
- **From the Success Screen**: Click *"✨ Continue Full Admission Process"* callout card.
- **From Admissions Pipeline Table**: Click the *"Full Dossier"* button on any student application row.

### How the Bridge Works:
- The system connects via `?app_id=<APP_ID>`.
- Displays a top connection badge: `Continuing Full Admission Profile: [Student Name] (Quick-Enroll Connected)`.
- Automatically populates all 10 steps with existing data.
- When finalized, it updates the existing student profile and attaches statutory documents **without creating duplicate student records**.

---

## 4. Mode 2: Full 10-Step Admission Wizard

Accessible at `/admissions/full/`:

| Step | Title | Data Collected |
| :--- | :--- | :--- |
| **01** | Student Demographics | First/Last Name, DOB, Gender, Blood Group, Social Category, Nationality, Mother Tongue, Aadhaar/PEN ID, Passport Photo. |
| **02** | Parents & Guardian | Father/Mother Names, Mobile Phones, Occupations, Official Email, Primary Guardian Designation. |
| **03** | Address & Emergency | Permanent Residential Address, City, State, PIN Code, Emergency Contact Person & Phone. |
| **04** | Previous Institution | Previous School Name, Affiliated Board (CBSE/ICSE/State/IB), Last Grade Attended, TC Number, TC Issue Date, Reason for Leaving. |
| **05** | Academic Placement | Academic Session, Class Level, Section, Curriculum Stream (STEM/Arts/General), Second Language Choice. |
| **06** | Medical & Health | Known Allergies, Chronic Conditions, Pediatrician Contact, Dietary Restrictions, Nurse Special Notes. |
| **07** | Document Center | Upload Transfer Certificate (TC), Previous Marksheet, Character Certificate, Birth Certificate. |
| **08** | Additional Services | Transport Route / Bus Stop Allocation, Hostel Wing & Room Placement, Sibling Links. |
| **09** | Review Matrix | Full data validation summary table before submission. |
| **10** | Finalize & Enroll | Auto-generation of Student ID, Admission No, Class Roll No, Term 1 Composite Invoice, and Official Printable Letter. |

---

## 5. Document Uploads & Verification

Uploaded documents are stored in the secure media vault under `media/documents/admissions/`:
- Supported formats: PDF, PNG, JPEG, WEBP.
- Status verification tracking: `Pending Review` &rarr; `Verified` &rarr; `Rejected`.

---

## 6. Admissions Pipeline Directory & Review

Accessible at `/admissions/pipeline/`:
- Filter by Academic Year, Class Level, and Status (`Submitted`, `Under Review`, `Accepted`, `Enrolled`, `Rejected`).
- Instant actions on each row:
  - **Review**: Open detailed applicant dossier.
  - **Full Dossier**: Complete or edit the full multi-step profile.
  - **Print Letter**: Generate official admission confirmation PDF.
