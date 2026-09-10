# FAULTLENS: Predictive Infrastructure Maintenance Platform

> **“Predict failures. Prioritize maintenance. Prevent downtime.”**

[![Platform](https://img.shields.io/badge/Platform-Industrial%20AI-0066ff.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.13-00e5ff.svg)](#)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.1-00e676.svg)](#)
[![License](https://img.shields.io/badge/License-Proprietary-gray.svg)](#)

FaultLens is an intelligent predictive infrastructure maintenance platform engineered to transform operational signals, physics-coupled IoT telemetry, and maintenance history into actionable risk insights for high-voltage **electrical transformers**.

---

## 1. Problem Statement
Power utilities and heavy industrial operators frequently discover infrastructure anomalies only **after** catastrophic equipment failure occurs—such as dielectric breakdown, winding flashover, or radiator rupture—resulting in:
1. **Catastrophic Unplanned Outages:** Millions in industrial downtime and emergency grid penalty fees.
2. **Suboptimal Crew Dispatch:** Constrained maintenance technicians dispatched to healthy assets while degraded transformers near thermal runaway remain uninspected.
3. **Black-Box AI Skepticism:** Engineering leadership rejecting opaque machine learning scores that fail to explain **why** an asset is at risk.

---

## 2. The FaultLens Solution
FaultLens closes the operational loop with an interpretable, 7-stage industrial workflow:

$$\mathbf{MONITOR} \longrightarrow \mathbf{DETECT} \longrightarrow \mathbf{PREDICT} \longrightarrow \mathbf{EXPLAIN} \longrightarrow \mathbf{PRIORITIZE} \longrightarrow \mathbf{ACT} \longrightarrow \mathbf{TRACK}$$

- **Physics-Informed IoT Telemetry:** Real-time diurnal telemetry modeling quadratic load-to-temperature coupling, core vibration harmonics, and oil dielectric health.
- **Explainable Additive Risk Engine:** Composite risk scores (0–100) decomposed into transparent factor contributions with engineering rationales.
- **Interpretable Machine Learning:** Failure probability estimation ($0.0 \dots 1.0$) trained with logistic regression feature-weight attribution.
- **Algorithmic Prioritization Queue:** Dynamic dispatch ranking solving the "Which transformer must be inspected first?" optimization problem.
- **What-If Scenario Simulator:** Interactive slider analysis to evaluate hypothetical grid overloads or deferred maintenance intervals before execution.
- **7-Stage Action Tracker:** Traceable lifecycle management from automated anomaly detection through to technician resolution and administrative engineering sign-off.

---

## 3. System Architecture

```
                                  [ IoT Telemetry Stream ]
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │    Telemetry Generator        │
                             │  (Physics-Coupled Simulation) │
                             └───────────────┬───────────────┘
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │       SQL Relational DB       │
                             │   (PostgreSQL / SQLite)       │
                             └───────┬───────────────┬───────┘
                                     │               │
                     ┌───────────────┘               └───────────────┐
                     ▼                                               ▼
     ┌───────────────────────────────┐               ┌───────────────────────────────┐
     │    Explainable Risk Engine    │               │     ML Prediction Engine      │
     │  (Additive Factor Attribution)│               │  (Calibrated Failure Prob)    │
     └───────────────┬───────────────┘               └───────────────┬───────────────┘
                     │                                               │
                     └───────────────┐               ┌───────────────┘
                                     ▼               ▼
                             ┌───────────────────────────────┐
                             │ Maintenance Prioritization    │
                             │   Dispatch Urgency Index      │
                             └───────────────┬───────────────┘
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │   Operations Command Center   │
                             │   (Vanilla JS + SVG Charts)   │
                             └───────────────────────────────┘
```

---

## 4. Tech Stack

- **Backend:** Python 3.13, Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.52, Flask-CORS 6.0.5, Werkzeug 3.1.8, python-dotenv 1.2.3, scikit-learn 1.9.0, numpy 2.5.2.
- **Database:** SQLite (zero-config local development and automated testing); PostgreSQL (production-ready via `psycopg2-binary` and dynamic `DATABASE_URL` resolution).
- **Frontend:** Pure HTML5, CSS3, Vanilla JavaScript with custom zero-dependency SVG sparkline charts. **No React, Next.js, Node.js, MongoDB, or external CDN dependencies.**
- **Deployment:** Vercel Serverless Function (`api/index.py`), `vercel.json`, `Procfile`.
- **API Communication:** Strictly relative URL pathing using `window.location.origin` (no hardcoded localhost).

---

## 5. Visual Identity & Design System
FaultLens employs a technical **Dark + Neon Blue + Cyan Industrial AI** aesthetic:
- **Backgrounds:** Near-black navy (`#060a12`, `#0a101f`, `#0d1527`)
- **Primary Accent:** Electric Neon Blue (`#0066ff`)
- **Secondary Accent:** High-Luminance Cyan (`#00e5ff`)
- **Status Indicators:**
  - `HEALTHY` $\to$ Signal Green (`#00e676`)
  - `MODERATE` $\to$ Amber Yellow (`#ffb300`)
  - `HIGH` $\to$ Warning Orange (`#ff9100`)
  - `CRITICAL` $\to$ Signal Red (`#ff3d00`)

---

## 6. Database Schema (9 Relational Models)

1. **`User`:** Identity and role-based access control (`ADMIN`, `TECHNICIAN`, `VIEWER`) with secure password hashing (`generate_password_hash`).
2. **`TransformerAsset`:** Asset registry (e.g. `FL-042`), nameplate ratings (kVA, voltages, cooling), service age, maintenance intervals, fault history, current risk, failure probability.
3. **`TelemetryReading`:** Chronological sensor packets: top-oil temperature (°C), ambient temperature, 3-phase voltage, current, load percentage, mechanical vibration (mm/s), oil level, anomaly flags.
4. **`MaintenanceRecord`:** Physical interventions log (`PREVENTIVE`, `CORRECTIVE`, `OVERHAUL`), downtime hours, cost, and technician notes.
5. **`Inspection`:** Comprehensive condition assessments: infrared thermography status, oil quality index (0–100), structural integrity, findings, recommendations.
6. **`IncidentReport`:** Technician field observations (temperature, vibration, noise, oil leak) with severity ranking and density-based risk escalation.
7. **`RiskAssessment`:** Historical snapshots storing additive factor breakdowns in structured JSON format.
8. **`Alert`:** Operational notifications with triage state machine (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`).
9. **`MaintenanceTask`:** 7-stage workflow tracker (`DETECTED`, `RISK_ASSESSED`, `INSPECTION_REQUIRED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `VERIFIED`).

---

## 7. Core Engines

### 7.1 Physics-Coupled Telemetry Simulation
Transformers follow coupled thermodynamic and electro-mechanical relationships:
- **Thermal Physics:** Top-oil temperature rise scales quadratically with operational load:
  $$\Delta T \propto (\text{Load}\% / 100)^{1.8}$$
- **Harmonic Vibration:** Base core vibration scales with mechanical service age, foundation looseness, and electrical harmonic distortion.
- **Anomalies:** Injects thermal runaways (>95°C), vibration surges (>4.2 mm/s), and unbalance events.

### 7.2 Explainable Risk Engine (`risk_engine.py`)
No black-box scores. Risk (0–100) is deconstructed additively:
$$\text{Risk} = \Delta_{\text{temp}} + \Delta_{\text{vib}} + \Delta_{\text{load}} + \Delta_{\text{overdue}} + \Delta_{\text{faults}} + \Delta_{\text{age}} + \Delta_{\text{reports}}$$

Example output for flagship unit **FL-042**:
```
Temperature Anomaly           +28.0  (104.2°C surge)
Historical Failure Recurrence +20.0  (3 prior faults)
Electrical Load Stress        +18.0  (112.5% overload)
Maintenance Overdue           +16.0  (410 days since service)
Vibration Stress              +14.0  (3.82 mm/s harmonics)
Asset Aging Degradation       +8.0   (7.0 yrs service)
Technician Incident Signals   +10.0  (2 field reports filed)
------------------------------------------------------
COMPOSITE RISK TOTAL          87.0 / 100  [CRITICAL]
```

### 7.3 Machine Learning Failure Probability (`prediction_engine.py`)
- Evaluates operational telemetry and degradation features using a calibrated logistic regression classifier.
- Returns calibrated probability ($0.0 \dots 1.0$), risk tier (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), and feature contribution vectors.
- Analytical sigmoid fallback ensures cold-start reliability in minimal serverless constraints.

### 7.4 Maintenance Resource Prioritization (`prioritization_engine.py`)
Ranks entire transformer fleets by Maintenance Urgency Index:
$$\text{Priority} = 0.35 \cdot P(\text{Failure}) + 0.25 \cdot \text{Risk} + 0.15 \cdot \text{Overdue} + 0.15 \cdot \text{Anomaly} + 0.10 \cdot \text{Incidents}$$

### 7.5 What-If Scenario Simulator (`simulation.py`)
Allows operators to manipulate hypothetical load shifts, ambient heatwaves, or maintenance delays, observing immediate baseline vs. projected risk deltas and updated action directives.

---

## 8. REST API Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/login` | Authenticate session | No |
| `POST` | `/api/auth/register` | Register new user | No |
| `POST` | `/api/auth/logout` | Terminate session | Yes |
| `GET` | `/api/auth/me` | Current user identity | No |
| `GET` | `/api/dashboard/stats` | Fleet KPI metrics & alert counts | No |
| `GET` | `/api/dashboard/priority` | Prioritized dispatch queue | No |
| `GET` | `/api/assets` | Filtered & paginated transformer list | No |
| `GET` | `/api/assets/<id>` | Asset deep profile, telemetry & risk | No |
| `POST` | `/api/assets` | Register new transformer | Admin |
| `PUT` | `/api/assets/<id>` | Update asset metadata | Admin |
| `DELETE` | `/api/assets/<id>` | Decommission asset | Admin |
| `GET` | `/api/assets/<id>/telemetry` | Historical time-series for charts | No |
| `POST` | `/api/assets/<id>/telemetry/generate` | Trigger live telemetry packet | No |
| `GET` | `/api/maintenance/tasks` | List maintenance work orders | No |
| `POST` | `/api/maintenance/tasks` | Create maintenance task | Tech / Admin |
| `PUT` | `/api/maintenance/tasks/<id>/status` | Advance 7-stage workflow state | Tech / Admin |
| `GET` | `/api/reports` | List field observations | No |
| `POST` | `/api/reports` | Submit incident report | Yes |
| `GET` | `/api/alerts` | Operational alerts triage feed | No |
| `PUT` | `/api/alerts/<id>/acknowledge` | Acknowledge alert | Yes |
| `PUT` | `/api/alerts/<id>/resolve` | Mark alert resolved | Yes |
| `POST` | `/api/simulation/what-if` | Run What-If parameter sensitivity | No |

---

## 9. Local Installation & Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Git

### Setup Steps
```powershell
# 1. Clone or navigate to the FaultLens repository
cd FaultLens

# 2. (Optional) Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
copy .env.example .env

# 5. Run the local development server (automatically seeds 32 demo transformers on first run)
python run.py
```

Open your browser at:
`http://127.0.0.1:5000`

### Pre-seeded Demo Credentials
| Role | Username | Password | Access Capabilities |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | Full control: asset CRUD, task verification, user management |
| **Technician** | `technician` | `tech123` | Create tasks, progress workflow, submit field reports |
| **Viewer** | `viewer` | `viewer123` | Read-only access to telemetry, dashboard, and simulations |

*(1-click login buttons are also available directly on the login page)*

---

## 10. Automated Testing
Run the complete automated test suite:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The test suite validates:
- Application initialization and database table creation
- User authentication and role gating
- Asset catalog CRUD, multi-parameter search, and filtering
- Telemetry generation, physics equations, and anomaly flags
- Additive risk factor breakdown and bounds clamping
- Machine learning failure prediction and feature importances
- Maintenance prioritization dispatch queue
- What-If scenario delta computation
- 7-stage maintenance workflow state machine
- Incident report submission, risk escalation, and alert generation
- Dashboard fleet KPI calculations

---

## 11. Vercel Serverless Deployment

FaultLens is configured for serverless deployment on Vercel:
- **Serverless Entrypoint:** `api/index.py` exposes `app = create_app()`.
- **Routing Configuration:** `vercel.json` routes all web and API traffic through `@vercel/python`.
- **Dynamic URLs:** Zero hardcoded hosts; all API requests utilize `window.location.origin`.

### Steps to Deploy to Vercel:
1. Push repository to GitHub: `https://github.com/<username>/FaultLens`
2. In the Vercel dashboard, click **Add New Project** and import `FaultLens`.
3. Configure Environment Variables in Vercel:
   - `DATABASE_URL`: Your PostgreSQL connection string (e.g., Neon, Supabase, Railway).
   - `SECRET_KEY`: A secure random string.
   - `FLASK_ENV`: `production`
4. Click **Deploy**.
5. Once deployed, run one-time remote database migration/seed or execute `seed_database()` via a secure script or migration runner.

---

## 12. Honest AI & Machine Learning Positioning

> **IMPORTANT DISCLAIMER:**
> FaultLens is a prototype predictive infrastructure maintenance platform designed for engineering decision support and demonstration.
>
> 1. **Telemetry is Simulated:** Operational telemetry (temperature, voltage, current, load, vibration) is produced by synthetic physics approximations and does not represent live utility grid SCADA feeds.
> 2. **Data is Fictional:** All substation names, asset tags, maintenance logs, and incident records are demonstration fixtures.
> 3. **Prototype ML Model:** Failure probabilities and risk scores are derived from demonstration classifiers. Real-world utility deployment requires calibrated models trained on validated Dissolved Gas Analysis (DGA), acoustic partial discharge sensors, and utility-certified operational datasets.

---

## 13. Future Roadmap
- Integration with live SCADA protocols (DNP3, Modbus, IEC 61850).
- Automated Dissolved Gas Analysis (DGA) Duval Triangle and Rogers Ratios diagnostic module.
- Modular asset extension for centrifugal pumps, gas turbines, and HVAC compressors.
- Mobile PWA offline synchronization for field technicians in remote substations without cellular connectivity.
