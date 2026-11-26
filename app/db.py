"""
Job Portal and Application Tracking System (ATS)
Secure Database Access Layer
Phase 4: SQL Injection Protection, Transaction Safety & Error Concealment
"""

import logging
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from flask import current_app, has_app_context
from config import Config

logger = logging.getLogger("ats.database")
logger.setLevel(logging.INFO)

# Whitelist of approved Phase 2 stored procedures
ALLOWED_PROCEDURES = {
    "sp_register_candidate",
    "sp_register_recruiter",
    "sp_apply_job",
    "sp_update_application_status",
    "sp_schedule_interview",
}


class DatabaseSecurityError(Exception):
    """Sanitized database exception concealing internal SQL and credentials."""

    def __init__(self, message="A secure database error occurred.", error_code=None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _resolve_config(config=None):
    """Resolve explicit config, active Flask app config, or base Config."""
    if config is not None:
        return config
    if has_app_context():
        active = current_app.config.get("ACTIVE_CONFIG_CLASS")
        if active is not None:
            return active
        return current_app.config
    return Config


def _cfg_get(cfg, key: str, default=None):
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def _sanitize_mysql_error(err: pymysql.MySQLError, context: str = "query") -> DatabaseSecurityError:
    """Convert raw MySQL errors into safe, non-leaking client exceptions."""
    error_code, error_msg = err.args if len(err.args) >= 2 else (0, str(err))
    logger.error("Database error during %s [%s]: %s", context, error_code, error_msg)

    if error_code == 1062:
        return DatabaseSecurityError(
            "A duplicate record already exists with the provided information.",
            error_code=error_code,
        )
    if error_code in (1451, 1452):
        return DatabaseSecurityError(
            "Referential integrity validation failed.",
            error_code=error_code,
        )
    if error_code == 3819:  # CHECK constraint violation
        return DatabaseSecurityError(
            "Input violated a database integrity constraint.",
            error_code=error_code,
        )
    if error_code == 1644:  # SIGNAL SQLSTATE '45000' from triggers/procedures
        return DatabaseSecurityError(str(error_msg), error_code=error_code)

    return DatabaseSecurityError(
        "Database operation could not be completed safely.",
        error_code=error_code,
    )


def get_db_connection(config=None):
    """Establish a secure connection to MySQL 8.0+ using parameterized PyMySQL driver."""
    cfg = _resolve_config(config)
    try:
        connection = pymysql.connect(
            host=_cfg_get(cfg, "DATABASE_HOST", "localhost"),
            port=int(_cfg_get(cfg, "DATABASE_PORT", 3306)),
            user=_cfg_get(cfg, "DATABASE_USER"),
            password=_cfg_get(cfg, "DATABASE_PASSWORD"),
            database=_cfg_get(cfg, "DATABASE_NAME", "job_portal_ats"),
            charset=_cfg_get(cfg, "DATABASE_CHARSET", "utf8mb4"),
            cursorclass=DictCursor,
            autocommit=False,  # Enforce explicit transaction control
            connect_timeout=10,
        )
        return connection
    except pymysql.MySQLError as err:
        error_code = err.args[0] if err.args else None
        logger.error("Failed to connect to MySQL database (code=%s)", error_code)
        raise DatabaseSecurityError(
            "Database connection could not be established. Please contact administrator."
        ) from None


@contextmanager
def get_db_cursor(commit=False, config=None):
    """
    Context manager for database transactional execution.
    Automatically commits on clean exit and issues ROLLBACK on any SQL error.
    """
    conn = get_db_connection(config)
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except pymysql.MySQLError as err:
        conn.rollback()
        raise _sanitize_mysql_error(err, context="transaction") from None
    except DatabaseSecurityError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Unexpected error in database transaction: %s", type(exc).__name__)
        raise DatabaseSecurityError("An unexpected server error occurred.") from None
    finally:
        cursor.close()
        conn.close()


def execute_query(
    sql: str,
    params: tuple | list = None,
    fetch: str = "all",
    commit: bool = False,
    config=None,
):
    """
    Execute a parameterized SQL query safely.
    NEVER construct SQL queries with formatted strings or string concatenation.
    """
    with get_db_cursor(commit=commit, config=config) as cursor:
        cursor.execute(sql, params or ())
        if fetch == "all":
            return cursor.fetchall()
        if fetch == "one":
            return cursor.fetchone()
        if fetch == "lastrowid":
            return cursor.lastrowid
        return None


def execute_procedure(
    proc_name: str,
    in_params: tuple | list = (),
    out_param_names: list[str] | tuple[str, ...] = (),
    config=None,
):
    """
    Execute an approved Phase 2 stored procedure using callproc with ACID transaction handling.
    Properly binds IN and OUT arguments and retrieves PyMySQL @_proc_idx OUT parameters.
    """
    if proc_name not in ALLOWED_PROCEDURES:
        raise DatabaseSecurityError("Requested stored procedure is not permitted.")

    in_list = list(in_params or ())
    out_names = list(out_param_names or ())
    full_args = in_list + [None] * len(out_names)

    conn = get_db_connection(config)
    cursor = conn.cursor()
    try:
        cursor.callproc(proc_name, full_args)
        while cursor.nextset():
            pass

        result = {}
        if out_names:
            select_exprs = ", ".join(
                f"@_{proc_name}_{len(in_list) + idx} AS {name}"
                for idx, name in enumerate(out_names)
            )
            cursor.execute(f"SELECT {select_exprs};")
            row = cursor.fetchone() or {}
            result = dict(row)

        conn.commit()
        return result
    except pymysql.MySQLError as err:
        conn.rollback()
        raise _sanitize_mysql_error(err, context=f"procedure {proc_name}") from None
    except Exception as exc:
        conn.rollback()
        logger.error("Unexpected error in procedure %s: %s", proc_name, type(exc).__name__)
        raise DatabaseSecurityError("An unexpected server error occurred.") from None
    finally:
        cursor.close()
        conn.close()
