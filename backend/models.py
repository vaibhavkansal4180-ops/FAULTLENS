import json
from datetime import datetime, timezone, date
from werkzeug.security import generate_password_hash, check_password_hash
from backend.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="VIEWER")  # ADMIN, TECHNICIAN, VIEWER
    full_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    assigned_tasks = db.relationship("MaintenanceTask", foreign_keys="MaintenanceTask.assigned_to_id", backref="assignee", lazy="dynamic")
    verified_tasks = db.relationship("MaintenanceTask", foreign_keys="MaintenanceTask.verified_by_id", backref="verifier", lazy="dynamic")
    submitted_reports = db.relationship("IncidentReport", foreign_keys="IncidentReport.reporter_id", backref="reporter", lazy="dynamic")
    inspections = db.relationship("Inspection", foreign_keys="Inspection.inspector_id", backref="inspector", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TransformerAsset(db.Model):
    __tablename__ = "transformer_assets"

    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(30), unique=True, nullable=False, index=True)  # e.g., FL-042
    name = db.Column(db.String(120), nullable=False)
    substation = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    installation_date = db.Column(db.Date, nullable=False)
    manufacturer = db.Column(db.String(100), nullable=False)
    model_number = db.Column(db.String(100), nullable=False)
    rated_capacity_kva = db.Column(db.Float, nullable=False, default=500.0)
    primary_voltage_kv = db.Column(db.Float, default=33.0)
    secondary_voltage_kv = db.Column(db.Float, default=11.0)
    cooling_type = db.Column(db.String(50), default="ONAN")  # ONAN, ONAF, OFAF
    current_status = db.Column(db.String(30), nullable=False, default="OPERATIONAL")  # OPERATIONAL, MAINTENANCE_REQUIRED, UNDER_MAINTENANCE, DECOMMISSIONED
    last_inspection_date = db.Column(db.Date, nullable=True)
    last_maintenance_date = db.Column(db.Date, nullable=True)
    previous_failure_count = db.Column(db.Integer, default=0)
    current_risk_score = db.Column(db.Float, default=15.0)  # 0 to 100
    failure_probability = db.Column(db.Float, default=0.15)  # 0.00 to 1.00
    health_status = db.Column(db.String(20), default="HEALTHY")  # HEALTHY, MODERATE, HIGH, CRITICAL
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relational associations
    telemetry_readings = db.relationship("TelemetryReading", backref="asset", cascade="all, delete-orphan", lazy="dynamic")
    maintenance_records = db.relationship("MaintenanceRecord", backref="asset", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(MaintenanceRecord.date_performed)")
    inspections = db.relationship("Inspection", backref="asset", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(Inspection.inspection_date)")
    incident_reports = db.relationship("IncidentReport", backref="asset", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(IncidentReport.reported_at)")
    risk_assessments = db.relationship("RiskAssessment", backref="asset", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(RiskAssessment.assessment_date)")
    alerts = db.relationship("Alert", backref="asset", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(Alert.triggered_at)")
    maintenance_tasks = db.relationship("MaintenanceTask", backref="asset", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(MaintenanceTask.created_at)")

    @property
    def age_years(self) -> float:
        if not self.installation_date:
            return 0.0
        today = date.today()
        return round((today - self.installation_date).days / 365.25, 1)

    @property
    def days_since_maintenance(self) -> int:
        if not self.last_maintenance_date:
            return 999
        today = date.today()
        return (today - self.last_maintenance_date).days

    def to_dict(self, include_counts=False):
        data = {
            "id": self.id,
            "asset_tag": self.asset_tag,
            "name": self.name,
            "substation": self.substation,
            "location": self.location,
            "installation_date": self.installation_date.isoformat() if self.installation_date else None,
            "age_years": self.age_years,
            "manufacturer": self.manufacturer,
            "model_number": self.model_number,
            "rated_capacity_kva": self.rated_capacity_kva,
            "primary_voltage_kv": self.primary_voltage_kv,
            "secondary_voltage_kv": self.secondary_voltage_kv,
            "cooling_type": self.cooling_type,
            "current_status": self.current_status,
            "last_inspection_date": self.last_inspection_date.isoformat() if self.last_inspection_date else None,
            "last_maintenance_date": self.last_maintenance_date.isoformat() if self.last_maintenance_date else None,
            "days_since_maintenance": self.days_since_maintenance,
            "previous_failure_count": self.previous_failure_count,
            "current_risk_score": round(self.current_risk_score, 1),
            "failure_probability": round(self.failure_probability, 3),
            "failure_probability_pct": round(self.failure_probability * 100, 1),
            "health_status": self.health_status,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_counts:
            data["active_alerts_count"] = self.alerts.filter_by(status="ACTIVE").count()
            data["open_tasks_count"] = self.maintenance_tasks.filter(MaintenanceTask.status.notin_(["RESOLVED", "VERIFIED"])).count()
            data["incident_reports_count"] = self.incident_reports.count()
        return data


class TelemetryReading(db.Model):
    __tablename__ = "telemetry_readings"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("transformer_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    temperature_c = db.Column(db.Float, nullable=False)
    ambient_temp_c = db.Column(db.Float, default=25.0)
    voltage_v = db.Column(db.Float, nullable=False)
    current_a = db.Column(db.Float, nullable=False)
    load_pct = db.Column(db.Float, nullable=False)
    vibration_mms = db.Column(db.Float, nullable=False)
    oil_level_pct = db.Column(db.Float, default=95.0)
    is_anomaly = db.Column(db.Boolean, default=False)
    anomaly_details = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "temperature_c": round(self.temperature_c, 1),
            "ambient_temp_c": round(self.ambient_temp_c, 1),
            "voltage_v": round(self.voltage_v, 1),
            "current_a": round(self.current_a, 1),
            "load_pct": round(self.load_pct, 1),
            "vibration_mms": round(self.vibration_mms, 2),
            "oil_level_pct": round(self.oil_level_pct, 1),
            "is_anomaly": self.is_anomaly,
            "anomaly_details": self.anomaly_details,
        }


class MaintenanceRecord(db.Model):
    __tablename__ = "maintenance_records"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("transformer_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_type = db.Column(db.String(50), nullable=False)  # PREVENTIVE, CORRECTIVE, OVERHAUL, OIL_FILTERING
    performed_by = db.Column(db.String(100), nullable=False)
    date_performed = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=False)
    cost_usd = db.Column(db.Float, default=0.0)
    downtime_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "maintenance_type": self.maintenance_type,
            "performed_by": self.performed_by,
            "date_performed": self.date_performed.isoformat() if self.date_performed else None,
            "notes": self.notes,
            "cost_usd": self.cost_usd,
            "downtime_hours": self.downtime_hours,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Inspection(db.Model):
    __tablename__ = "inspections"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("transformer_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    inspector_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    inspector_name = db.Column(db.String(100), nullable=False)
    inspection_date = db.Column(db.Date, nullable=False)
    thermal_imaging_status = db.Column(db.String(50), default="NORMAL")  # NORMAL, HOTSPOT_DETECTED, SEVERE_OVERHEATING
    oil_quality_index = db.Column(db.Float, default=92.0)  # Dielectric strength / quality 0-100
    structural_integrity = db.Column(db.String(50), default="SATISFACTORY")  # EXCELLENT, SATISFACTORY, MINOR_CORROSION, STRUCTURAL_DEGRADATION
    findings = db.Column(db.Text, nullable=False)
    recommended_actions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "inspector_id": self.inspector_id,
            "inspector_name": self.inspector_name,
            "inspection_date": self.inspection_date.isoformat() if self.inspection_date else None,
            "thermal_imaging_status": self.thermal_imaging_status,
            "oil_quality_index": self.oil_quality_index,
            "structural_integrity": self.structural_integrity,
            "findings": self.findings,
            "recommended_actions": self.recommended_actions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IncidentReport(db.Model):
    __tablename__ = "incident_reports"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("transformer_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reporter_name = db.Column(db.String(100), nullable=True, default="Field Technician")
    category = db.Column(db.String(50), nullable=False)  # TEMPERATURE, VOLTAGE, VIBRATION, PHYSICAL_DAMAGE, NOISE, OIL_LEAK, OTHER
    severity = db.Column(db.String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="SUBMITTED")  # SUBMITTED, REVIEWED, CONVERTED_TO_TASK, CLOSED
    reported_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_tag": self.asset.asset_tag if self.asset else None,
            "asset_name": self.asset.name if self.asset else None,
            "reporter_id": self.reporter_id,
            "reporter_name": self.reporter_name,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
        }


class RiskAssessment(db.Model):
    __tablename__ = "risk_assessments"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("transformer_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    overall_risk_score = db.Column(db.Float, nullable=False)  # 0 to 100
    failure_probability = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    factor_breakdown_json = db.Column(db.Text, nullable=False)  # JSON factor breakdown
    model_version = db.Column(db.String(50), default="v1.0-prototype")
    recommendation = db.Column(db.Text, nullable=True)

    def get_factors(self):
        try:
            return json.loads(self.factor_breakdown_json)
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_tag": self.asset.asset_tag if self.asset else None,
            "assessment_date": self.assessment_date.isoformat() if self.assessment_date else None,
            "overall_risk_score": round(self.overall_risk_score, 1),
            "failure_probability": round(self.failure_probability, 3),
            "failure_probability_pct": round(self.failure_probability * 100, 1),
            "factors": self.get_factors(),
            "model_version": self.model_version,
            "recommendation": self.recommendation,
        }


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("transformer_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False)  # INFO, WARNING, HIGH, CRITICAL
    alert_type = db.Column(db.String(50), nullable=False)  # TEMPERATURE_ANOMALY, VIBRATION_SPIKE, LOAD_OVERLOAD, OVERDUE_MAINTENANCE, RAPID_RISK_SURGE, MULTIPLE_INCIDENTS
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="ACTIVE", index=True)  # ACTIVE, ACKNOWLEDGED, RESOLVED
    triggered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by = db.Column(db.String(100), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_tag": self.asset.asset_tag if self.asset else None,
            "asset_name": self.asset.name if self.asset else None,
            "substation": self.asset.substation if self.asset else None,
            "severity": self.severity,
            "alert_type": self.alert_type,
            "title": self.title,
            "message": self.message,
            "status": self.status,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }


class MaintenanceTask(db.Model):
    __tablename__ = "maintenance_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_code = db.Column(db.String(30), unique=True, nullable=False, index=True)  # e.g., TASK-2026-001
    asset_id = db.Column(db.Integer, db.ForeignKey("transformer_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(30), default="DETECTED", nullable=False, index=True)
    # Status progression workflow:
    # DETECTED -> RISK_ASSESSED -> INSPECTION_REQUIRED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> VERIFIED
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    verified_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_by_name = db.Column(db.String(100), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    WORKFLOW_STAGES = [
        "DETECTED",
        "RISK_ASSESSED",
        "INSPECTION_REQUIRED",
        "ASSIGNED",
        "IN_PROGRESS",
        "RESOLVED",
        "VERIFIED",
    ]

    def to_dict(self):
        return {
            "id": self.id,
            "task_code": self.task_code,
            "asset_id": self.asset_id,
            "asset_tag": self.asset.asset_tag if self.asset else None,
            "asset_name": self.asset.name if self.asset else None,
            "substation": self.asset.substation if self.asset else None,
            "title": self.title,
            "priority": self.priority,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_name": self.assigned_to_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "notes": self.notes,
            "resolution_notes": self.resolution_notes,
            "verified_by_id": self.verified_by_id,
            "verified_by_name": self.verified_by_name,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }
