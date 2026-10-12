"""Relational Database ORM Models using SQLAlchemy 2.0.

Normalized 3NF schema covering patients, encounters, diagnoses, medications,
lab results, outcomes, audit logging, RBAC users, and ETL batch tracking.
"""

from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""
    pass


class User(Base):
    """System User for Role-Based Access Control (RBAC)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # 'administrator', 'clinical_operations', 'analyst'
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AdmissionType(Base):
    """Lookup mapping for hospital admission type."""
    __tablename__ = "admission_types"

    admission_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False)

    encounters: Mapped[List["Encounter"]] = relationship("Encounter", back_populates="admission_type")


class DischargeDisposition(Base):
    """Lookup mapping for discharge destination/status."""
    __tablename__ = "discharge_dispositions"

    discharge_disposition_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    encounters: Mapped[List["Encounter"]] = relationship("Encounter", back_populates="discharge_disposition")


class AdmissionSource(Base):
    """Lookup mapping for admission origin/referral source."""
    __tablename__ = "admission_sources"

    admission_source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    encounters: Mapped[List["Encounter"]] = relationship("Encounter", back_populates="admission_source")


class Patient(Base):
    """Normalized Patient Demographic Master."""
    __tablename__ = "patients"

    patient_nbr: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    race: Mapped[str] = mapped_column(String(50), default="Unknown", nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="Unknown", nullable=False)
    age_bracket: Mapped[str] = mapped_column(String(20), default="Unknown", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    encounters: Mapped[List["Encounter"]] = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_patients_race_gender", "race", "gender"),
    )


class Encounter(Base):
    """Clinical Encounter Record."""
    __tablename__ = "encounters"

    encounter_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_nbr: Mapped[int] = mapped_column(Integer, ForeignKey("patients.patient_nbr", ondelete="CASCADE"), index=True, nullable=False)
    admission_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("admission_types.admission_type_id"), nullable=False, index=True)
    discharge_disposition_id: Mapped[int] = mapped_column(Integer, ForeignKey("discharge_dispositions.discharge_disposition_id"), nullable=False, index=True)
    admission_source_id: Mapped[int] = mapped_column(Integer, ForeignKey("admission_sources.admission_source_id"), nullable=False)
    
    admission_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    discharge_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_in_hospital: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # Length of Stay (LOS) in days
    
    payer_code: Mapped[Optional[str]] = mapped_column(String(20), default="Unknown")
    medical_specialty: Mapped[Optional[str]] = mapped_column(String(100), default="Unknown")
    
    num_lab_procedures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_procedures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_medications: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    number_outpatient: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    number_emergency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    number_inpatient: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    number_diagnoses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="encounters")
    admission_type: Mapped["AdmissionType"] = relationship("AdmissionType", back_populates="encounters")
    discharge_disposition: Mapped["DischargeDisposition"] = relationship("DischargeDisposition", back_populates="encounters")
    admission_source: Mapped["AdmissionSource"] = relationship("AdmissionSource", back_populates="encounters")
    
    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis", back_populates="encounter", cascade="all, delete-orphan")
    lab_result: Mapped[Optional["LabResult"]] = relationship("LabResult", back_populates="encounter", uselist=False, cascade="all, delete-orphan")
    medications: Mapped[List["Medication"]] = relationship("Medication", back_populates="encounter", cascade="all, delete-orphan")
    outcome: Mapped[Optional["Outcome"]] = relationship("Outcome", back_populates="encounter", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_encounters_los_admtype", "time_in_hospital", "admission_type_id"),
    )


class Diagnosis(Base):
    """Clinical Diagnoses (ICD-9 codes) mapped to clinical category."""
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    encounter_id: Mapped[int] = mapped_column(Integer, ForeignKey("encounters.encounter_id", ondelete="CASCADE"), index=True, nullable=False)
    diag_seq: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = Primary, 2 = Secondary, 3 = Additional
    icd9_code: Mapped[str] = mapped_column(String(20), nullable=False)
    category_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="diagnoses")


class LabResult(Base):
    """Laboratory test outcomes for encounter."""
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    encounter_id: Mapped[int] = mapped_column(Integer, ForeignKey("encounters.encounter_id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    max_glu_serum: Mapped[str] = mapped_column(String(20), default="None", nullable=False)
    a1c_result: Mapped[str] = mapped_column(String(20), default="None", nullable=False)

    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="lab_result")


class Medication(Base):
    """Medications prescribed and dosage adjustments during encounter."""
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    encounter_id: Mapped[int] = mapped_column(Integer, ForeignKey("encounters.encounter_id", ondelete="CASCADE"), index=True, nullable=False)
    medication_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dosage_change: Mapped[str] = mapped_column(String(20), nullable=False)  # 'No', 'Steady', 'Up', 'Down'
    diabetes_med: Mapped[str] = mapped_column(String(10), default="Yes", nullable=False)
    med_changed: Mapped[str] = mapped_column(String(10), default="No", nullable=False)

    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="medications")


class Outcome(Base):
    """Encounter outcome: Readmission and Mortality metrics."""
    __tablename__ = "outcomes"

    encounter_id: Mapped[int] = mapped_column(Integer, ForeignKey("encounters.encounter_id", ondelete="CASCADE"), primary_key=True)
    readmitted_raw: Mapped[str] = mapped_column(String(10), nullable=False)  # 'NO', '>30', '<30'
    readmitted_30d: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_mortality: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="outcome")


class AuditLog(Base):
    """HIPAA and Operational Audit Trail recording record mutations."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # 'CREATE', 'UPDATE', 'DELETE', 'EXPORT', 'ETL'
    entity_name: Mapped[str] = mapped_column(String(50), nullable=False)  # 'patient', 'encounter', 'report', 'batch'
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ETLBatch(Base):
    """Metadata tracking for initial and incremental ETL batch executions."""
    __tablename__ = "etl_batches"

    batch_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    batch_type: Mapped[str] = mapped_column(String(30), nullable=False)  # 'INITIAL', 'INCREMENTAL'
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_clean: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_flagged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
