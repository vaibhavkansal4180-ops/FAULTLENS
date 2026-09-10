import json
import random
from datetime import datetime, date, timedelta, timezone
from backend.extensions import db
from backend.models import (
    User,
    TransformerAsset,
    TelemetryReading,
    MaintenanceRecord,
    Inspection,
    IncidentReport,
    RiskAssessment,
    Alert,
    MaintenanceTask
)
from backend.services.telemetry_generator import TelemetryGenerator
from backend.services.risk_engine import RiskEngine
from backend.services.prediction_engine import PredictionEngine

SUBSTATIONS = [
    {"name": "Metro North Grid Substation", "location": "Sector 4, Industrial Corridor, Metro North", "lat": 40.7128, "lon": -74.0060},
    {"name": "East River Terminal Substation", "location": "Pier 14, Commercial District, East River", "lat": 40.7282, "lon": -73.9942},
    {"name": "West Valley Distribution Center", "location": "Gateway Logistics Park, West Valley", "lat": 40.7589, "lon": -73.9851},
    {"name": "High-Tech Corridor Substation", "location": "Innovation Blvd, Silicon Sector", "lat": 40.7484, "lon": -73.9857},
    {"name": "South Bay Power Hub", "location": "Maritime Zone, Berth 9, South Bay", "lat": 40.6782, "lon": -74.0445},
    {"name": "Central Metro Switching Station", "location": "Civic Center Underground Vault 2", "lat": 40.7135, "lon": -74.0080},
]

MANUFACTURERS = [
    {"maker": "ABB Power Grids", "model": "TrafoStar Pro-X"},
    {"maker": "Siemens Energy", "model": "Troniq T-500"},
    {"maker": "General Electric", "model": "Prolec GE Cast-Coil"},
    {"maker": "Schneider Electric", "model": "Minera MP-Industrial"},
    {"maker": "Hitachi Energy", "model": "Resibloc Dry-Type"},
]

CAPACITIES = [315.0, 500.0, 630.0, 800.0, 1000.0, 1250.0, 1600.0, 2000.0]


def seed_database():
    """Populates the database with realistic industrial demonstration data."""
    print("Clearing existing tables for clean seed...")
    db.session.query(MaintenanceTask).delete()
    db.session.query(Alert).delete()
    db.session.query(RiskAssessment).delete()
    db.session.query(IncidentReport).delete()
    db.session.query(Inspection).delete()
    db.session.query(MaintenanceRecord).delete()
    db.session.query(TelemetryReading).delete()
    db.session.query(TransformerAsset).delete()
    db.session.query(User).delete()
    db.session.commit()

    print("Seeding demo users...")
    admin = User(
        username="admin",
        email="admin@faultlens.internal",
        role="ADMIN",
        full_name="Chief Operations Engineer (Admin)"
    )
    admin.set_password("admin123")

    tech = User(
        username="technician",
        email="technician@faultlens.internal",
        role="TECHNICIAN",
        full_name="Alex Vance (Lead Field Technician)"
    )
    tech.set_password("tech123")

    viewer = User(
        username="viewer",
        email="viewer@faultlens.internal",
        role="VIEWER",
        full_name="Dana Scully (Grid Reliability Analyst)"
    )
    viewer.set_password("viewer123")

    db.session.add_all([admin, tech, viewer])
    db.session.commit()

    print("Generating 32 realistic transformer assets...")
    today = date.today()
    assets = []

    # 1. Specially highlighted flagship Critical asset from specification: FL-042
    fl_042 = TransformerAsset(
        asset_tag="FL-042",
        name="Primary Distribution Unit 42",
        substation="Metro North Grid Substation",
        location="Sector 4, Heavy Industrial Corridor, Metro North",
        installation_date=today - timedelta(days=7 * 365),  # 7 years old
        manufacturer="Siemens Energy",
        model_number="Troniq T-500",
        rated_capacity_kva=1250.0,
        primary_voltage_kv=33.0,
        secondary_voltage_kv=11.0,
        cooling_type="ONAF",
        current_status="MAINTENANCE_REQUIRED",
        last_inspection_date=today - timedelta(days=95),
        last_maintenance_date=today - timedelta(days=410),  # > 1 year overdue
        previous_failure_count=3,
        current_risk_score=87.0,
        failure_probability=0.87,
        health_status="CRITICAL",
        latitude=40.7130,
        longitude=-74.0062,
        notes="FLAGSHIP TEST ASSET: Severe thermal surges recorded. Recurrent tap-changer contact faults."
    )
    assets.append(fl_042)

    # 2. FL-017 (High Risk)
    fl_017 = TransformerAsset(
        asset_tag="FL-017",
        name="Dockyard Feeder Step-down 17",
        substation="East River Terminal Substation",
        location="Pier 14, Commercial District, East River",
        installation_date=today - timedelta(days=12 * 365),
        manufacturer="ABB Power Grids",
        model_number="TrafoStar Pro-X",
        rated_capacity_kva=1000.0,
        primary_voltage_kv=33.0,
        secondary_voltage_kv=0.415,
        cooling_type="ONAN",
        current_status="OPERATIONAL",
        last_inspection_date=today - timedelta(days=45),
        last_maintenance_date=today - timedelta(days=320),
        previous_failure_count=2,
        current_risk_score=78.5,
        failure_probability=0.78,
        health_status="HIGH",
        latitude=40.7285,
        longitude=-73.9945,
        notes="High mechanical vibration observed during peak tide dock crane cycles."
    )
    assets.append(fl_017)

    # 3. FL-031 (High Risk)
    fl_031 = TransformerAsset(
        asset_tag="FL-031",
        name="Logistics Intermodal Step-Down 31",
        substation="West Valley Distribution Center",
        location="Gateway Logistics Park, West Valley",
        installation_date=today - timedelta(days=15 * 365),
        manufacturer="Schneider Electric",
        model_number="Minera MP-Industrial",
        rated_capacity_kva=800.0,
        primary_voltage_kv=22.0,
        secondary_voltage_kv=0.415,
        cooling_type="ONAN",
        current_status="OPERATIONAL",
        last_inspection_date=today - timedelta(days=60),
        last_maintenance_date=today - timedelta(days=290),
        previous_failure_count=2,
        current_risk_score=72.0,
        failure_probability=0.71,
        health_status="HIGH",
        latitude=40.7592,
        longitude=-73.9855,
        notes="Aging oil insulation with moderate moisture content detected."
    )
    assets.append(fl_031)

    # 4. Generate 29 more assets covering Healthy, Moderate, High, Critical
    risk_targets = (
        ["CRITICAL"] * 3 +
        ["HIGH"] * 6 +
        ["MODERATE"] * 10 +
        ["HEALTHY"] * 10
    )

    for i, target_health in enumerate(risk_targets, start=1):
        tag_num = i if i < 17 else (i + 1 if i < 31 else (i + 2 if i < 42 else i + 3))
        tag = f"FL-{tag_num:03d}"
        sub = random.choice(SUBSTATIONS)
        mfr = random.choice(MANUFACTURERS)
        cap = random.choice(CAPACITIES)

        if target_health == "CRITICAL":
            age_years = random.uniform(14.0, 24.0)
            prev_fails = random.randint(2, 4)
            days_maint = random.randint(310, 480)
            risk = round(random.uniform(82.0, 94.0), 1)
            prob = round(random.uniform(0.81, 0.94), 2)
            op_status = "MAINTENANCE_REQUIRED"
        elif target_health == "HIGH":
            age_years = random.uniform(9.0, 18.0)
            prev_fails = random.randint(1, 2)
            days_maint = random.randint(210, 360)
            risk = round(random.uniform(62.0, 79.0), 1)
            prob = round(random.uniform(0.61, 0.79), 2)
            op_status = "OPERATIONAL"
        elif target_health == "MODERATE":
            age_years = random.uniform(5.0, 14.0)
            prev_fails = random.choice([0, 1])
            days_maint = random.randint(120, 250)
            risk = round(random.uniform(32.0, 58.0), 1)
            prob = round(random.uniform(0.32, 0.58), 2)
            op_status = "OPERATIONAL"
        else:  # HEALTHY
            age_years = random.uniform(1.0, 7.0)
            prev_fails = 0
            days_maint = random.randint(20, 110)
            risk = round(random.uniform(8.0, 28.0), 1)
            prob = round(random.uniform(0.06, 0.28), 2)
            op_status = "OPERATIONAL"

        asset = TransformerAsset(
            asset_tag=tag,
            name=f"{sub['name'].split()[0]} Unit {tag_num}",
            substation=sub["name"],
            location=sub["location"],
            installation_date=today - timedelta(days=int(age_years * 365)),
            manufacturer=mfr["maker"],
            model_number=mfr["model"],
            rated_capacity_kva=cap,
            primary_voltage_kv=33.0 if cap >= 1000.0 else 11.0,
            secondary_voltage_kv=0.415,
            cooling_type="ONAF" if cap >= 1250.0 else "ONAN",
            current_status=op_status,
            last_inspection_date=today - timedelta(days=random.randint(15, 90)),
            last_maintenance_date=today - timedelta(days=days_maint),
            previous_failure_count=prev_fails,
            current_risk_score=risk,
            failure_probability=prob,
            health_status=target_health,
            latitude=sub["lat"] + random.uniform(-0.005, 0.005),
            longitude=sub["lon"] + random.uniform(-0.005, 0.005),
            notes=f"Operational transformer serving {sub['name']} feeder network."
        )
        assets.append(asset)

    db.session.add_all(assets)
    db.session.commit()

    print("Generating telemetry histories, records, inspections, reports, and tasks...")
    now = datetime.now(timezone.utc)

    for asset in assets:
        # Generate 14 days of telemetry (4 points per day = 56 points)
        telemetry_series = TelemetryGenerator.generate_historical_series(asset, num_days=14, readings_per_day=4)
        readings_to_add = [
            TelemetryReading(
                asset_id=r["asset_id"],
                timestamp=r["timestamp"],
                temperature_c=r["temperature_c"],
                ambient_temp_c=r["ambient_temp_c"],
                voltage_v=r["voltage_v"],
                current_a=r["current_a"],
                load_pct=r["load_pct"],
                vibration_mms=r["vibration_mms"],
                oil_level_pct=r["oil_level_pct"],
                is_anomaly=r["is_anomaly"],
                anomaly_details=r["anomaly_details"]
            )
            for r in telemetry_series
        ]
        db.session.add_all(readings_to_add)

        # Maintenance records
        if asset.previous_failure_count > 0:
            for f_idx in range(asset.previous_failure_count):
                rec = MaintenanceRecord(
                    asset_id=asset.id,
                    maintenance_type="CORRECTIVE",
                    performed_by="High Voltage Emergency Crew",
                    date_performed=today - timedelta(days=random.randint(180, 700)),
                    notes=f"Emergency repair for secondary bushing arc-over and winding tap contact renewal #{f_idx+1}.",
                    cost_usd=random.choice([3200.0, 4800.0, 6500.0]),
                    downtime_hours=random.choice([4.5, 8.0, 14.0])
                )
                db.session.add(rec)

        # Standard preventive record
        rec_prev = MaintenanceRecord(
            asset_id=asset.id,
            maintenance_type="PREVENTIVE",
            performed_by="Alex Vance",
            date_performed=asset.last_maintenance_date or (today - timedelta(days=180)),
            notes="Annual preventive maintenance: oil sampling, silica gel renewal, radiator washdown.",
            cost_usd=1250.0,
            downtime_hours=2.0
        )
        db.session.add(rec_prev)

        # Inspections
        thermal_stat = "SEVERE_OVERHEATING" if asset.health_status == "CRITICAL" else ("HOTSPOT_DETECTED" if asset.health_status == "HIGH" else "NORMAL")
        oil_idx = 55.0 if asset.health_status == "CRITICAL" else (72.0 if asset.health_status == "HIGH" else 94.0)
        insp = Inspection(
            asset_id=asset.id,
            inspector_id=tech.id,
            inspector_name=tech.full_name,
            inspection_date=asset.last_inspection_date or (today - timedelta(days=30)),
            thermal_imaging_status=thermal_stat,
            oil_quality_index=oil_idx,
            structural_integrity="STRUCTURAL_DEGRADATION" if asset.health_status == "CRITICAL" else "SATISFACTORY",
            findings=f"Routine condition assessment completed. Health state classified as {asset.health_status}.",
            recommended_actions="Follow up on elevated thermals and monitor DGA trends." if asset.health_status in ["HIGH", "CRITICAL"] else "Continue periodic monitoring."
        )
        db.session.add(insp)

        # Risk Assessment breakdown snapshot
        latest_tel = telemetry_series[-1]
        risk_eval = RiskEngine.evaluate_asset_risk(asset, latest_telemetry=latest_tel)
        ra = RiskAssessment(
            asset_id=asset.id,
            assessment_date=now - timedelta(hours=2),
            overall_risk_score=risk_eval["overall_risk_score"],
            failure_probability=asset.failure_probability,
            factor_breakdown_json=json.dumps(risk_eval["factors"]),
            model_version=RiskEngine.MODEL_VERSION,
            recommendation=risk_eval["recommendations"][0]["action"] if risk_eval["recommendations"] else "Monitor."
        )
        db.session.add(ra)

        # Active Alerts for high and critical assets
        if asset.health_status == "CRITICAL":
            alert = Alert(
                asset_id=asset.id,
                severity="CRITICAL",
                alert_type="TEMPERATURE_ANOMALY",
                title=f"Critical Thermal Overload on {asset.asset_tag}",
                message=f"Transformer operating temperature reached {latest_tel['temperature_c']}°C. Failure probability at {asset.failure_probability*100:.1f}%. Immediate dispatch required.",
                status="ACTIVE",
                triggered_at=now - timedelta(hours=random.randint(1, 12))
            )
            db.session.add(alert)

            # High incident report
            rep = IncidentReport(
                asset_id=asset.id,
                reporter_id=tech.id,
                reporter_name=tech.full_name,
                category="TEMPERATURE",
                severity="CRITICAL",
                title=f"Excessive Radiator Surface Heat Detected on {asset.asset_tag}",
                description="Thermal imaging detected hotspot (>98°C) near high-voltage bushing B. Audible buzzing present.",
                status="SUBMITTED",
                reported_at=now - timedelta(hours=8)
            )
            db.session.add(rep)

            # Active maintenance task
            task = MaintenanceTask(
                task_code=f"TASK-2026-{random.randint(100, 999)}",
                asset_id=asset.id,
                title=f"Emergency Thermal Inspection & Load Relief for {asset.asset_tag}",
                priority="CRITICAL",
                assigned_to_id=tech.id,
                assigned_to_name=tech.full_name,
                status=random.choice(["INSPECTION_REQUIRED", "ASSIGNED", "IN_PROGRESS"]),
                created_at=now - timedelta(days=1),
                due_date=today + timedelta(days=1),
                notes="Prioritize cooling system flush and infrared thermography."
            )
            db.session.add(task)

        elif asset.health_status == "HIGH":
            if random.random() < 0.7:
                alert = Alert(
                    asset_id=asset.id,
                    severity="WARNING",
                    alert_type="RAPID_RISK_SURGE",
                    title=f"Elevated Risk Index on {asset.asset_tag}",
                    message=f"Asset risk index increased to {asset.current_risk_score:.1f}. Maintenance interval overdue.",
                    status="ACTIVE",
                    triggered_at=now - timedelta(hours=random.randint(4, 36))
                )
                db.session.add(alert)

            task = MaintenanceTask(
                task_code=f"TASK-2026-{random.randint(100, 999)}",
                asset_id=asset.id,
                title=f"Preventive Oil Degassing & Bushing Check for {asset.asset_tag}",
                priority="HIGH",
                assigned_to_id=tech.id,
                assigned_to_name=tech.full_name,
                status=random.choice(["RISK_ASSESSED", "ASSIGNED", "IN_PROGRESS"]),
                created_at=now - timedelta(days=2),
                due_date=today + timedelta(days=5),
                notes="Inspect vibration isolator dampers and test breakdown voltage."
            )
            db.session.add(task)

    db.session.commit()
    print("Database seeding completed successfully! Fleet populated with 32 realistic transformers.")


if __name__ == "__main__":
    from backend.app import create_app
    app = create_app()
    with app.app_context():
        seed_database()
