"""Healthcare Patient Management System - Streamlit Operational Portal.

Features a dedicated authentication login page, Role-Based Access Control (RBAC),
live clinical dashboards, patient CRUD operations, ETL management, and audit logs.
"""

import os
import sys
import json
import requests
import pandas as pd
import streamlit as st

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.database.connection import init_db, SessionLocal
from src.database.models import User, ETLBatch, AuditLog, Patient, Encounter
from src.services.analytics_service import AnalyticsService
from src.services.patient_service import PatientService
from src.services.encounter_service import EncounterService
from src.services.report_service import ReportService
from src.etl.pipeline import HealthcareETLPipeline
from src.utils.auth import verify_password, create_access_token

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="Healthcare Patient Management System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Database Schema & Seed Roles (only once per session)
@st.cache_resource
def _init_db_once():
    init_db()

_init_db_once()

# Custom Medical Theme Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .badge-admin {
        background-color: #DC2626;
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-clinical {
        background-color: #2563EB;
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-analyst {
        background-color: #059669;
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# Cached query functions (5-min cache to prevent repeated expensive DB scans)
@st.cache_data(ttl=300)
def get_kpis():
    with SessionLocal() as db:
        return AnalyticsService.get_summary_kpis(db)

@st.cache_data(ttl=300)
def get_trends():
    with SessionLocal() as db:
        return AnalyticsService.get_admissions_trend(db)

@st.cache_data(ttl=300)
def get_cohorts():
    with SessionLocal() as db:
        return AnalyticsService.get_los_by_cohort(db)

@st.cache_data(ttl=300)
def get_readmission_cats():
    with SessionLocal() as db:
        return AnalyticsService.get_readmission_by_category(db)

@st.cache_data(ttl=300)
def get_med_impact():
    with SessionLocal() as db:
        return AnalyticsService.get_medication_impact(db)

@st.cache_data(ttl=300)
def get_csv_export(limit: int):
    with SessionLocal() as db:
        return ReportService.export_to_csv(db, limit=limit)

@st.cache_data(ttl=300)
def get_excel_export(limit: int):
    with SessionLocal() as db:
        return ReportService.export_to_excel(db, limit=limit)

@st.cache_data(ttl=300)
def get_exec_summary():
    with SessionLocal() as db:
        return ReportService.generate_executive_summary_report(db)


# -------------------------------------------------------------
# SESSION STATE MANAGEMENT & AUTHENTICATION GUARD
# -------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "token" not in st.session_state:
    st.session_state.token = None


def authenticate_user(username: str, password: str) -> bool:
    """Verify user against database credentials and store session state."""
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username.strip()).first()
        if user and user.is_active and verify_password(password, user.hashed_password):
            token = create_access_token(data={"sub": user.username, "role": user.role})
            st.session_state.authenticated = True
            st.session_state.user = {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "full_name": user.full_name,
            }
            st.session_state.token = token
            return True
        return False


def logout_user():
    """Clear session state and redirect to login."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.token = None
    st.rerun()


# -------------------------------------------------------------
# DEDICATED LOGIN PAGE (Rendered when unauthenticated)
# -------------------------------------------------------------
if not st.session_state.authenticated:
    _, header_col, _ = st.columns([1, 2, 1])
    with header_col:
        st.markdown('<div style="text-align: center; font-size: 3rem; margin-bottom: 1rem;">🏥</div>', unsafe_allow_html=True)
        st.markdown('<div class="main-title" style="text-align: center;">Healthcare Patient Management System</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title" style="text-align: center;">Secure Inpatient Analytics & Clinical Administration Portal</div>', unsafe_allow_html=True)

    login_col1, login_col2, login_col3 = st.columns([1, 1.6, 1])

    with login_col2:
        with st.container(border=True):
            st.subheader("Sign In with Authorized Credentials")

            with st.form("login_form", border=False):
                username_input = st.text_input("Username", placeholder="e.g. admin, clinician, analyst")
                password_input = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_login = st.form_submit_button("Sign In to Portal", use_container_width=True)

                if submit_login:
                    if authenticate_user(username_input, password_input):
                        st.success("Authentication successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify your username and password.")

    st.stop()  # Halt execution until authenticated


# -------------------------------------------------------------
# AUTHENTICATED PORTAL (Rendered once logged in)
# -------------------------------------------------------------
current_user = st.session_state.user
current_username = current_user["username"]
current_user_role = current_user["role"]
current_user_name = current_user["full_name"]

# Sidebar Profile Header
st.sidebar.markdown('🏥', unsafe_allow_html=True)
st.sidebar.markdown(f"**{current_user_name}**")

if current_user_role == "administrator":
    st.sidebar.markdown('<span class="badge-admin">Administrator</span>', unsafe_allow_html=True)
elif current_user_role == "clinical_operations":
    st.sidebar.markdown('<span class="badge-clinical">Clinical Operations</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="badge-analyst">Data Analyst (Read-Only)</span>', unsafe_allow_html=True)

if st.sidebar.button("🚪 Sign Out", key="logout_btn", use_container_width=True):
    logout_user()

st.sidebar.divider()

# Navigation depending on role
nav_options = [
    "📊 Executive KPI Dashboard",
    "📈 Clinical Analytics & Trends",
    "🧑‍⚕️ Patient & Encounter Management",
    "⚡ ETL Ingestion & Data Quality",
    "📄 Reports & Exports",
]
if current_user_role == "administrator":
    nav_options.append("🛡️ System Audit Logs")

page = st.sidebar.radio("Navigation", nav_options)

st.sidebar.divider()
st.sidebar.caption("Healthcare Patient Management System v1.0.0")


# -------------------------------------------------------------
# PAGE 1: EXECUTIVE KPI DASHBOARD
# -------------------------------------------------------------
if page == "📊 Executive KPI Dashboard":
    st.markdown('<div class="main-title">Executive Operational Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Real-time hospital admissions, Length of Stay, and readmission indicators</div>', unsafe_allow_html=True)

    kpis = get_kpis()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Patients", f"{kpis['total_patients']:,}")
    col2.metric("Total Encounters", f"{kpis['total_encounters']:,}")
    col3.metric("Avg Length of Stay", f"{kpis['avg_length_of_stay']} Days")
    col4.metric("30-Day Readmission", f"{kpis['readmission_rate_30d_pct']}%", delta=f"{kpis['readmitted_30d_count']} cases", delta_color="inverse")
    col5.metric("In-Hospital Mortality", f"{kpis['mortality_rate_pct']}%", delta=f"{kpis['mortality_count']} cases", delta_color="inverse")

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Monthly Admissions & 30-Day Readmission Trends")
        trends = get_trends()
        if trends:
            df_trends = pd.DataFrame(trends)
            st.line_chart(df_trends.set_index("period")[["admissions", "readmissions_30d"]])
        else:
            st.info("No trend data available. Ingest dataset to populate trends.")

    with chart_col2:
        st.subheader("Length of Stay by Patient Age Bracket")
        cohorts = get_cohorts()
        if cohorts.get("by_age"):
            df_age = pd.DataFrame(cohorts["by_age"])
            st.bar_chart(df_age.set_index("age_bracket")["avg_los"])
        else:
            st.info("No age cohort data available.")

    st.subheader("30-Day Readmissions by Admission Type")
    cat_data = get_readmission_cats()
    if cat_data.get("by_admission_type"):
        df_adm = pd.DataFrame(cat_data["by_admission_type"])
        st.dataframe(df_adm, use_container_width=True)


# -------------------------------------------------------------
# PAGE 2: CLINICAL ANALYTICS & TRENDS
# -------------------------------------------------------------
elif page == "📈 Clinical Analytics & Trends":
    st.markdown('<div class="main-title">Clinical Trends & Readmission Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Detailed cohort analysis addressing core capstone research questions</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Readmission by Diagnosis", "Length of Stay Drivers", "Medication Regimen Impact"])

    with tab1:
        st.subheader("Readmission Rates by Primary Diagnosis Category")
        st.write("Identifies high-risk clinical categories contributing disproportionately to rapid 30-day readmissions.")
        cat_data = get_readmission_cats()
        if cat_data.get("by_diagnosis"):
            df_diag = pd.DataFrame(cat_data["by_diagnosis"])
            st.bar_chart(df_diag.set_index("category")["readmission_rate_pct"])
            st.dataframe(df_diag, use_container_width=True)
        else:
            st.info("No diagnosis data available.")

    with tab2:
        st.subheader("Length of Stay Variations Across Admission Categories")
        st.write("Examines how clinical acuity (Emergency vs Urgent vs Elective) impacts hospital utilization.")
        cohort_data = get_cohorts()
        if cohort_data.get("by_admission_type"):
            df_adm = pd.DataFrame(cohort_data["by_admission_type"])
            st.dataframe(df_adm, use_container_width=True)
            st.bar_chart(df_adm.set_index("admission_type")["avg_los"])

    with tab3:
        st.subheader("Insulin Dosage Changes vs 30-Day Readmission Rate")
        st.write("Analyzes clinical outcomes across patients with unchanged, increased, or decreased insulin regimens.")
        med_impact = get_med_impact()
        if med_impact:
            df_med = pd.DataFrame(med_impact)
            st.dataframe(df_med, use_container_width=True)
            st.bar_chart(df_med.set_index("insulin_status")["readmission_rate_pct"])
        else:
            st.info("No medication impact data available.")


# -------------------------------------------------------------
# PAGE 3: PATIENT & ENCOUNTER MANAGEMENT (CRUD)
# -------------------------------------------------------------
elif page == "🧑‍⚕️ Patient & Encounter Management":
    st.markdown('<div class="main-title">Patient & Encounter Management Portal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Authorized CRUD operations, clinical search, and historical records</div>', unsafe_allow_html=True)

    with SessionLocal() as db:
        tab_enc, tab_pat, tab_new = st.tabs(["🏥 Encounter Explorer & Editor", "🧑‍⚕️ Patient Directory", "➕ Register New Patient / Encounter"])

        # -------------------------------------------------------------
        # TAB 1: ENCOUNTER EXPLORER & EDITOR (All 101,766 Encounters)
        # -------------------------------------------------------------
        with tab_enc:
            st.subheader("Clinical Encounter Search, Pagination & Live Editor")
            st.write("Browse and edit any of the **101,766** historical hospital encounter records.")

            f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1, 1, 1])
            with f_col1:
                enc_search = st.text_input("Search Encounter ID or Patient ID", "", placeholder="e.g. 2278392 or 8222157")
            with f_col2:
                enc_readmit = st.selectbox("Readmission Status", ["All", "NO", ">30", "<30"], index=0)
            with f_col3:
                enc_sort = st.selectbox("Sort By", ["admission_date", "time_in_hospital", "encounter_id"], index=0)
            with f_col4:
                enc_order = st.selectbox("Sort Order", ["desc", "asc"], index=0)

            # Pagination parameters
            p_col1, p_col2 = st.columns([1, 2])
            with p_col1:
                page_size = st.selectbox("Encounters per Page", [25, 50, 100, 200], index=1)

            # Resolve patient_nbr or encounter_id search
            pat_search_id = int(enc_search) if enc_search.strip().isdigit() and len(enc_search.strip()) < 9 else None

            # Count and fetch
            all_encs, total_enc_matches = EncounterService.get_encounters(
                db=db,
                skip=0,
                limit=1,
                patient_nbr=pat_search_id,
                readmitted=enc_readmit if enc_readmit != "All" else None,
                sort_by=enc_sort,
                sort_order=enc_order,
            )

            total_pages = max(1, (total_enc_matches + page_size - 1) // page_size)
            page_num = p_col2.number_input("Page Number", min_value=1, max_value=total_pages, value=1, step=1)
            st.caption(f"Displaying Page **{page_num}** of **{total_pages:,}** | Total matching encounters: **{total_enc_matches:,}**")

            # Fetch page data
            page_encounters, _ = EncounterService.get_encounters(
                db=db,
                skip=(page_num - 1) * page_size,
                limit=page_size,
                patient_nbr=pat_search_id,
                readmitted=enc_readmit if enc_readmit != "All" else None,
                sort_by=enc_sort,
                sort_order=enc_order,
            )

            if page_encounters:
                enc_table_data = [
                    {
                        "Encounter ID": e.encounter_id,
                        "Patient ID": e.patient_nbr,
                        "Admission Date": str(e.admission_date),
                        "Discharge Date": str(e.discharge_date),
                        "LOS (Days)": e.time_in_hospital,
                        "Specialty": e.medical_specialty,
                        "Medications": e.num_medications,
                        "Lab Procedures": e.num_lab_procedures,
                        "Readmission": e.outcome.readmitted_raw if e.outcome else "N/A",
                    }
                    for e in page_encounters
                ]
                st.dataframe(pd.DataFrame(enc_table_data), use_container_width=True)

                st.divider()
                st.subheader("Edit Encounter Record")

                # Choose encounter from current page or type direct ID
                page_enc_ids = [e.encounter_id for e in page_encounters]
                target_enc_id = st.selectbox("Select Encounter ID from Current View to Edit", page_enc_ids)

                manual_enc_id = st.text_input("Or Enter Any Specific Encounter ID to Edit", value=str(target_enc_id))
                active_enc_id = int(manual_enc_id) if manual_enc_id.strip().isdigit() else target_enc_id

                target_enc = EncounterService.get_encounter_by_id(db, active_enc_id)

                if target_enc:
                    st.info(f"Loaded Encounter **#{target_enc.encounter_id}** for Patient **#{target_enc.patient_nbr}** (Admission: {target_enc.admission_date})")

                    if current_user_role in ["administrator", "clinical_operations"]:
                        with st.form("edit_encounter_form"):
                            e_c1, e_c2, e_c3 = st.columns(3)
                            with e_c1:
                                new_los = st.slider("Length of Stay (Days)", min_value=1, max_value=14, value=int(target_enc.time_in_hospital))
                                new_spec = st.text_input("Medical Specialty", value=str(target_enc.medical_specialty or "Unknown"))
                            with e_c2:
                                new_meds = st.number_input("Number of Medications", min_value=0, max_value=100, value=int(target_enc.num_medications))
                                new_labs = st.number_input("Number of Lab Procedures", min_value=0, max_value=200, value=int(target_enc.num_lab_procedures))
                            with e_c3:
                                current_readmit = target_enc.outcome.readmitted_raw if target_enc.outcome else "NO"
                                readmit_options = ["NO", ">30", "<30"]
                                readmit_idx = readmit_options.index(current_readmit) if current_readmit in readmit_options else 0
                                new_readmit = st.selectbox("Readmission Status", readmit_options, index=readmit_idx)

                            save_enc_btn = st.form_submit_button("💾 Save Encounter Updates")

                            if save_enc_btn:
                                EncounterService.update_encounter(
                                    db=db,
                                    encounter_id=active_enc_id,
                                    update_data={
                                        "time_in_hospital": new_los,
                                        "medical_specialty": new_spec,
                                        "num_medications": new_meds,
                                        "num_lab_procedures": new_labs,
                                        "readmitted_raw": new_readmit,
                                    },
                                    username=current_username,
                                )
                                st.success(f"Encounter #{active_enc_id} successfully updated and recorded in audit logs!")
                                st.rerun()

                        if current_user_role == "administrator":
                            with st.expander(f"Delete Encounter #{active_enc_id} (Admin Only)"):
                                st.warning("Deleting an encounter permanently removes this clinical record.")
                                if st.button("Confirm Delete Encounter", type="primary", key="del_enc_btn"):
                                    EncounterService.delete_encounter(db, active_enc_id, username=current_username)
                                    st.success(f"Encounter #{active_enc_id} deleted and audited.")
                                    st.rerun()
                    else:
                        st.warning("Analyst Role: Read-only access. Modification forms are disabled.")
                else:
                    st.error(f"Encounter ID {active_enc_id} not found in database.")
            else:
                st.info("No encounters found matching the specified filters.")

        # -------------------------------------------------------------
        # TAB 2: PATIENT DIRECTORY
        # -------------------------------------------------------------
        with tab_pat:
            st.subheader("Patient Master Directory & Timeline")
            search_col1, search_col2, search_col3 = st.columns([2, 1, 1])
            with search_col1:
                pat_search_term = st.text_input("Search Patient ID, Race, or Gender", "")
            with search_col2:
                gender_filter = st.selectbox("Gender Filter", ["All", "Male", "Female", "Unknown"])
            with search_col3:
                age_filter = st.selectbox("Age Bracket Filter", ["All", "[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)", "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"])

            # Patient Pagination
            pat_p_col1, pat_p_col2 = st.columns([1, 2])
            with pat_p_col1:
                pat_page_size = st.selectbox("Patients per Page", [25, 50, 100], index=0)

            _, total_pat_count = PatientService.get_patients(
                db=db,
                skip=0,
                limit=1,
                search=pat_search_term if pat_search_term else None,
                gender=gender_filter,
                age_bracket=age_filter,
            )

            total_pat_pages = max(1, (total_pat_count + pat_page_size - 1) // pat_page_size)
            pat_page_num = pat_p_col2.number_input("Patient Page", min_value=1, max_value=total_pat_pages, value=1, step=1)
            st.caption(f"Showing Page **{pat_page_num}** of **{total_pat_pages:,}** | Total patients: **{total_pat_count:,}**")

            patients, _ = PatientService.get_patients(
                db=db,
                skip=(pat_page_num - 1) * pat_page_size,
                limit=pat_page_size,
                search=pat_search_term if pat_search_term else None,
                gender=gender_filter,
                age_bracket=age_filter,
            )

            if patients:
                patient_data = [
                    {
                        "Patient ID": p.patient_nbr,
                        "Race": p.race,
                        "Gender": p.gender,
                        "Age Bracket": p.age_bracket,
                        "Created At": p.created_at.strftime("%Y-%m-%d %H:%M"),
                    }
                    for p in patients
                ]
                st.dataframe(pd.DataFrame(patient_data), use_container_width=True)

                st.subheader("Inspect Patient Clinical Encounters")
                pat_id_list = [p.patient_nbr for p in patients]
                p_sel_col1, p_sel_col2 = st.columns([1, 1])
                with p_sel_col1:
                    selected_patient_id = st.selectbox("Select Patient ID from Current Page", pat_id_list)
                with p_sel_col2:
                    manual_pat_id = st.text_input("Or Enter Any Specific Patient ID", value=str(selected_patient_id) if selected_patient_id else "")

                active_patient_id = int(manual_pat_id) if manual_pat_id.strip().isdigit() else selected_patient_id
                target_patient = PatientService.get_patient_by_id(db, active_patient_id)

                if target_patient:
                    st.info(f"Loaded Patient **#{target_patient.patient_nbr}** | Demographics: {target_patient.race}, {target_patient.gender}, Age: {target_patient.age_bracket}")

                    pat_encounters, _ = EncounterService.get_encounters(db, patient_nbr=active_patient_id, limit=50)
                    if pat_encounters:
                        p_enc_data = [
                            {
                                "Encounter ID": e.encounter_id,
                                "Admission Date": str(e.admission_date),
                                "Discharge Date": str(e.discharge_date),
                                "Length of Stay (Days)": e.time_in_hospital,
                                "Specialty": e.medical_specialty,
                                "Medications": e.num_medications,
                                "Readmission": e.outcome.readmitted_raw if e.outcome else "N/A",
                            }
                            for e in pat_encounters
                        ]
                        st.write(f"Clinical Encounter Timeline ({len(pat_encounters)} recorded visits):")
                        st.dataframe(pd.DataFrame(p_enc_data), use_container_width=True)
                    else:
                        st.info("No recorded clinical encounters for this patient.")

                    # Edit / Delete Section
                    if current_user_role in ["administrator", "clinical_operations"]:
                        with st.expander(f"Edit Demographics for Patient #{active_patient_id}"):
                            races = ["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other", "Unknown"]
                            race_idx = races.index(target_patient.race) if target_patient.race in races else races.index("Unknown")
                            ages = ["[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)", "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"]
                            age_idx = ages.index(target_patient.age_bracket) if target_patient.age_bracket in ages else 0

                            edit_col1, edit_col2 = st.columns(2)
                            with edit_col1:
                                new_race = st.selectbox("Update Race", races, index=race_idx)
                            with edit_col2:
                                new_age = st.selectbox("Update Age Bracket", ages, index=age_idx)

                            if st.button("Save Patient Demographics", key="update_patient_btn"):
                                PatientService.update_patient(
                                    db,
                                    patient_nbr=active_patient_id,
                                    update_data={"race": new_race, "age_bracket": new_age},
                                    username=current_username,
                                    )
                                st.success("Patient details updated and logged to audit trail!")
                                st.rerun()

                    if current_user_role == "administrator":
                        with st.expander(f"Delete Patient #{active_patient_id} (Admin Only)"):
                            st.warning("Deleting a patient permanently removes the patient record and all associated clinical encounters.")
                            if st.button("Confirm Delete Patient", type="primary", key="del_patient_btn"):
                                PatientService.delete_patient(db, patient_nbr=active_patient_id, username=current_username)
                                st.success("Patient deleted and logged to audit trail.")
                                st.rerun()
                else:
                    st.error(f"Patient ID {active_patient_id} not found in database.")

        # -------------------------------------------------------------
        # TAB 3: REGISTER NEW PATIENT / ENCOUNTER
        # -------------------------------------------------------------
        with tab_new:
            if current_user_role == "analyst":
                st.warning("Analyst Role: Creation forms are disabled.")
            else:
                form_type = st.radio("Record Type to Create", ["New Patient", "New Encounter"], horizontal=True)

                if form_type == "New Patient":
                    st.subheader("Register New Patient")
                    with st.form("new_patient_form"):
                        f_id = st.number_input("Patient ID (patient_nbr)", min_value=100000, max_value=999999999, value=88888001)
                        f_race = st.selectbox("Race", ["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other", "Unknown"])
                        f_gender = st.selectbox("Gender", ["Female", "Male", "Unknown"])
                        f_age = st.selectbox("Age Bracket", ["[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)", "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"], index=5)
                        submit_btn = st.form_submit_button("Create Patient Record")

                        if submit_btn:
                            existing = PatientService.get_patient_by_id(db, f_id)
                            if existing:
                                st.error(f"Patient ID {f_id} already exists!")
                            else:
                                PatientService.create_patient(
                                    db,
                                    {"patient_nbr": f_id, "race": f_race, "gender": f_gender, "age_bracket": f_age},
                                    username=current_username,
                                )
                                st.success(f"Patient {f_id} successfully created and audited!")

                elif form_type == "New Encounter":
                    st.subheader("Record Clinical Encounter")
                    with st.form("new_encounter_form"):
                        enc_id = st.number_input("Encounter ID", min_value=100000, max_value=999999999, value=99999001)
                        enc_pat_id = st.number_input("Patient ID", min_value=100000, max_value=999999999, value=88888001)
                        enc_los = st.slider("Length of Stay (Days)", min_value=1, max_value=14, value=3)
                        enc_specialty = st.text_input("Medical Specialty", "InternalMedicine")
                        enc_meds = st.slider("Number of Medications", min_value=1, max_value=50, value=12)
                        enc_readmit = st.selectbox("Readmission Outcome", ["NO", ">30", "<30"])
                        enc_submit = st.form_submit_button("Record Encounter")

                        if enc_submit:
                            existing = EncounterService.get_encounter_by_id(db, enc_id)
                            if existing:
                                st.error(f"Encounter ID {enc_id} already exists!")
                            else:
                                pat = PatientService.get_patient_by_id(db, enc_pat_id)
                                if not pat:
                                    PatientService.create_patient(db, {"patient_nbr": enc_pat_id}, username=current_username)

                                EncounterService.create_encounter(
                                    db,
                                    {
                                        "encounter_id": enc_id,
                                        "patient_nbr": enc_pat_id,
                                        "time_in_hospital": enc_los,
                                        "medical_specialty": enc_specialty,
                                        "num_medications": enc_meds,
                                        "readmitted_raw": enc_readmit,
                                    },
                                    username=current_username,
                                )
                                st.success(f"Encounter #{enc_id} recorded and logged to audit trail!")


# -------------------------------------------------------------
# PAGE 4: ETL INGESTION & DATA QUALITY
# -------------------------------------------------------------
elif page == "⚡ ETL Ingestion & Data Quality":
    st.markdown('<div class="main-title">ETL Ingestion & Data Quality Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Ingest historical datasets and upload incremental encounter batches</div>', unsafe_allow_html=True)

    with SessionLocal() as db:
        if current_user_role != "administrator":
            st.warning("Note: ETL ingestion and data quality controls require Administrator privileges.")

        st.subheader("1. Execute Ingestion from Dataset Files")
        project_root = os.path.dirname(__file__)
        data_csv_path = os.path.join(project_root, "diabetic_data.csv")
        mapping_csv_path = os.path.join(project_root, "IDS_mapping.csv")

        if not os.path.exists(data_csv_path):
            data_csv_path = os.path.join(project_root, "data", "diabetic_data.csv")
            mapping_csv_path = os.path.join(project_root, "data", "IDS_mapping.csv")

        st.info(f"Primary Ingestion Dataset: `{os.path.basename(data_csv_path)}` | Mapping: `{os.path.basename(mapping_csv_path)}`")

        col_run1, col_run2 = st.columns([1, 2])
        with col_run1:
            run_full_btn = st.button("Run Ingestion (diabetic_data.csv)", disabled=current_user_role != "administrator", type="primary")

        pipeline = HealthcareETLPipeline(db)

        if run_full_btn and current_user_role == "administrator":
            with st.spinner("Processing dataset through cleaning, data quality, and relational ingestion..."):
                result = pipeline.run_pipeline(data_csv_path, mapping_path=mapping_csv_path, batch_type="INITIAL")
                st.success("Ingestion completed successfully!")
                st.json(result)

        st.divider()
        st.subheader("2. Upload Incremental Batch CSV")
        uploaded_file = st.file_uploader("Upload Incremental Encounter CSV", type=["csv"], disabled=current_user_role != "administrator")

        if uploaded_file and current_user_role == "administrator":
            if st.button("Ingest Uploaded Batch"):
                try:
                    df = pd.read_csv(uploaded_file)
                    with st.spinner(f"Ingesting {len(df)} records..."):
                        result = pipeline.run_pipeline(df, mapping_path=mapping_csv_path, batch_type="INCREMENTAL")
                        st.success("Incremental batch ingested successfully!")
                        st.json(result)
                except Exception as e:
                    st.error(f"Error during ingestion: {str(e)}")

        st.divider()
        st.subheader("3. Historical ETL Batch Audits")
        batches = db.query(ETLBatch).order_by(ETLBatch.created_at.desc()).limit(15).all()
        if batches:
            batch_data = [
                {
                    "Batch ID": b.batch_id,
                    "Type": b.batch_type,
                    "Source": b.source_filename,
                    "Processed": b.records_processed,
                    "Clean Ingested": b.records_clean,
                    "Flagged": b.records_flagged,
                    "Status": b.status,
                    "Duration (s)": b.execution_time_seconds,
                    "Timestamp": b.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for b in batches
            ]
            st.dataframe(pd.DataFrame(batch_data), use_container_width=True)
        else:
            st.info("No batches recorded yet.")


# -------------------------------------------------------------
# PAGE 5: REPORTS & EXPORTS
# -------------------------------------------------------------
elif page == "📄 Reports & Exports":
    st.markdown('<div class="main-title">Operational Reports & Dataset Export</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Export curated patient records to CSV/Excel and generate executive summaries</div>', unsafe_allow_html=True)

    st.subheader("1. Export Filtered Encounters")
    record_limit = st.slider("Export Record Limit", min_value=100, max_value=20000, value=5000, step=1000)

    col_csv, col_excel = st.columns(2)
    with col_csv:
        if st.button("📥 Prepare CSV Download", key="csv_btn"):
            with st.spinner("Generating CSV..."):
                csv_stream = get_csv_export(record_limit)
                st.download_button(
                    label="📥 Download CSV Now",
                    data=csv_stream.getvalue(),
                    file_name="healthcare_encounters_export.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="csv_download",
                )

    with col_excel:
        if st.button("📊 Prepare Excel Download", key="excel_btn"):
            with st.spinner("Generating Excel..."):
                excel_stream = get_excel_export(record_limit)
                st.download_button(
                    label="📊 Download Excel Now",
                    data=excel_stream.getvalue(),
                    file_name="healthcare_encounters_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="excel_download",
                )

    st.divider()
    st.subheader("2. Automated Scheduled Executive Summary")
    if st.button("Generate Executive Summary Report"):
        with st.spinner("Generating summary..."):
            summary = get_exec_summary()
            st.json(summary)


# -------------------------------------------------------------
# PAGE 6: SYSTEM AUDIT LOGS (ADMIN ONLY)
# -------------------------------------------------------------
elif page == "🛡️ System Audit Logs":
    st.markdown('<div class="main-title">System & Security Audit Logs</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">HIPAA and governance audit trail recording all create, update, delete, and ETL mutations</div>', unsafe_allow_html=True)

    with SessionLocal() as db:
        action_filter = st.selectbox("Filter by Action", ["ALL", "CREATE", "UPDATE", "DELETE", "ETL_INGESTION"])

        query = db.query(AuditLog)
        if action_filter != "ALL":
            query = query.filter(AuditLog.action == action_filter)

        logs = query.order_by(AuditLog.timestamp.desc()).limit(50).all()

        if logs:
            log_data = [
                {
                    "Timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "User": l.username,
                    "Action": l.action,
                    "Entity": l.entity_name,
                    "Entity ID": l.entity_id,
                    "Details": l.details_json,
                }
                for l in logs
            ]
            st.dataframe(pd.DataFrame(log_data), use_container_width=True)
        else:
            st.info("No audit logs recorded matching criteria.")
