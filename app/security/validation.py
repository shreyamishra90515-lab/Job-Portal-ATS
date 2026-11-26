"""
Job Portal and Application Tracking System (ATS)
Input Validation & Sanitization Module
Phase 4: Defense-in-Depth Against Malformed Input, SQLi & XSS
"""

import html
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

# Strict email format pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Phone pattern allowing optional +, digits, spaces, hyphens, parentheses, dots
PHONE_REGEX = re.compile(r"^[+]?[0-9\s\-().]{7,20}$")

# Password policy: 8..72 chars (Bcrypt 72-byte ceiling), upper, lower, digit, special char
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_\-+=\[\]{}|\\:;\"'<>,./~`])[A-Za-z\d@$!%*?&#^()_\-+=\[\]{}|\\:;\"'<>,./~`]{8,72}$"
)

ALLOWED_RESUME_EXTENSIONS = (".pdf", ".doc", ".docx")

# Canonical ATS ENUM Whitelists matching Phase 1 Schema
ROLE_ENUMS = {"ADMIN", "RECRUITER", "CANDIDATE"}
EMPLOYMENT_TYPE_ENUMS = {"FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP"}
WORKPLACE_TYPE_ENUMS = {"ON_SITE", "REMOTE", "HYBRID"}
JOB_STATUS_ENUMS = {"DRAFT", "ACTIVE", "PAUSED", "CLOSED"}
PROFICIENCY_ENUMS = {"BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"}
APPLICATION_STATUS_ENUMS = {
    "APPLIED",
    "UNDER_REVIEW",
    "SHORTLISTED",
    "INTERVIEW_SCHEDULED",
    "INTERVIEWED",
    "OFFERED",
    "REJECTED",
    "WITHDRAWN",
}
ROUND_TYPE_ENUMS = {"SCREENING", "TECHNICAL", "HR", "MANAGERIAL", "FINAL"}
INTERVIEW_STATUS_ENUMS = {
    "SCHEDULED",
    "COMPLETED",
    "CANCELLED",
    "RESCHEDULED",
    "NO_SHOW",
}


class ValidationError(Exception):
    """Exception raised when user input fails server-side validation."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def validate_email(email: str) -> str:
    """Validate and normalize user email address."""
    if not email or not isinstance(email, str):
        raise ValidationError("Email address is required.", field="email")
    email = email.strip()
    if len(email) > 255:
        raise ValidationError("Email address must not exceed 255 characters.", field="email")
    if not EMAIL_REGEX.match(email):
        raise ValidationError("Invalid email address format.", field="email")
    return email.lower()


def validate_password(password: str) -> str:
    """Enforce strict password complexity and Bcrypt 72-byte length bounds."""
    if not password or not isinstance(password, str):
        raise ValidationError("Password is required.", field="password")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.", field="password")
    if len(password.encode("utf-8")) > 72:
        raise ValidationError("Password must not exceed 72 bytes.", field="password")
    if not PASSWORD_REGEX.match(password):
        raise ValidationError(
            "Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",
            field="password",
        )
    return password


def validate_phone(phone: str | None, required: bool = False) -> str:
    """Validate optional or required phone number format."""
    if phone is None or (isinstance(phone, str) and not phone.strip()):
        if required:
            raise ValidationError("Phone number is required.", field="phone")
        return ""
    if not isinstance(phone, str):
        raise ValidationError("Phone number must be a string.", field="phone")
    cleaned = phone.replace("\0", "").strip()
    if not PHONE_REGEX.match(cleaned):
        raise ValidationError("Invalid phone number format.", field="phone")
    return cleaned


def validate_url(
    url: str | None,
    field_name: str = "url",
    max_length: int = 255,
    required: bool = False,
) -> str:
    """Validate HTTP/HTTPS URLs and reject dangerous schemes (javascript:, data:, etc.)."""
    if url is None or (isinstance(url, str) and not url.strip()):
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    if not isinstance(url, str):
        raise ValidationError(f"{field_name} must be a valid URL string.", field=field_name)
    cleaned = url.replace("\0", "").strip()
    if len(cleaned) > max_length:
        raise ValidationError(
            f"{field_name} exceeds maximum length of {max_length} characters.",
            field=field_name,
        )
    if any(ch.isspace() for ch in cleaned):
        raise ValidationError(f"{field_name} must not contain whitespace.", field=field_name)
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValidationError(
            f"{field_name} must be a valid http:// or https:// URL.",
            field=field_name,
        )
    return cleaned


def validate_positive_int(value, field_name: str, max_val: int | None = None) -> int:
    """Validate positive integer values (e.g. primary keys, counts, durations)."""
    if value is None or isinstance(value, bool):
        raise ValidationError(f"{field_name} is required.", field=field_name)
    try:
        int_val = int(value)
        if str(value).strip() != str(int_val) and not isinstance(value, int):
            raise ValueError()
        if int_val <= 0:
            raise ValueError()
        if max_val is not None and int_val > max_val:
            raise ValidationError(f"{field_name} cannot exceed {max_val}.", field=field_name)
        return int_val
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a positive integer.", field=field_name) from None


def validate_decimal_range(value, field_name: str, min_val=0.0, max_val=None) -> Decimal:
    """Validate decimal numbers within valid bounds."""
    if value is None or isinstance(value, bool):
        raise ValidationError(f"{field_name} is required.", field=field_name)
    try:
        dec_val = Decimal(str(value))
        if not dec_val.is_finite():
            raise InvalidOperation()
        if dec_val < Decimal(str(min_val)):
            raise ValidationError(
                f"{field_name} must be at least {min_val}.", field=field_name
            )
        if max_val is not None and dec_val > Decimal(str(max_val)):
            raise ValidationError(
                f"{field_name} cannot exceed {max_val}.", field=field_name
            )
        return dec_val
    except InvalidOperation:
        raise ValidationError(f"{field_name} must be a valid numeric decimal.", field=field_name) from None


def validate_salary_range(salary_min, salary_max) -> tuple[Decimal | None, Decimal | None]:
    """Validate optional minimum and maximum salary bounds and ordering."""
    clean_min = (
        validate_decimal_range(salary_min, "salary_min", min_val=0.0, max_val=100000000.0)
        if salary_min is not None and str(salary_min).strip() != ""
        else None
    )
    clean_max = (
        validate_decimal_range(salary_max, "salary_max", min_val=0.0, max_val=100000000.0)
        if salary_max is not None and str(salary_max).strip() != ""
        else None
    )
    if clean_min is not None and clean_max is not None and clean_max < clean_min:
        raise ValidationError(
            "salary_max must be greater than or equal to salary_min.",
            field="salary_max",
        )
    return clean_min, clean_max


def validate_date(value: str | None, field_name: str = "deadline_date", required: bool = False) -> str | None:
    """Validate ISO YYYY-MM-DD date string."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a date string (YYYY-MM-DD).", field=field_name)
    cleaned = value.strip()
    try:
        dt = datetime.strptime(cleaned, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"{field_name} must follow YYYY-MM-DD format.", field=field_name) from None


def validate_datetime(value: str | None, field_name: str = "scheduled_at", required: bool = True) -> str | None:
    """Validate datetime string (YYYY-MM-DD HH:MM:SS or ISO 8601) and normalize."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a valid datetime string.", field=field_name)
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    raise ValidationError(
        f"{field_name} must be a valid datetime (YYYY-MM-DD HH:MM:SS).",
        field=field_name,
    )


def validate_pagination(page, per_page, max_per_page: int = 100) -> tuple[int, int]:
    """Validate pagination parameters safely."""
    clean_page = validate_positive_int(page if page not in (None, "") else 1, "page", max_val=10000)
    clean_per_page = validate_positive_int(
        per_page if per_page not in (None, "") else 20, "per_page", max_val=max_per_page
    )
    return clean_page, clean_per_page


def validate_enum(value: str, allowed_set: set, field_name: str) -> str:
    """Whitelist validation against allowed ENUM values."""
    if not value or not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.", field=field_name)
    val_upper = value.strip().upper()
    if val_upper not in allowed_set:
        raise ValidationError(
            f"Invalid {field_name}. Allowed values: {', '.join(sorted(allowed_set))}",
            field=field_name,
        )
    return val_upper


def sanitize_text(
    text: str | None,
    max_length: int = 500,
    field_name: str = "text",
    required: bool = False,
) -> str:
    """
    Sanitize text input to prevent Stored & Reflected Cross-Site Scripting (XSS).
    Strips null bytes and escapes HTML special characters.
    """
    if text is None:
        if required:
            raise ValidationError(f"{field_name} is required.", field=field_name)
        return ""
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("\0", "").strip()
    if required and not text:
        raise ValidationError(f"{field_name} is required.", field=field_name)
    if max_length and len(text) > max_length:
        raise ValidationError(
            f"{field_name} exceeds maximum length of {max_length} characters.",
            field=field_name,
        )
    return html.escape(text)


def validate_registration_candidate(data: dict) -> dict:
    """Comprehensive validation for candidate registration payload."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    validated = {
        "email": validate_email(data.get("email")),
        "password": validate_password(data.get("password")),
        "first_name": sanitize_text(data.get("first_name"), max_length=100, field_name="first_name", required=True),
        "last_name": sanitize_text(data.get("last_name"), max_length=100, field_name="last_name", required=True),
        "phone": validate_phone(data.get("phone"), required=False),
        "headline": sanitize_text(data.get("headline", ""), max_length=255, field_name="headline"),
        "summary": sanitize_text(data.get("summary", ""), max_length=2000, field_name="summary"),
        "current_location": sanitize_text(data.get("current_location", ""), max_length=150, field_name="current_location"),
        "years_of_experience": float(
            validate_decimal_range(data.get("years_of_experience", 0.0), "years_of_experience", min_val=0.0, max_val=60.0)
        ),
        "highest_education": sanitize_text(data.get("highest_education", ""), max_length=100, field_name="highest_education"),
        "linkedin_url": validate_url(data.get("linkedin_url"), field_name="linkedin_url", max_length=255),
        "portfolio_url": validate_url(data.get("portfolio_url"), field_name="portfolio_url", max_length=255),
    }
    return validated


def validate_registration_recruiter(data: dict) -> dict:
    """Comprehensive validation for recruiter registration payload."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    validated = {
        "email": validate_email(data.get("email")),
        "password": validate_password(data.get("password")),
        "first_name": sanitize_text(data.get("first_name"), max_length=100, field_name="first_name", required=True),
        "last_name": sanitize_text(data.get("last_name"), max_length=100, field_name="last_name", required=True),
        "phone": validate_phone(data.get("phone"), required=False),
        "company_name": sanitize_text(data.get("company_name"), max_length=150, field_name="company_name", required=True),
        "company_website": validate_url(data.get("company_website"), field_name="company_website", max_length=255),
        "department": sanitize_text(data.get("department", ""), max_length=100, field_name="department"),
        "designation": sanitize_text(data.get("designation", ""), max_length=100, field_name="designation"),
        "office_location": sanitize_text(data.get("office_location", ""), max_length=150, field_name="office_location"),
    }
    return validated


def validate_job_payload(data: dict, partial: bool = False) -> dict:
    """Validate job creation or update payloads."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    result = {}
    if not partial or "title" in data:
        result["title"] = sanitize_text(data.get("title"), max_length=200, field_name="title", required=True)
    if not partial or "description" in data:
        result["description"] = sanitize_text(data.get("description"), max_length=5000, field_name="description", required=True)
    if not partial or "location" in data:
        result["location"] = sanitize_text(data.get("location"), max_length=150, field_name="location", required=True)
    if not partial or "employment_type" in data:
        result["employment_type"] = validate_enum(
            data.get("employment_type", "FULL_TIME"), EMPLOYMENT_TYPE_ENUMS, "employment_type"
        )
    if not partial or "workplace_type" in data:
        result["workplace_type"] = validate_enum(
            data.get("workplace_type", "ON_SITE"), WORKPLACE_TYPE_ENUMS, "workplace_type"
        )
    if not partial or "min_experience_years" in data:
        result["min_experience_years"] = float(
            validate_decimal_range(data.get("min_experience_years", 0.0), "min_experience_years", min_val=0.0, max_val=60.0)
        )
    if not partial or "salary_min" in data or "salary_max" in data:
        s_min, s_max = validate_salary_range(data.get("salary_min"), data.get("salary_max"))
        result["salary_min"] = float(s_min) if s_min is not None else None
        result["salary_max"] = float(s_max) if s_max is not None else None
    if not partial or "status" in data:
        result["status"] = validate_enum(data.get("status", "ACTIVE"), JOB_STATUS_ENUMS, "status")
    if not partial or "deadline_date" in data:
        result["deadline_date"] = validate_date(data.get("deadline_date"), "deadline_date", required=False)

    if partial and not result:
        raise ValidationError("At least one valid job field must be provided for update.")

    return result


def validate_candidate_profile_update(data: dict) -> dict:
    """Validate candidate profile update fields."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    profile_fields = {}
    if "headline" in data:
        profile_fields["headline"] = sanitize_text(data.get("headline"), max_length=255, field_name="headline")
    if "summary" in data:
        profile_fields["summary"] = sanitize_text(data.get("summary"), max_length=2000, field_name="summary")
    if "current_location" in data:
        profile_fields["current_location"] = sanitize_text(
            data.get("current_location"), max_length=150, field_name="current_location"
        )
    if "years_of_experience" in data:
        profile_fields["years_of_experience"] = float(
            validate_decimal_range(data.get("years_of_experience"), "years_of_experience", min_val=0.0, max_val=60.0)
        )
    if "highest_education" in data:
        profile_fields["highest_education"] = sanitize_text(
            data.get("highest_education"), max_length=100, field_name="highest_education"
        )
    if "linkedin_url" in data:
        profile_fields["linkedin_url"] = validate_url(data.get("linkedin_url"), field_name="linkedin_url", max_length=255)
    if "portfolio_url" in data:
        profile_fields["portfolio_url"] = validate_url(data.get("portfolio_url"), field_name="portfolio_url", max_length=255)
    if "phone" in data:
        profile_fields["phone"] = validate_phone(data.get("phone"), required=False)

    if not profile_fields:
        raise ValidationError("At least one profile field must be provided.")
    return profile_fields


def validate_resume_payload(data: dict) -> dict:
    """Validate resume metadata registration payload (prevents path traversal)."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    raw_name = data.get("file_name")
    if not raw_name or not isinstance(raw_name, str):
        raise ValidationError("file_name is required.", field="file_name")
    clean_name = raw_name.replace("\0", "").strip()
    if ".." in clean_name or "/" in clean_name or "\\" in clean_name:
        raise ValidationError("Invalid file_name: path traversal characters are forbidden.", field="file_name")
    if len(clean_name) > 255 or not clean_name.lower().endswith(ALLOWED_RESUME_EXTENSIONS):
        raise ValidationError(
            "Invalid file_name: must end with .pdf, .doc, or .docx.",
            field="file_name",
        )

    raw_path = data.get("file_path") or f"/uploads/resumes/{clean_name}"
    if not isinstance(raw_path, str):
        raise ValidationError("file_path must be a string.", field="file_path")
    clean_path = raw_path.replace("\0", "").strip()
    if ".." in clean_path or len(clean_path) > 500:
        raise ValidationError("Invalid file_path.", field="file_path")

    file_size_kb = validate_positive_int(data.get("file_size_kb", 128), "file_size_kb", max_val=20480)
    is_primary = bool(data.get("is_primary", False))

    return {
        "file_name": html.escape(clean_name),
        "file_path": clean_path,
        "file_size_kb": file_size_kb,
        "is_primary": is_primary,
    }


def validate_recruiter_profile_update(data: dict) -> dict:
    """Validate corporate recruiter profile update fields."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    fields = {}
    if "company_name" in data:
        fields["company_name"] = sanitize_text(
            data.get("company_name"), max_length=150, field_name="company_name", required=True
        )
    if "company_website" in data:
        fields["company_website"] = validate_url(
            data.get("company_website"), field_name="company_website", max_length=255
        )
    if "department" in data:
        fields["department"] = sanitize_text(data.get("department"), max_length=100, field_name="department")
    if "designation" in data:
        fields["designation"] = sanitize_text(data.get("designation"), max_length=100, field_name="designation")
    if "office_location" in data:
        fields["office_location"] = sanitize_text(
            data.get("office_location"), max_length=150, field_name="office_location"
        )
    if "phone" in data:
        fields["phone"] = validate_phone(data.get("phone"), required=False)

    if not fields:
        raise ValidationError("At least one recruiter profile field must be provided.")
    return fields


def validate_interview_update(data: dict) -> dict:
    """Validate interview feedback, rating, and status update payload."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    fields = {}
    if "status" in data:
        fields["status"] = validate_enum(data.get("status"), INTERVIEW_STATUS_ENUMS, "status")
    if "feedback" in data:
        fields["feedback"] = sanitize_text(data.get("feedback"), max_length=2000, field_name="feedback")
    if "rating" in data and data.get("rating") not in (None, ""):
        fields["rating"] = validate_positive_int(data.get("rating"), "rating", max_val=5)
    if "scheduled_at" in data and data.get("scheduled_at"):
        fields["scheduled_at"] = validate_datetime(data.get("scheduled_at"), "scheduled_at", required=True)
    if "duration_minutes" in data and data.get("duration_minutes") not in (None, ""):
        fields["duration_minutes"] = validate_positive_int(
            data.get("duration_minutes"), "duration_minutes", max_val=480
        )

    if not fields:
        raise ValidationError("At least one interview update field must be provided.")
    return fields

