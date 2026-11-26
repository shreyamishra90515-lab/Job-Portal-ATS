"""
Job Portal and Application Tracking System (ATS)
Flask Application Factory
Phase 4 & 5: Security Middleware, Error Handling, RBAC, CSRF & Web UI Registration
"""

import logging
import os
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from werkzeug.exceptions import HTTPException
from config import config_by_name
from app.db import DatabaseSecurityError
from app.security.auth import get_current_user
from app.security.csrf import init_csrf, generate_csrf_token, CSRFError
from app.security.validation import ValidationError
from app.api import api_bp
from app.web import web_bp


def _wants_json_response() -> bool:
    return request.path.startswith("/api/") or request.is_json


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure a hardened Flask application instance."""
    env_name = config_name or os.environ.get("FLASK_ENV", "default")
    cfg_class = config_by_name.get(env_name, config_by_name["default"])

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(cfg_class)

    if env_name == "production" and not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY environment variable must be set in production.")

    app.config["ACTIVE_CONFIG_CLASS"] = cfg_class

    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
        )
        app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # Initialize Flask-WTF CSRF middleware
    init_csrf(app)

    # Register API and Web UI blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)

    @app.context_processor
    def inject_template_globals():
        return {
            "current_user": get_current_user(),
            "csrf_token": generate_csrf_token,
        }

    # Security response headers
    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'self'; "
                "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                "script-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data:; "
                "frame-ancestors 'none'; "
                "form-action 'self';"
            ),
        )
        if request.path.startswith("/api/auth/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

    # Sanitized error handlers (JSON for /api/*, HTML for Web UI)
    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        if _wants_json_response():
            payload = {"error": err.message}
            if err.field:
                payload["field"] = err.field
            return jsonify(payload), 400
        return render_template("errors/error.html", code=400, title="Bad Request", message=err.message), 400

    @app.errorhandler(CSRFError)
    def handle_csrf_error(err):
        if _wants_json_response():
            return jsonify({"error": err.message}), 400
        return render_template("errors/error.html", code=400, title="Security Check Failed", message=err.message), 400

    @app.errorhandler(DatabaseSecurityError)
    def handle_db_error(err):
        status = 400 if err.error_code in (1062, 1451, 1452, 1644, 3819) else 500
        if _wants_json_response():
            return jsonify({"error": err.message}), status
        return render_template("errors/error.html", code=status, title="Request Error", message=err.message), status

    @app.errorhandler(400)
    def bad_request(err):
        desc = err.description if isinstance(err, HTTPException) else "Bad request."
        if _wants_json_response():
            return jsonify({"error": desc}), 400
        return render_template("errors/error.html", code=400, title="Bad Request", message=desc), 400

    @app.errorhandler(401)
    def unauthorized(err):
        desc = err.description if isinstance(err, HTTPException) else "Authentication required."
        if _wants_json_response():
            return jsonify({"error": desc}), 401
        flash("Please sign in to access this page.", "warning")
        return redirect(url_for("web.login_page", next=request.path))

    @app.errorhandler(403)
    def forbidden(err):
        desc = err.description if isinstance(err, HTTPException) else "Access forbidden."
        if _wants_json_response():
            return jsonify({"error": desc}), 403
        return render_template("errors/error.html", code=403, title="Access Forbidden", message=desc), 403

    @app.errorhandler(404)
    def not_found(_err):
        if _wants_json_response():
            return jsonify({"error": "Requested resource was not found."}), 404
        return render_template(
            "errors/error.html",
            code=404,
            title="Page Not Found",
            message="The requested page or resource could not be found.",
        ), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        if _wants_json_response():
            return jsonify({"error": "HTTP method not allowed for this endpoint."}), 405
        return render_template(
            "errors/error.html",
            code=405,
            title="Method Not Allowed",
            message="This action is not permitted on the requested URL.",
        ), 405

    @app.errorhandler(500)
    def internal_error(err):
        app.logger.error("Unhandled internal server error: %s", type(err).__name__)
        if _wants_json_response():
            return jsonify({"error": "An internal server error occurred."}), 500
        return render_template(
            "errors/error.html",
            code=500,
            title="Server Error",
            message="An unexpected error occurred. Please try again later.",
        ), 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(err):
        if isinstance(err, HTTPException):
            if _wants_json_response():
                return jsonify({"error": err.description}), err.code or 500
            return (
                render_template(
                    "errors/error.html",
                    code=err.code or 500,
                    title=err.name or "Error",
                    message=err.description,
                ),
                err.code or 500,
            )
        app.logger.error("Unexpected unhandled exception: %s", type(err).__name__)
        if _wants_json_response():
            return jsonify({"error": "An internal server error occurred."}), 500
        return (
            render_template(
                "errors/error.html",
                code=500,
                title="Server Error",
                message="An unexpected error occurred.",
            ),
            500,
        )

    return app
