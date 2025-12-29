"""
Authentication and Authorization module for Aletheia
"""

from .jwt_handler import create_access_token, verify_token, decode_token
from .password import hash_token, verify_token_hash
from .magic_link import create_magic_link, verify_magic_link
from .dependencies import get_current_user, get_current_user_optional, require_permission
from .permissions import ROLE_PERMISSIONS, has_permission, get_user_permissions

__all__ = [
    # JWT
    "create_access_token",
    "verify_token",
    "decode_token",
    # Password/Token hashing
    "hash_token",
    "verify_token_hash",
    # Magic Link
    "create_magic_link",
    "verify_magic_link",
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_permission",
    # Permissions
    "ROLE_PERMISSIONS",
    "has_permission",
    "get_user_permissions",
]

