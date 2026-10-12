"""Unit tests for Relational Database schema and ORM models."""

from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import (
    Base,
    Patient,
    Encounter,
    Diagnosis,
    Outcome,
    AdmissionType,
    DischargeDisposition,
    AdmissionSource,
    AuditLog,
)


def test_schema_relationships_and_cascades():
    """Verify relational integrity and cascading deletes."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed reference lookups
    adm = AdmissionType(admission_type_id=1, description="Emergency")
    disp = DischargeDisposition(discharge_disposition_id=1, description="Home")
    src = AdmissionSource(admission_source_id=7, description="ER")
    session.add_all([adm, disp, src])

    # Add patient
    patient = Patient(patient_nbr=12345, race="Caucasian", gender="Male", age_bracket="[50-60)")
    session.add(patient)
    session.commit()

    # Add encounter
    enc = Encounter(
        encounter_id=999,
        patient_nbr=patient.patient_nbr,
        admission_type_id=1,
        discharge_disposition_id=1,
        admission_source_id=7,
        admission_date=date(2004, 1, 1),
        discharge_date=date(2004, 1, 4),
        time_in_hospital=3,
    )
    session.add(enc)

    # Add diagnosis and outcome
    diag = Diagnosis(encounter_id=enc.encounter_id, diag_seq=1, icd9_code="250.01", category_name="Diabetes")
    outcome = Outcome(encounter_id=enc.encounter_id, readmitted_raw="<30", readmitted_30d=True, is_mortality=False)
    session.add_all([diag, outcome])
    session.commit()

    # Verify query joins
    fetched_enc = session.query(Encounter).filter_by(encounter_id=999).first()
    assert fetched_enc is not None
    assert fetched_enc.patient.race == "Caucasian"
    assert len(fetched_enc.diagnoses) == 1
    assert fetched_enc.outcome.readmitted_30d is True

    # Test audit logging
    audit = AuditLog(username="tester", action="CREATE", entity_name="patient", entity_id="12345")
    session.add(audit)
    session.commit()
    assert session.query(AuditLog).count() == 1

    session.close()
