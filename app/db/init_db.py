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
    Vulnerability,
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

    # 6. Seed Default Lansweeper Vulnerabilities / CVEs
    default_cves = [
        {
            "cve_id": "CVE-2023-9876",
            "title": "Windows Kernel Elevation of Privilege Vulnerability",
            "description": "An elevation of privilege vulnerability in Microsoft Windows Kernel allows authorized local attackers to execute arbitrary code with SYSTEM privileges.",
            "risk_score": 9.2,
            "severity": "critical",
            "patch_available": True,
            "exploited_in_wild": True,
            "vendor": "Microsoft",
            "affected_product": "Windows Server 2022 / Windows 11 Enterprise",
            "affected_assets_count": 61,
            "is_ignored": False,
        },
        {
            "cve_id": "CVE-2007-4559",
            "title": "Python TarFile Directory Traversal Arbitrary File Overwrite",
            "description": "Directory traversal vulnerability in the extract and extractall functions in the tarfile module in Python allows user-assisted remote attackers to overwrite arbitrary files.",
            "risk_score": 8.0,
            "severity": "high",
            "patch_available": True,
            "exploited_in_wild": False,
            "vendor": "Python / Linux",
            "affected_product": "Python 3.x Standard Library on Ubuntu & RHEL",
            "affected_assets_count": 46,
            "is_ignored": False,
        },
        {
            "cve_id": "CVE-2023-7890",
            "title": "Apple WebKit Out-of-Bounds Read Information Disclosure",
            "description": "Processing maliciously crafted web content may disclose sensitive user memory due to insufficient input bounds checking in Apple Safari and WebKit.",
            "risk_score": 6.9,
            "severity": "medium",
            "patch_available": True,
            "exploited_in_wild": False,
            "vendor": "Apple",
            "affected_product": "macOS Sonoma & Safari 17",
            "affected_assets_count": 39,
            "is_ignored": False,
        },
        {
            "cve_id": "CVE-2007-1894",
            "title": "Apache HTTP Server mod_proxy Reverse Proxy Denial of Service",
            "description": "The worker_proxy function in Apache HTTP Server allows remote attackers to cause a denial of service via malformed HTTP requests.",
            "risk_score": 5.7,
            "severity": "medium",
            "patch_available": True,
            "exploited_in_wild": False,
            "vendor": "Apache",
            "affected_product": "Apache HTTP Server 2.4.x",
            "affected_assets_count": 39,
            "is_ignored": False,
        },
        {
            "cve_id": "CVE-2024-21413",
            "title": "Microsoft Outlook Remote Code Execution Vulnerability (MonikerLink)",
            "description": "Flaw in Outlook parsing of 'file://' monikers bypasses Office Protected View and leads to remote code execution and NTLM credential leakage.",
            "risk_score": 9.8,
            "severity": "critical",
            "patch_available": True,
            "exploited_in_wild": True,
            "vendor": "Microsoft",
            "affected_product": "Microsoft 365 Apps / Office 2021",
            "affected_assets_count": 128,
            "is_ignored": False,
        },
        {
            "cve_id": "CVE-2023-4863",
            "title": "Google Chrome libwebp Heap Buffer Overflow",
            "description": "Heap buffer overflow in libwebp in Google Chrome prior to 116.0.5845.187 allowed a remote attacker to perform an out-of-bounds memory write via a crafted HTML page.",
            "risk_score": 8.8,
            "severity": "high",
            "patch_available": True,
            "exploited_in_wild": True,
            "vendor": "Google",
            "affected_product": "Google Chrome Browser 116.x",
            "affected_assets_count": 215,
            "is_ignored": False,
        },
        {
            "cve_id": "CVE-2021-44228",
            "title": "Apache Log4j JNDI Remote Code Execution (Log4Shell)",
            "description": "Apache Log4j2 JNDI features used in configuration, log messages, and parameters do not protect against attacker controlled LDAP and other JNDI related endpoints.",
            "risk_score": 10.0,
            "severity": "critical",
            "patch_available": True,
            "exploited_in_wild": True,
            "vendor": "Apache",
            "affected_product": "Log4j Core 2.0-beta9 to 2.15.0",
            "affected_assets_count": 310,
            "is_ignored": False,
        },
        {
            "cve_id": "CVE-2023-38606",
            "title": "Apple Kernel In-the-Wild Exploitation Vulnerability",
            "description": "An app may be able to modify sensitive kernel state. Apple is aware of a report that this issue may have been exploited against versions of iOS released before iOS 15.7.",
            "risk_score": 8.4,
            "severity": "high",
            "patch_available": True,
            "exploited_in_wild": True,
            "vendor": "Apple",
            "affected_product": "macOS Ventura & iOS Enterprise",
            "affected_assets_count": 52,
            "is_ignored": False,
        },
    ]

    default_ignored_cves = [
        {
            "cve_id": "CVE-2024-3094",
            "title": "XZ Utils Backdoor in Release Archives",
            "description": "Malicious code was introduced into XZ Utils release archives and could enable unauthorized access on affected Linux systems.",
            "risk_score": 10.0,
            "severity": "critical",
            "patch_available": True,
            "exploited_in_wild": False,
            "vendor": "XZ Utils",
            "affected_product": "XZ Utils 5.6.0 and 5.6.1",
            "affected_assets_count": 12,
            "is_ignored": True,
        },
        {
            "cve_id": "CVE-2021-41773",
            "title": "Apache HTTP Server Path Traversal Vulnerability",
            "description": "A path normalization flaw in Apache HTTP Server 2.4.49 could allow path traversal and, under specific configurations, remote code execution.",
            "risk_score": 7.5,
            "severity": "high",
            "patch_available": True,
            "exploited_in_wild": True,
            "vendor": "Apache",
            "affected_product": "Apache HTTP Server 2.4.49",
            "affected_assets_count": 8,
            "is_ignored": True,
        },
        {
            "cve_id": "CVE-2023-22515",
            "title": "Atlassian Confluence Data Center Privilege Escalation",
            "description": "An improper authorization issue in Confluence Data Center and Server could allow an unauthenticated attacker to create an administrator account.",
            "risk_score": 10.0,
            "severity": "critical",
            "patch_available": True,
            "exploited_in_wild": True,
            "vendor": "Atlassian",
            "affected_product": "Confluence Data Center and Server",
            "affected_assets_count": 5,
            "is_ignored": True,
        },
    ]

    for cve_data in default_cves + default_ignored_cves:
        cve = db.query(Vulnerability).filter(Vulnerability.cve_id == cve_data["cve_id"]).first()
        if not cve:
            db.add(Vulnerability(**cve_data))
    db.commit()

    logger.info("Database initialization and seed completed successfully.")
