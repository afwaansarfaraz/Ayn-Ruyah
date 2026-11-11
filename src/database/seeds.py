"""Realistic Indian demo data seeder for multi-tenant Diabetic Retinopathy platform.

Populates 3 independent Indian hospital screening facilities with authentic,
diverse, synthetic demographic and clinical cohorts across all 5 DR stages.
Never uses real identifiable personal patient information.
"""

import os
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any

from src.database.connection import Database
from src.services.tenant_service import TenantService
from src.services.user_service import UserService
from src.services.patient_service import PatientService
from src.services.screening_service import ScreeningService
from src.core.constants import GRADE_LABELS, GRADE_SEVERITY, GRADE_RECOMMENDATIONS
from src.core.logging import logger

# Clean, neutral professional medical silhouette avatars
def get_avatar(seed: str, gender: str) -> str:
    """Returns a clean, neutral professional medical silhouette avatar."""
    if gender and gender.lower() == "male":
        return "/assets/branding/avatar_male.svg"
    elif gender and gender.lower() == "female":
        return "/assets/branding/avatar_female.svg"
    return "/assets/branding/avatar_placeholder.svg"


HOSPITALS_DATA = [
    {
        "id": "apex-retina-lucknow",
        "name": "Apex Retina Care & Research Institute",
        "registration_number": "UP-HOSP-LKO-2021-9481",
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "address": "14/2 Ashok Marg, Near Hazratganj Crossing, Lucknow, UP 226001",
        "contact_email": "screening@apexretina-lko.org",
        "contact_phone": "+91 522 2618900",
        "logo_url": "https://api.dicebear.com/7.x/identicon/svg?seed=ApexRetina&backgroundColor=0d9488",
        "tier": "Tertiary Eye Institute",
        "users": [
            {
                "username": "admin_lucknow",
                "password": "admin123",
                "full_name": "Dr. Arvind Verma",
                "role": "hospital_admin",
                "email": "dr.verma@apexretina-lko.org",
                "phone": "+91 94150 12345",
                "qualification": "MS (Ophth), Vitreoretinal Fellow",
            },
            {
                "username": "dr_saxena",
                "password": "doctor123",
                "full_name": "Dr. Neha Saxena",
                "role": "ophthalmologist",
                "email": "dr.saxena@apexretina-lko.org",
                "phone": "+91 98390 54321",
                "qualification": "DNB (Ophthalmology), FICO",
            },
            {
                "username": "screener_rajesh",
                "password": "screener123",
                "full_name": "Rajesh Kumar",
                "role": "screening_operator",
                "email": "r.kumar@apexretina-lko.org",
                "phone": "+91 99190 67890",
                "qualification": "Certified Ophthalmic Paramedic (AIIMS)",
            },
        ],
    },
    {
        "id": "shroff-eye-delhi",
        "name": "Dr. Shroff Charity Eye Hospital — Retinal Unit",
        "registration_number": "DL-CLINIC-DLH-2018-4102",
        "city": "New Delhi",
        "state": "Delhi",
        "address": "5027 Kedar Nath Road, Daryaganj, New Delhi, DL 110002",
        "contact_email": "retina@shroffeye-delhi.org",
        "contact_phone": "+91 11 43524444",
        "logo_url": "https://api.dicebear.com/7.x/identicon/svg?seed=ShroffEye&backgroundColor=2563eb",
        "tier": "Charitable Trust Hospital",
        "users": [
            {
                "username": "admin_delhi",
                "password": "admin123",
                "full_name": "Dr. Meenakshi Sundaram",
                "role": "hospital_admin",
                "email": "m.sundaram@shroffeye-delhi.org",
                "phone": "+91 98110 99887",
                "qualification": "MD (AIIMS), FRCS (Edin)",
            },
            {
                "username": "dr_batra",
                "password": "doctor123",
                "full_name": "Dr. Rohan Batra",
                "role": "ophthalmologist",
                "email": "r.batra@shroffeye-delhi.org",
                "phone": "+91 98711 22334",
                "qualification": "MS (Ophthalmology)",
            },
            {
                "username": "screener_sunita",
                "password": "screener123",
                "full_name": "Sunita Nair",
                "role": "screening_operator",
                "email": "sunita.nair@shroffeye-delhi.org",
                "phone": "+91 99990 11223",
                "qualification": "Diploma in Ophthalmic Assistance",
            },
        ],
    },
    {
        "id": "sankara-eye-bengaluru",
        "name": "Sankara Eye Centre — Diabetic Retinopathy Clinic",
        "registration_number": "KA-MED-BLR-2020-7731",
        "city": "Bengaluru",
        "state": "Karnataka",
        "address": "Varthur Main Road, Kundalahalli Gate, Bengaluru, KA 560037",
        "contact_email": "retina@sankara-blr.in",
        "contact_phone": "+91 80 28542727",
        "logo_url": "https://api.dicebear.com/7.x/identicon/svg?seed=SankaraEye&backgroundColor=059669",
        "tier": "Specialty Retinal Centre",
        "users": [
            {
                "username": "admin_bengaluru",
                "password": "admin123",
                "full_name": "Dr. S. K. Narayana Rao",
                "role": "hospital_admin",
                "email": "sk.rao@sankara-blr.in",
                "phone": "+91 98450 33445",
                "qualification": "FRCS (Glasg), Vitreoretinal Specialist",
            },
            {
                "username": "dr_hegde",
                "password": "doctor123",
                "full_name": "Dr. Ananya Hegde",
                "role": "ophthalmologist",
                "email": "ananya.h@sankara-blr.in",
                "phone": "+91 97410 55667",
                "qualification": "DNB, Vitreoretinal Fellow",
            },
            {
                "username": "screener_karthik",
                "password": "screener123",
                "full_name": "Karthik S.",
                "role": "screening_operator",
                "email": "karthik.s@sankara-blr.in",
                "phone": "+91 94800 88990",
                "qualification": "Certified Retinal Imager",
            },
        ],
    },
]

# 36 Realistic Indian Patient Profiles across different ages, genders, and Indian cities
PATIENTS_SEEDS = [
    # --- Lucknow Cohort (20 patients) ---
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Ramesh", "last_name": "Tiwari", "gender": "Male",
        "dob": "1964-08-14", "age": 62, "phone": "+91 94150 78219", "email": "ramesh.tiwari@gmail.com",
        "address": "Plot 24, Sector B, Aliganj", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226024",
        "diabetes_type": "Type 2", "diabetes_duration_years": 14.5, "hba1c": 8.9,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Longstanding T2D with peripheral neuropathy. Reports blurred vision in left eye for 3 months.",
        "screening": {"grade": 3, "eye": "Left Eye (OS)", "confidence": 88.4, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Sunita", "last_name": "Srivastava", "gender": "Female",
        "dob": "1972-04-20", "age": 54, "phone": "+91 98390 12847", "email": "sunita.sriv@yahoo.co.in",
        "address": "3/118 Vipul Khand, Gomti Nagar", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226010",
        "diabetes_type": "Type 2", "diabetes_duration_years": 8.0, "hba1c": 7.4,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Routine annual diabetic retinal screening. Controlled fasting glucose.",
        "screening": {"grade": 1, "eye": "Bilateral", "confidence": 91.2, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Mohammad", "last_name": "Afzal", "gender": "Male",
        "dob": "1958-11-03", "age": 68, "phone": "+91 99190 33412", "email": "m.afzal.lko@outlook.com",
        "address": "82 Nazirabad Road, Aminabad", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226018",
        "diabetes_type": "Type 2", "diabetes_duration_years": 21.0, "hba1c": 9.8,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 1,
        "clinical_notes": "Severe diabetic nephropathy. Floaters and sudden visual deterioration noted. Urgent referral.",
        "screening": {"grade": 4, "eye": "Right Eye (OD)", "confidence": 94.6, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Pooja", "last_name": "Mishra", "gender": "Female",
        "dob": "1988-06-17", "age": 38, "phone": "+91 94500 89123", "email": "pooja.mishra88@gmail.com",
        "address": "B-42, Sector J, Aliganj", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226024",
        "diabetes_type": "Type 1", "diabetes_duration_years": 16.0, "hba1c": 7.8,
        "insulin_dependent": 1, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Type 1 diabetes since age 22. Multiple microaneurysms detected in macula periphery.",
        "screening": {"grade": 2, "eye": "Left Eye (OS)", "confidence": 86.7, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Aarav", "last_name": "Verma", "gender": "Male",
        "dob": "2011-03-09", "age": 15, "phone": "+91 94155 44332", "email": "suresh.verma.parent@gmail.com",
        "address": "Flat 302, Rohtas Court, Prag Narain Road", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226001",
        "diabetes_type": "Type 1", "diabetes_duration_years": 4.5, "hba1c": 7.1,
        "insulin_dependent": 1, "hypertension": 0, "smoker": 0,
        "is_minor": 1, "guardian_name": "Suresh Verma", "guardian_relation": "Father", "guardian_phone": "+91 94155 44332",
        "clinical_notes": "Adolescent screening validation record. Baseline pediatric fundus exam. Clear fundus.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 98.1, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Fatima", "last_name": "Zehra", "gender": "Female",
        "dob": "1994-09-25", "age": 32, "phone": "+91 98380 77112", "email": "fatima.zehra@rediffmail.com",
        "address": "Kashmiri Mohalla, Old City", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226003",
        "diabetes_type": "Gestational", "diabetes_duration_years": 1.0, "hba1c": 6.8,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Gestational diabetes diagnosed at 26 weeks. Fundus exam normal with clear retinal vasculature.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 97.4, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Devendra", "last_name": "Singh Yadav", "gender": "Male",
        "dob": "1960-01-12", "age": 66, "phone": "+91 94520 66554", "email": "devendra.yadav@gmail.com",
        "address": "Village Sarojini Nagar, Kanpur Road", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226008",
        "diabetes_type": "Type 2", "diabetes_duration_years": 18.0, "hba1c": 9.1,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 1,
        "clinical_notes": "Farmer with irregular compliance. Extensive intraretinal blot haemorrhages and hard exudates.",
        "screening": {"grade": 3, "eye": "Right Eye (OD)", "confidence": 89.9, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Kavita", "last_name": "Agarwal", "gender": "Female",
        "dob": "1978-12-05", "age": 47, "phone": "+91 98399 22110", "email": "kavita.agarwal@hotmail.com",
        "address": "45 Cantonment Road", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226001",
        "diabetes_type": "Type 2", "diabetes_duration_years": 6.0, "hba1c": 7.0,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Well controlled on Metformin. Routine checkup.",
        "screening": {"grade": 0, "eye": "Left Eye (OS)", "confidence": 96.5, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Anil", "last_name": "Kapoor", "gender": "Male",
        "dob": "1970-03-30", "age": 56, "phone": "+91 94151 90812", "email": "anil.kapoor.lko@gmail.com",
        "address": "Sector 14, Indira Nagar", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226016",
        "diabetes_type": "Type 2", "diabetes_duration_years": 11.0, "hba1c": 8.2,
        "insulin_dependent": 0, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Moderate non-proliferative DR. Exudates in temporal macula.",
        "screening": {"grade": 2, "eye": "Bilateral", "confidence": 84.1, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Shabana", "last_name": "Bano", "gender": "Female",
        "dob": "1982-07-14", "age": 44, "phone": "+91 99350 44119", "email": "shabana.bano@gmail.com",
        "address": "Chowk Bazar, Near Gol Darwaza", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226003",
        "diabetes_type": "Type 2", "diabetes_duration_years": 7.5, "hba1c": 7.6,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Isolated microaneurysms without macular edema.",
        "screening": {"grade": 1, "eye": "Right Eye (OD)", "confidence": 88.0, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Harish", "last_name": "Chandra Joshi", "gender": "Male",
        "dob": "1952-10-19", "age": 74, "phone": "+91 94510 33887", "email": "hc.joshi.ret@gmail.com",
        "address": "C-12, Sector 8, Jankipuram", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226021",
        "diabetes_type": "Type 2", "diabetes_duration_years": 25.0, "hba1c": 9.4,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Neovascularization on disc (NVD). High risk of vitreous hemorrhage.",
        "screening": {"grade": 4, "eye": "Left Eye (OS)", "confidence": 95.8, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Manju", "last_name": "Gupta", "gender": "Female",
        "dob": "1967-05-11", "age": 59, "phone": "+91 98381 44556", "email": "manju.gupta59@gmail.com",
        "address": "12 Eldeco Greens, Gomti Nagar", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226010",
        "diabetes_type": "Type 2", "diabetes_duration_years": 9.0, "hba1c": 7.9,
        "insulin_dependent": 0, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Microaneurysms and few dot hemorrhages.",
        "screening": {"grade": 2, "eye": "Bilateral", "confidence": 82.5, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Deepak", "last_name": "Pandey", "gender": "Male",
        "dob": "1985-02-28", "age": 41, "phone": "+91 94158 77221", "email": "deepak.pandey@tcs.com",
        "address": "Flat 401, Cyber Heights, Vibhuti Khand", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226010",
        "diabetes_type": "Type 2", "diabetes_duration_years": 3.0, "hba1c": 6.5,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Early onset T2D discovered during corporate health check. Normal retina.",
        "screening": {"grade": 0, "eye": "Left Eye (OS)", "confidence": 99.0, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Rukhsana", "last_name": "Khatoon", "gender": "Female",
        "dob": "1963-09-08", "age": 63, "phone": "+91 99360 88210", "email": "rukhsana.k@yahoo.com",
        "address": "House 18, Victoria Street", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226003",
        "diabetes_type": "Type 2", "diabetes_duration_years": 17.0, "hba1c": 8.7,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Multiple cotton wool spots and venous beading in two quadrants.",
        "screening": {"grade": 3, "eye": "Right Eye (OD)", "confidence": 87.6, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Pradeep", "last_name": "Shukla", "gender": "Male",
        "dob": "1975-11-23", "age": 51, "phone": "+91 94501 12399", "email": "pradeep.shukla@upgov.in",
        "address": "B-18 Rajajipuram", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226017",
        "diabetes_type": "Type 2", "diabetes_duration_years": 8.5, "hba1c": 7.3,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Few microaneurysms, no significant progression from last year.",
        "screening": {"grade": 1, "eye": "Bilateral", "confidence": 90.1, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Sita", "last_name": "Ram Meena", "gender": "Male",
        "dob": "1949-04-16", "age": 77, "phone": "+91 94154 55660", "email": "sitaram.meena@gmail.com",
        "address": "Qtr 12, Railway Colony, Charbagh", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226004",
        "diabetes_type": "Type 2", "diabetes_duration_years": 28.0, "hba1c": 10.2,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 1,
        "clinical_notes": "Proliferative DR with tractional membranes. Urgent vitrectomy consultation.",
        "screening": {"grade": 4, "eye": "Right Eye (OD)", "confidence": 96.2, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Ananya", "last_name": "Patel", "gender": "Female",
        "dob": "2010-08-12", "age": 16, "phone": "+91 98394 66110", "email": "meena.patel.parent@gmail.com",
        "address": "78 River Bank Colony", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226018",
        "diabetes_type": "Type 1", "diabetes_duration_years": 5.0, "hba1c": 7.5,
        "insulin_dependent": 1, "hypertension": 0, "smoker": 0,
        "is_minor": 1, "guardian_name": "Meena Patel", "guardian_relation": "Mother", "guardian_phone": "+91 98394 66110",
        "clinical_notes": "Adolescent T1D screening profile. Fundus normal. Regular pediatric endocrinology follow up.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 97.9, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Satish", "last_name": "Kumar Rastogi", "gender": "Male",
        "dob": "1969-12-01", "age": 57, "phone": "+91 94150 99881", "email": "satish.rastogi@gmail.com",
        "address": "Chowk Sarafa", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226003",
        "diabetes_type": "Type 2", "diabetes_duration_years": 10.0, "hba1c": 8.0,
        "insulin_dependent": 0, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Moderate NPDR with hard exudates outside macula.",
        "screening": {"grade": 2, "eye": "Left Eye (OS)", "confidence": 85.3, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Geeta", "last_name": "Devi", "gender": "Female",
        "dob": "1955-03-15", "age": 71, "phone": "+91 94522 33441", "email": "geeta.devi.lko@gmail.com",
        "address": "Village Bakshi Ka Talab", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226201",
        "diabetes_type": "Type 2", "diabetes_duration_years": 15.0, "hba1c": 8.6,
        "insulin_dependent": 0, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Severe NPDR with microaneurysms in all four quadrants.",
        "screening": {"grade": 3, "eye": "Bilateral", "confidence": 91.0, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "apex-retina-lucknow",
        "first_name": "Vikas", "last_name": "Singh", "gender": "Male",
        "dob": "1983-05-22", "age": 43, "phone": "+91 98398 55443", "email": "vikas.singh.up@gmail.com",
        "address": "House 45, Sector D, Mahanagar", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226006",
        "diabetes_type": "Pre-diabetes", "diabetes_duration_years": 1.5, "hba1c": 6.1,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Impaired glucose tolerance. Screening baseline. Clear fundus.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 99.2, "sample": "grade0_14197_left-600.jpg"}
    },

    # --- Delhi Cohort (10 patients) ---
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Gurpreet", "last_name": "Singh", "gender": "Male",
        "dob": "1966-07-19", "age": 60, "phone": "+91 98110 54321", "email": "gurpreet.singh@delhi.in",
        "address": "B-12, Lajpat Nagar II", "city": "New Delhi", "state": "Delhi", "pincode": "110024",
        "diabetes_type": "Type 2", "diabetes_duration_years": 13.0, "hba1c": 8.4,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Moderate NPDR with ring of hard exudates.",
        "screening": {"grade": 2, "eye": "Right Eye (OD)", "confidence": 87.2, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Priyanka", "last_name": "Bhardwaj", "gender": "Female",
        "dob": "1980-02-14", "age": 46, "phone": "+91 98711 90812", "email": "priyanka.bhardwaj@gmail.com",
        "address": "Flat 204, Pocket 1, Mayur Vihar Phase 1", "city": "New Delhi", "state": "Delhi", "pincode": "110091",
        "diabetes_type": "Type 2", "diabetes_duration_years": 5.5, "hba1c": 6.9,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Mild non-proliferative changes. Advise tight glycemic control.",
        "screening": {"grade": 1, "eye": "Left Eye (OS)", "confidence": 89.4, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Amitav", "last_name": "Mukherjee", "gender": "Male",
        "dob": "1954-10-08", "age": 72, "phone": "+91 98101 22334", "email": "amitav.m@crpark.delhi.in",
        "address": "K-84, C.R. Park", "city": "New Delhi", "state": "Delhi", "pincode": "110019",
        "diabetes_type": "Type 2", "diabetes_duration_years": 22.0, "hba1c": 9.5,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Proliferative DR with preretinal hemorrhage. Urgent panretinal photocoagulation indicated.",
        "screening": {"grade": 4, "eye": "Right Eye (OD)", "confidence": 95.1, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Deepa", "last_name": "Nair", "gender": "Female",
        "dob": "1976-09-30", "age": 50, "phone": "+91 98188 44332", "email": "deepa.nair@delhiuniv.ac.in",
        "address": "Faculty Flats, North Campus, Delhi University", "city": "New Delhi", "state": "Delhi", "pincode": "110007",
        "diabetes_type": "Type 2", "diabetes_duration_years": 4.0, "hba1c": 6.6,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Clear fundus bilaterally. Annual screening reminder.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 98.7, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Rajinder", "last_name": "Kohli", "gender": "Male",
        "dob": "1962-04-12", "age": 64, "phone": "+91 98112 66778", "email": "rajinder.kohli@gmail.com",
        "address": "15/4 Rajouri Garden", "city": "New Delhi", "state": "Delhi", "pincode": "110027",
        "diabetes_type": "Type 2", "diabetes_duration_years": 16.0, "hba1c": 8.8,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 1,
        "clinical_notes": "Severe NPDR, extensive microvascular abnormalities.",
        "screening": {"grade": 3, "eye": "Bilateral", "confidence": 90.8, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Simran", "last_name": "Kaur", "gender": "Female",
        "dob": "1992-01-20", "age": 34, "phone": "+91 99990 77881", "email": "simran.kaur92@gmail.com",
        "address": "C-4, Vikas Puri", "city": "New Delhi", "state": "Delhi", "pincode": "110018",
        "diabetes_type": "Type 1", "diabetes_duration_years": 12.0, "hba1c": 7.2,
        "insulin_dependent": 1, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Mild NPDR with early microaneurysms.",
        "screening": {"grade": 1, "eye": "Right Eye (OD)", "confidence": 92.0, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Venkatesh", "last_name": "Prasad", "gender": "Male",
        "dob": "1973-11-15", "age": 53, "phone": "+91 98710 33441", "email": "v.prasad.delhi@gmail.com",
        "address": "Sector 9, R.K. Puram", "city": "New Delhi", "state": "Delhi", "pincode": "110022",
        "diabetes_type": "Type 2", "diabetes_duration_years": 7.0, "hba1c": 7.7,
        "insulin_dependent": 0, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Moderate retinopathy features. Schedule follow up in 6 months.",
        "screening": {"grade": 2, "eye": "Left Eye (OS)", "confidence": 83.9, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Meera", "last_name": "Deshmukh", "gender": "Female",
        "dob": "1986-08-03", "age": 40, "phone": "+91 98114 88990", "email": "meera.deshmukh@gmail.com",
        "address": "Pocket B, Sarita Vihar", "city": "New Delhi", "state": "Delhi", "pincode": "110076",
        "diabetes_type": "Type 2", "diabetes_duration_years": 3.5, "hba1c": 6.7,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Normal fundus, healthy optic disc.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 98.4, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Zubair", "last_name": "Ahmed", "gender": "Male",
        "dob": "1959-05-18", "age": 67, "phone": "+91 98108 11229", "email": "zubair.ahmed@yahoo.com",
        "address": "Basti Nizamuddin West", "city": "New Delhi", "state": "Delhi", "pincode": "110013",
        "diabetes_type": "Type 2", "diabetes_duration_years": 19.0, "hba1c": 9.2,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Severe non-proliferative DR with venous caliber changes.",
        "screening": {"grade": 3, "eye": "Right Eye (OD)", "confidence": 88.7, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "shroff-eye-delhi",
        "first_name": "Master Kabir", "last_name": "Gupta", "gender": "Male",
        "dob": "2012-07-21", "age": 14, "phone": "+91 98110 44556", "email": "tarun.gupta.parent@gmail.com",
        "address": "Sector 14, Rohini", "city": "New Delhi", "state": "Delhi", "pincode": "110085",
        "diabetes_type": "Type 1", "diabetes_duration_years": 3.0, "hba1c": 6.9,
        "insulin_dependent": 1, "hypertension": 0, "smoker": 0,
        "is_minor": 1, "guardian_name": "Tarun Gupta", "guardian_relation": "Father", "guardian_phone": "+91 98110 44556",
        "clinical_notes": "Synthetic pediatric test profile. Retinal vessels normal.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 99.1, "sample": "grade0_14197_left-600.jpg"}
    },

    # --- Bengaluru Cohort (6 patients) ---
    {
        "tenant_id": "sankara-eye-bengaluru",
        "first_name": "Nagaraj", "last_name": "Bhat", "gender": "Male",
        "dob": "1965-03-22", "age": 61, "phone": "+91 98450 77881", "email": "nagaraj.bhat@bengaluru.in",
        "address": "72, 4th Main, Malleshwaram", "city": "Bengaluru", "state": "Karnataka", "pincode": "560003",
        "diabetes_type": "Type 2", "diabetes_duration_years": 12.0, "hba1c": 8.1,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Moderate DR with macular dot hemorrhages.",
        "screening": {"grade": 2, "eye": "Bilateral", "confidence": 86.4, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "sankara-eye-bengaluru",
        "first_name": "Lakshmi", "last_name": "Narayanan", "gender": "Female",
        "dob": "1971-11-10", "age": 55, "phone": "+91 94480 33442", "email": "lakshmi.narayanan@gmail.com",
        "address": "345, 17th Cross, HSR Layout Sector 4", "city": "Bengaluru", "state": "Karnataka", "pincode": "560102",
        "diabetes_type": "Type 2", "diabetes_duration_years": 7.0, "hba1c": 7.2,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Mild microaneurysms in paramacular zone.",
        "screening": {"grade": 1, "eye": "Right Eye (OD)", "confidence": 91.5, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "sankara-eye-bengaluru",
        "first_name": "Suresh", "last_name": "Patil", "gender": "Male",
        "dob": "1956-08-19", "age": 70, "phone": "+91 98800 66771", "email": "suresh.patil@karnataka.gov.in",
        "address": "12, 1st Block, Koramangala", "city": "Bengaluru", "state": "Karnataka", "pincode": "560034",
        "diabetes_type": "Type 2", "diabetes_duration_years": 20.0, "hba1c": 9.6,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Proliferative DR with vitreous haze and frond neovascularization.",
        "screening": {"grade": 4, "eye": "Left Eye (OS)", "confidence": 94.9, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "sankara-eye-bengaluru",
        "first_name": "Shweta", "last_name": "Rao", "gender": "Female",
        "dob": "1989-04-14", "age": 37, "phone": "+91 97410 88992", "email": "shweta.rao@infosys.com",
        "address": "Tower 4, Electronic City Phase 1", "city": "Bengaluru", "state": "Karnataka", "pincode": "560100",
        "diabetes_type": "Type 1", "diabetes_duration_years": 9.0, "hba1c": 6.8,
        "insulin_dependent": 1, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Well maintained T1D on insulin pump. Clear fundus.",
        "screening": {"grade": 0, "eye": "Bilateral", "confidence": 98.9, "sample": "grade0_14197_left-600.jpg"}
    },
    {
        "tenant_id": "sankara-eye-bengaluru",
        "first_name": "Syed", "last_name": "Irfan", "gender": "Male",
        "dob": "1963-12-07", "age": 63, "phone": "+91 98455 11220", "email": "syed.irfan.blr@gmail.com",
        "address": "Mosque Road, Frazer Town", "city": "Bengaluru", "state": "Karnataka", "pincode": "560005",
        "diabetes_type": "Type 2", "diabetes_duration_years": 15.5, "hba1c": 8.7,
        "insulin_dependent": 1, "hypertension": 1, "smoker": 0,
        "clinical_notes": "Severe non-proliferative changes with extensive intraretinal microvascular abnormalities.",
        "screening": {"grade": 3, "eye": "Bilateral", "confidence": 89.2, "sample": "grade3_6b128e648646-600-FS.jpg"}
    },
    {
        "tenant_id": "sankara-eye-bengaluru",
        "first_name": "Meenakshi", "last_name": "Iyer", "gender": "Female",
        "dob": "1981-06-25", "age": 45, "phone": "+91 98860 44551", "email": "meenakshi.iyer@gmail.com",
        "address": "42, 8th Cross, Malleshwaram", "city": "Bengaluru", "state": "Karnataka", "pincode": "560003",
        "diabetes_type": "Type 2", "diabetes_duration_years": 5.0, "hba1c": 7.0,
        "insulin_dependent": 0, "hypertension": 0, "smoker": 0,
        "clinical_notes": "Single microaneurysm noted. Non-referable early mild DR.",
        "screening": {"grade": 1, "eye": "Left Eye (OS)", "confidence": 90.7, "sample": "grade0_14197_left-600.jpg"}
    },
]


def get_seed_password(role: str, fallback: str = "admin123") -> str:
    """Retrieves staff seed password from environment variable if provided."""
    env_name = f"DEMO_{role.upper()}_PASSWORD"
    return os.getenv(env_name, fallback)


def seed_database(
    db: Database,
    tenant_service: TenantService,
    user_service: UserService,
    patient_service: PatientService,
    screening_service: ScreeningService,
    sample_images_dir: str = "",
) -> None:
    """Populates initial multi-tenant hospitals, staff, Indian patient cohort, and screenings."""
    with db.session() as conn:
        existing_tenants = conn.execute("SELECT COUNT(*) as c FROM tenants").fetchone()["c"]
        if existing_tenants > 0:
            logger.info("Database already seeded with %d tenants. Skipping seed.", existing_tenants)
            return

    logger.info("Seeding database with realistic Indian multi-tenant hospital cohort...")

    # 1. Onboard Hospitals & Staff
    user_id_map: Dict[str, str] = {}
    for h in HOSPITALS_DATA:
        t = tenant_service.create_tenant(
            tenant_id=h["id"],
            name=h["name"],
            city=h["city"],
            state=h["state"],
            address=h["address"],
            contact_email=h["contact_email"],
            contact_phone=h["contact_phone"],
            registration_number=h["registration_number"],
            logo_url=h["logo_url"],
            tier=h["tier"],
        )
        for u in h["users"]:
            staff_password = get_seed_password(u["role"], u.get("password", "admin123"))
            created_u = user_service.create_user(
                tenant_id=t.id,
                username=u["username"],
                password=staff_password,
                full_name=u["full_name"],
                role=u["role"],
                email=u["email"],
                phone=u["phone"],
                qualification=u["qualification"],
            )
            user_id_map[u["username"]] = created_u.id

    # 2. Register Indian Patient Cohort & Screenings
    for idx, p in enumerate(PATIENTS_SEEDS, 1):
        tid = p["tenant_id"]
        # Determine assigned doctor from hospital staff
        if tid == "apex-retina-lucknow":
            doc_id = user_id_map.get("dr_saxena")
            op_id = user_id_map.get("screener_rajesh")
        elif tid == "shroff-eye-delhi":
            doc_id = user_id_map.get("dr_batra")
            op_id = user_id_map.get("screener_sunita")
        else:
            doc_id = user_id_map.get("dr_hegde")
            op_id = user_id_map.get("screener_karthik")

        avatar = get_avatar(f"{p['first_name']}_{p['last_name']}", p["gender"])
        pat_id = f"PAT-IND-{1000 + idx}"

        patient = patient_service.register_patient(
            tenant_id=tid,
            patient_id=pat_id,
            first_name=p["first_name"],
            last_name=p["last_name"],
            gender=p["gender"],
            dob=p["dob"],
            age=p["age"],
            phone=p["phone"],
            email=p["email"],
            address=p["address"],
            city=p["city"],
            state=p["state"],
            pincode=p["pincode"],
            avatar_url=avatar,
            diabetes_type=p["diabetes_type"],
            diabetes_duration_years=p["diabetes_duration_years"],
            hba1c=p["hba1c"],
            insulin_dependent=p["insulin_dependent"],
            hypertension=p["hypertension"],
            smoker=p["smoker"],
            assigned_doctor_id=doc_id,
            is_minor=p.get("is_minor", 0),
            guardian_name=p.get("guardian_name"),
            guardian_relation=p.get("guardian_relation"),
            guardian_phone=p.get("guardian_phone"),
            clinical_notes=p["clinical_notes"],
            is_demo=1,
        )

        # 3. Create realistic historical screening record
        scr_info = p.get("screening")
        if scr_info:
            grade = scr_info["grade"]
            conf = scr_info["confidence"]
            eye = scr_info["eye"]
            diagnosis = GRADE_LABELS.get(grade, f"Grade {grade}")
            severity = GRADE_SEVERITY.get(grade, "Normal")
            recommendation = GRADE_RECOMMENDATIONS.get(grade, "Routine follow-up.")

            # Synthetic calibrated probability distribution
            probs: Dict[str, float] = {}
            for g in range(5):
                label = GRADE_LABELS[g]
                if g == grade:
                    probs[label] = conf
                else:
                    rem = round((100.0 - conf) / 4.0, 1)
                    probs[label] = max(0.5, rem)

            # Map image path
            img_filename = scr_info.get("sample", "grade0_14197_left-600.jpg")
            img_url = f"/sample_images/{img_filename}"

            status = "Completed"
            if grade >= 3:
                status = "Urgent Specialist Review"
            elif grade in (1, 2):
                status = "Referred"

            # Historical date staggered over past 6 months
            days_ago = (idx * 5) % 150
            scr_date = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()

            screening_service.create_demo_screening(
                tenant_id=tid,
                patient_id=patient.id,
                eye=eye,
                grade=grade,
                diagnosis=diagnosis,
                confidence=conf,
                severity=severity,
                probabilities=probs,
                recommendation=recommendation,
                original_image_path=img_url,
                heatmap_image_path=img_url,
                operator_id=op_id,
                doctor_id=doc_id,
                status=status,
                created_at=scr_date,
            )

    logger.info("Successfully seeded database with 3 hospitals, 9 staff, and 36 realistic Indian patients.")

