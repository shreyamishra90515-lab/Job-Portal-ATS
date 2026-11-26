"""
Job Portal and Application Tracking System (ATS)
CSRF Protection Middleware (Flask-WTF backed)
Phase 4: Cryptographic Token Generation & State-Changing Request Defense
"""

from flask import session, request, abort, current_app
from flask_wtf.csrf import generate_csrf, validate_csrf
from wtforms.validators import ValidationError as WTFormsValidationError


class CSRFError(Exception):
    """Exception raised when a state-changing request lacks a valid CSRF token."""

    def __init__(self, message="CSRF token validation failed."):
        super().__init__(message)
        self.message = message


def generate_csrf_token() -> str:
    """
    Generate or retrieve a cryptographically signed CSRF token bound to the current session
    using Flask-WTF's itsdangerous-backed generate_csrf().
    """
    return generate_csrf()


def verify_csrf_token():
    """
    Validate CSRF tokens on all state-changing HTTP methods (POST, PUT, DELETE, PATCH).
    Tokens are accepted via X-CSRF-Token / X-CSRFToken header, form data, or JSON body.
    """
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return

    if not current_app.config.get("WTF_CSRF_ENABLED", True):
        return

    if "csrf_token" not in session:
        abort(
            400,
            description="CSRF validation failed: No CSRF token found in session.",
        )

    submitted_token = (
        request.headers.get("X-CSRF-Token")
        or request.headers.get("X-CSRFToken")
        or request.form.get("csrf_token")
    )

    if not submitted_token and request.is_json:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            submitted_token = data.get("csrf_token")

    if not submitted_token:
        abort(
            400,
            description="CSRF validation failed: Missing CSRF token in request header or body.",
        )

    try:
        validate_csrf(str(submitted_token))
    except WTFormsValidationError as exc:
        abort(400, description=f"CSRF validation failed: {exc}")


def init_csrf(app):
    """Initialize Flask-WTF CSRF middleware on the Flask application."""

    @app.before_request
    def check_csrf():
        if not app.config.get("WTF_CSRF_ENABLED", True):
            return
        verify_csrf_token()

    @app.after_request
    def set_csrf_header(response):
        if "csrf_token" in session:
            response.headers["X-CSRF-Token"] = generate_csrf()
        return response
