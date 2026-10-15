from enum import Enum
from typing import List


class RoleType(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    # Assets
    ASSET_READ = "asset:read"
    ASSET_CREATE = "asset:create"
    ASSET_UPDATE = "asset:update"
    ASSET_DELETE = "asset:delete"
    ASSET_EXPORT = "asset:export"
    ASSET_IMPORT = "asset:import"

    # Discovery
    DISCOVERY_READ = "discovery:read"
    DISCOVERY_EXECUTE = "discovery:execute"
    DISCOVERY_MANAGE = "discovery:manage"

    # Relationships & Software
    RELATIONSHIP_MANAGE = "relationship:manage"
    SOFTWARE_READ = "software:read"

    # Administration
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"
    SYSTEM_SETTINGS = "system:settings"


ROLE_PERMISSIONS = {
    RoleType.ADMIN: [p.value for p in Permission],
    RoleType.OPERATOR: [
        Permission.ASSET_READ.value,
        Permission.ASSET_CREATE.value,
        Permission.ASSET_UPDATE.value,
        Permission.ASSET_EXPORT.value,
        Permission.ASSET_IMPORT.value,
        Permission.DISCOVERY_READ.value,
        Permission.DISCOVERY_EXECUTE.value,
        Permission.RELATIONSHIP_MANAGE.value,
        Permission.SOFTWARE_READ.value,
        Permission.AUDIT_READ.value,
    ],
    RoleType.VIEWER: [
        Permission.ASSET_READ.value,
        Permission.ASSET_EXPORT.value,
        Permission.DISCOVERY_READ.value,
        Permission.SOFTWARE_READ.value,
    ],
}
