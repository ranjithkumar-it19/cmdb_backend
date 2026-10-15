from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.core.permissions import RoleType, Permission as PermEnum, ROLE_PERMISSIONS
from app.core.security import get_password_hash
from app.db.session import engine
from app.models import (
    Base,
    User,
    Role,
    Permission,
    ReconciliationRule,
    DiscoverySource,
)


def init_db(db: Session) -> None:
    """Create tables if not existing and seed default roles, permissions, admin, and rules."""
    Base.metadata.create_all(bind=engine)

    # 1. Seed Permissions
    existing_perms = {p.code: p for p in db.query(Permission).all()}
    for perm_enum in PermEnum:
        if perm_enum.value not in existing_perms:
            p = Permission(code=perm_enum.value, description=f"Permission to {perm_enum.value}")
            db.add(p)
            existing_perms[perm_enum.value] = p
    db.commit()

    # 2. Seed Roles
    existing_roles = {r.name: r for r in db.query(Role).all()}
    for role_type in RoleType:
        if role_type.value not in existing_roles:
            role = Role(
                name=role_type.value,
                description=f"Standard {role_type.value} role with predefined permissions",
            )
            role_perm_codes = ROLE_PERMISSIONS.get(role_type, [])
            role.permissions = [existing_perms[code] for code in role_perm_codes if code in existing_perms]
            db.add(role)
            existing_roles[role_type.value] = role
    db.commit()

    # 3. Seed Initial Administrator
    admin_user = db.query(User).filter(User.email == settings.INITIAL_ADMIN_EMAIL).first()
    if not admin_user:
        admin_role = existing_roles[RoleType.ADMIN.value]
        admin_user = User(
            email=settings.INITIAL_ADMIN_EMAIL,
            username="admin",
            full_name=settings.INITIAL_ADMIN_NAME,
            hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True,
            roles=[admin_role],
        )
        db.add(admin_user)
        db.commit()
        logger.info(f"Initial administrator created: {settings.INITIAL_ADMIN_EMAIL}")

    # 4. Seed Default Reconciliation Rules
    default_rules = [
        {"rule_name": "Serial Number Exact Match", "priority": 1, "matching_field": "serial_number", "minimum_confidence": 0.95, "auto_merge": True},
        {"rule_name": "BIOS UUID Exact Match", "priority": 2, "matching_field": "bios_uuid", "minimum_confidence": 0.95, "auto_merge": True},
        {"rule_name": "MAC Address Correlation", "priority": 3, "matching_field": "mac_address", "minimum_confidence": 0.85, "auto_merge": True},
        {"rule_name": "Hostname + Domain Match", "priority": 4, "matching_field": "hostname", "minimum_confidence": 0.75, "auto_merge": False},
    ]
    for r_data in default_rules:
        rule = db.query(ReconciliationRule).filter(ReconciliationRule.rule_name == r_data["rule_name"]).first()
        if not rule:
            db.add(ReconciliationRule(**r_data, is_active=True))
    db.commit()

    # 5. Seed Default Discovery Sources
    default_sources = [
        {
            "name": "Corporate Subnet Discovery (Mock / Sandbox)",
            "source_type": "mock",
            "description": "Deterministic internal network discovery simulation for test & verification",
            "scope_definition": '["192.168.1.0/24", "10.0.0.0/24"]',
            "is_active": True,
        },
        {
            "name": "Standard CSV Import",
            "source_type": "csv",
            "description": "Manual or automated CSV inventory file ingestion",
            "scope_definition": '["*"]',
            "is_active": True,
        },
        {
            "name": "Windows Domain Fleet",
            "source_type": "windows_winrm",
            "description": "Windows Remote Management (WinRM) agentless collector",
            "scope_definition": '["10.0.10.0/24"]',
            "credentials_ref": "vault://credentials/winrm-prod-readonly",
            "is_active": True,
        },
        {
            "name": "Linux Production Servers",
            "source_type": "linux_ssh",
            "description": "SSH agentless collector for Ubuntu, Debian, RHEL, CentOS",
            "scope_definition": '["10.0.20.0/24"]',
            "credentials_ref": "vault://credentials/ssh-prod-keys",
            "is_active": True,
        },
        {
            "name": "Core Network Switches & Routers",
            "source_type": "snmp",
            "description": "SNMPv3 telemetry collector for network infrastructure",
            "scope_definition": '["10.0.1.0/24"]',
            "credentials_ref": "vault://credentials/snmp-v3-authpriv",
            "is_active": True,
        },
    ]
    for s_data in default_sources:
        src = db.query(DiscoverySource).filter(DiscoverySource.name == s_data["name"]).first()
        if not src:
            db.add(DiscoverySource(**s_data))
    db.commit()
    logger.info("Database initialization and seed completed successfully.")
