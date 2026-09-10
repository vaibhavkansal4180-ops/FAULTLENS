import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from backend.config import Config
from backend.extensions import db, cors

# Import blueprints
from backend.routes.auth import auth_bp
from backend.routes.assets import assets_bp
from backend.routes.telemetry import telemetry_bp
from backend.routes.maintenance import maintenance_bp
from backend.routes.reports import reports_bp
from backend.routes.prediction import prediction_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.simulation import simulation_bp


def create_app(config_class=Config):
    """Application factory for FaultLens."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(telemetry_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(simulation_bp)

    # Resolve frontend directory path
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    # Static / HTML page routes
    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/<page_name>")
    def render_page(page_name):
        # Serve static assets from frontend root or html files
        if (frontend_dir / f"{page_name}.html").exists():
            return send_from_directory(frontend_dir, f"{page_name}.html")
        if (frontend_dir / page_name).exists():
            return send_from_directory(frontend_dir, page_name)
        # If API route not matched, fallback 404
        if page_name.startswith("api"):
            return jsonify({"error": "API route not found."}), 404
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(frontend_dir / "css", filename)

    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(frontend_dir / "js", filename)

    # API error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found"}), 404
        return send_from_directory(frontend_dir, "index.html"), 200

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error occurred. Please contact system administrator."}), 500
        return "An internal server error occurred.", 500

    return app
