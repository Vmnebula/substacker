"""
Security utilities for Substacker
Handles file validation, rate limiting, CSRF protection, and input sanitization
"""

import logging
import os
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Central security configuration"""

    # File upload
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILE_ROWS = 100000
    ALLOWED_EXTENSIONS = {'.csv', '.json'}
    ALLOWED_CONTENT_TYPES = {'text/csv', 'application/json'}

    # Rate limiting
    RATE_LIMITS = {
        'upload': '10/minute',
        'signup': '5/minute',
        'login': '5/minute',
        'api': '1000/minute'
    }

    # Input validation
    MAX_EMAIL_LENGTH = 255
    MAX_PASSWORD_LENGTH = 256
    MIN_PASSWORD_LENGTH = 8
    MAX_TEAM_NAME_LENGTH = 255

    # Session
    SESSION_TIMEOUT = 1800  # 30 minutes
    CSRF_TOKEN_EXPIRY = 3600  # 1 hour

    # Secrets
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError("CRITICAL: SECRET_KEY environment variable is not set. Refusing to start.")

    @staticmethod
    def get_secret_key():
        """Get validated secret key"""
        return SecurityConfig.SECRET_KEY


class InputValidator:
    """Validate and sanitize user inputs"""

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    TEAM_NAME_REGEX = re.compile(r'^[a-zA-Z0-9\s\-_]{1,255}$')

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        if len(email) > SecurityConfig.MAX_EMAIL_LENGTH:
            return False
        return bool(InputValidator.EMAIL_REGEX.match(email))

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if not password:
            return False, "Password required"

        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters"

        if len(password) > SecurityConfig.MAX_PASSWORD_LENGTH:
            return False, "Password too long"

        # Check for common weak passwords
        weak_passwords = {'password', 'admin', '12345678', 'qwerty', 'abc123', 'password123', '123456'}
        if password.lower() in weak_passwords:
            return False, "Password too common - choose something more unique"

        return True, ""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove potentially dangerous characters from filename"""
        # Remove path traversal attempts
        filename = filename.replace('../', '').replace('..\\', '')

        # Remove special characters except dots and hyphens
        filename = re.sub(r'[^\w\s.-]', '', filename)

        return filename.strip()

    @staticmethod
    def validate_team_name(team_name: str) -> bool:
        """Validate team name format"""
        if not team_name or not isinstance(team_name, str):
            return False

        if len(team_name) > SecurityConfig.MAX_TEAM_NAME_LENGTH:
            return False

        # Allow alphanumeric, spaces, hyphens, underscores
        return bool(InputValidator.TEAM_NAME_REGEX.match(team_name))

    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 255) -> str:
        """Sanitize string input to prevent XSS"""
        if not input_str:
            return ""

        # Truncate if too long
        if len(input_str) > max_length:
            input_str = input_str[:max_length]

        # Remove null bytes
        input_str = input_str.replace('\x00', '')

        return input_str.strip()


class FileValidator:
    """Validate file uploads"""

    @staticmethod
    def validate_upload(filename: str, file_size: int | None = None, content_type: str | None = None) -> tuple[bool, str]:
        """
        Validate uploaded file for security and format

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check filename extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in SecurityConfig.ALLOWED_EXTENSIONS:
            return False, f"Invalid file type. Allowed: CSV, JSON. Got: {file_ext}"

        # Check file size
        if file_size and file_size > SecurityConfig.MAX_FILE_SIZE:
            size_mb = file_size / 1024 / 1024
            return False, f"File too large. Max size: 10MB. Got: {size_mb:.1f}MB"

        # Check content type
        if content_type and content_type not in SecurityConfig.ALLOWED_CONTENT_TYPES:
            return False, f"Invalid content type. Allowed: CSV, JSON. Got: {content_type}"

        logger.info(f"File validation passed: {filename}")
        return True, ""

    @staticmethod
    def validate_csv_content(df_length: int, max_rows: int = SecurityConfig.MAX_FILE_ROWS) -> tuple[bool, str]:
        """Validate CSV content"""
        if df_length == 0:
            return False, "Uploaded file is empty"

        if df_length > max_rows:
            return False, f"File has too many rows (max {max_rows:,}). Got: {df_length:,}"

        return True, ""


class CSRFProtection:
    """CSRF token management"""

    _tokens = {}  # In production, use Redis
    TOKEN_EXPIRY = 3600  # 1 hour

    @staticmethod
    def generate_token(session_id: str) -> str:
        """Generate CSRF token"""
        token = secrets.token_urlsafe(32)
        CSRFProtection._tokens[token] = {
            'session_id': session_id,
            'created_at': datetime.now(),
            'used': False
        }
        logger.debug(f"Generated CSRF token for session: {session_id[:10]}...")
        return token

    @staticmethod
    def verify_token(token: str, session_id: str) -> bool:
        """Verify CSRF token"""
        if not token or token not in CSRFProtection._tokens:
            logger.warning("CSRF token not found or invalid")
            return False

        token_data = CSRFProtection._tokens[token]

        # Check session match
        if token_data['session_id'] != session_id:
            logger.warning("CSRF token session mismatch")
            return False

        # Check expiry
        if datetime.now() - token_data['created_at'] > timedelta(seconds=CSRFProtection.TOKEN_EXPIRY):
            logger.warning("CSRF token expired")
            del CSRFProtection._tokens[token]
            return False

        # Check not already used
        if token_data['used']:
            logger.warning("CSRF token already used")
            return False

        # Mark as used
        token_data['used'] = True

        logger.debug("CSRF token verified successfully")
        return True

    @staticmethod
    def cleanup_expired_tokens():
        """Remove expired tokens"""
        now = datetime.now()
        expired_tokens = [
            token for token, data in CSRFProtection._tokens.items()
            if now - data['created_at'] > timedelta(seconds=CSRFProtection.TOKEN_EXPIRY)
        ]

        for token in expired_tokens:
            del CSRFProtection._tokens[token]

        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired CSRF tokens")


class SecurityHeaders:
    """Security headers for HTTP responses"""

    HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://www.clarity.ms https://scripts.clarity.ms https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://www.clarity.ms https://cdn.jsdelivr.net"
        ),
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }

    @staticmethod
    def get_headers() -> dict:
        """Get all security headers"""
        return SecurityHeaders.HEADERS.copy()
