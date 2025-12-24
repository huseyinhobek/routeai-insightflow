"""
Role-Based Access Control (RBAC) permissions configuration
"""
from typing import List, Set

# Permission definitions
PERMISSIONS = {
    # User management
    "users:manage": "Manage users (invite, remove, change roles)",
    "users:view": "View user list",
    
    # Organization settings
    "org:settings": "Manage organization settings",
    
    # Dataset operations
    "dataset:read": "View datasets and their contents",
    "dataset:write": "Upload and modify datasets",
    "dataset:delete": "Delete datasets",
    
    # Transform operations
    "transform:run": "Run transformation jobs",
    "transform:view": "View transformation results",
    
    # Export operations
    "export:download": "Download exports (Excel, CSV, JSON)",
    
    # Smart filters
    "smart_filter:create": "Generate smart filters",
    "smart_filter:view": "View smart filters",
    
    # Audit
    "audit:read": "View audit logs",
}

# Role to permissions mapping
ROLE_PERMISSIONS: dict[str, Set[str]] = {
    "super_admin": {
        "users:manage",
        "users:view",
        "org:settings",
        "dataset:read",
        "dataset:write",
        "dataset:delete",
        "transform:run",
        "transform:view",
        "export:download",
        "smart_filter:create",
        "smart_filter:view",
        "audit:read",
    },
    "org_admin": {
        "users:manage",
        "users:view",
        "org:settings",
        "dataset:read",
        "dataset:write",
        "dataset:delete",
        "transform:run",
        "transform:view",
        "export:download",
        "smart_filter:create",
        "smart_filter:view",
        "audit:read",
    },
    "transformer": {
        "dataset:read",
        "dataset:write",
        "transform:run",
        "transform:view",
        "export:download",
        "smart_filter:create",
        "smart_filter:view",
    },
    "reviewer": {
        "dataset:read",
        "transform:view",
        "smart_filter:view",
        # Note: export:download is configurable per org for reviewers
    },
    "viewer": {
        "dataset:read",
        "transform:view",
        "smart_filter:view",
    },
}


def get_user_permissions(role: str, org_settings: dict = None) -> List[str]:
    """
    Get list of permissions for a user based on their role and org settings.
    
    Args:
        role: User's role
        org_settings: Optional organization settings for conditional permissions
    
    Returns:
        List of permission strings
    """
    base_permissions = ROLE_PERMISSIONS.get(role, set()).copy()
    
    # Handle conditional permissions based on org settings
    if org_settings and role == "reviewer":
        if org_settings.get("reviewer_can_export", False):
            base_permissions.add("export:download")
    
    return list(base_permissions)


def has_permission(user_role: str, permission: str, org_settings: dict = None) -> bool:
    """
    Check if a user role has a specific permission.
    
    Args:
        user_role: User's role
        permission: Permission to check
        org_settings: Optional organization settings for conditional permissions
    
    Returns:
        True if user has permission, False otherwise
    """
    permissions = get_user_permissions(user_role, org_settings)
    return permission in permissions


def get_role_hierarchy() -> List[str]:
    """
    Get roles ordered by privilege level (highest first).
    
    Returns:
        List of role names in order of privilege
    """
    return ["super_admin", "org_admin", "transformer", "reviewer", "viewer"]


def is_role_higher_or_equal(role1: str, role2: str) -> bool:
    """
    Check if role1 has higher or equal privilege than role2.
    
    Args:
        role1: First role to compare
        role2: Second role to compare
    
    Returns:
        True if role1 >= role2 in privilege
    """
    hierarchy = get_role_hierarchy()
    
    try:
        idx1 = hierarchy.index(role1)
        idx2 = hierarchy.index(role2)
        return idx1 <= idx2  # Lower index = higher privilege
    except ValueError:
        return False


def can_manage_role(manager_role: str, target_role: str) -> bool:
    """
    Check if a manager can manage (assign/change) a target role.
    Users can only manage roles below their own level.
    
    Args:
        manager_role: Role of the user trying to manage
        target_role: Role being assigned/changed
    
    Returns:
        True if manager can manage target role
    """
    # Super admin can manage all roles
    if manager_role == "super_admin":
        return True
    
    # Org admin can manage all roles except super_admin
    if manager_role == "org_admin":
        return target_role != "super_admin"
    
    # Others cannot manage roles
    return False

