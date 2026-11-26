"""
Server-Side Input Validation Unit Tests
Phase 4: Email, Password, Phone, URL, Numeric, Date, Enum, Pagination & Path Traversal
"""

import pytest
from app.security.validation import (
    ValidationError,
    validate_email,
    validate_password,
    validate_phone,
    validate_url,
    validate_positive_int,
    validate_salary_range,
    validate_date,
    validate_datetime,
    validate_pagination,
    validate_enum,
    sanitize_text,
    validate_resume_payload,
    APPLICATION_STATUS_ENUMS,
)


def test_validate_email_cases():
    assert validate_email("  Alice.Smith@Example.COM ") == "alice.smith@example.com"
    for bad in ("", None, "plainaddress", "a@b", "user@.com", "x" * 250 + "@a.com"):
        with pytest.raises(ValidationError):
            validate_email(bad)


def test_validate_password_policy():
    assert validate_password("ValidPass@123") == "ValidPass@123"
    for weak in ("short1!", "alllowercase1!", "ALLUPPERCASE1!", "NoDigitsHere!", "NoSpecialChar123", "A" * 73 + "@1a"):
        with pytest.raises(ValidationError):
            validate_password(weak)


def test_validate_phone():
    assert validate_phone("") == ""
    assert validate_phone("+1 (415) 555-0199") == "+1 (415) 555-0199"
    with pytest.raises(ValidationError):
        validate_phone("not-a-phone!!!")


def test_validate_url_blocks_dangerous_schemes():
    assert validate_url("https://linkedin.com/in/user") == "https://linkedin.com/in/user"
    assert validate_url("") == ""
    for dangerous in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "ftp://example.com", "not a url"):
        with pytest.raises(ValidationError):
            validate_url(dangerous)


def test_validate_numeric_salary_and_dates():
    assert validate_positive_int("42", "job_id") == 42
    with pytest.raises(ValidationError):
        validate_positive_int(0, "job_id")
    with pytest.raises(ValidationError):
        validate_positive_int(-5, "job_id")

    s_min, s_max = validate_salary_range(100000, 150000)
    assert float(s_min) == 100000.0
    assert float(s_max) == 150000.0
    with pytest.raises(ValidationError):
        validate_salary_range(160000, 120000)

    assert validate_date("2026-12-31") == "2026-12-31"
    with pytest.raises(ValidationError):
        validate_date("31-12-2026")

    assert validate_datetime("2026-12-15T14:30:00") == "2026-12-15 14:30:00"
    with pytest.raises(ValidationError):
        validate_datetime("invalid-dt")


def test_validate_pagination_and_enum():
    assert validate_pagination("2", "25") == (2, 25)
    with pytest.raises(ValidationError):
        validate_pagination("0", "20")
    with pytest.raises(ValidationError):
        validate_pagination("1", "500")

    assert validate_enum("shortlisted", APPLICATION_STATUS_ENUMS, "status") == "SHORTLISTED"
    with pytest.raises(ValidationError):
        validate_enum("HACKED_STATUS", APPLICATION_STATUS_ENUMS, "status")


def test_sanitize_text_and_resume_path_traversal():
    escaped = sanitize_text("<script>alert('XSS')</script>", max_length=200)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped

    with pytest.raises(ValidationError):
        validate_resume_payload({"file_name": "../../etc/passwd.pdf"})
    with pytest.raises(ValidationError):
        validate_resume_payload({"file_name": "payload.exe"})
    clean = validate_resume_payload({"file_name": "my_cv.pdf", "file_size_kb": 150, "is_primary": True})
    assert clean["file_name"] == "my_cv.pdf"

