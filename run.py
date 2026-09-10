import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.extensions import db
from backend.models import TransformerAsset, User
from backend.seed import seed_database

app = create_app()

def initialize_local_environment():
    """Initializes tables and seeds demo data if running locally and empty."""
    with app.app_context():
        db.create_all()
        # Only seed if no transformers exist
        if TransformerAsset.query.count() == 0:
            print("[FaultLens] Database empty. Seeding realistic industrial demonstration data...")
            seed_database()
            print("[FaultLens] Demo seed complete. System ready.")
        else:
            print(f"[FaultLens] Database ready. {TransformerAsset.query.count()} assets loaded.")

if __name__ == "__main__":
    initialize_local_environment()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") in ("1", "true", "True")
    print(f"\n=======================================================")
    print(f"  FAULTLENS: Industrial AI Operations Center")
    print(f"  Predict failures. Prioritize maintenance. Prevent downtime.")
    print(f"  Local Development Server: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
