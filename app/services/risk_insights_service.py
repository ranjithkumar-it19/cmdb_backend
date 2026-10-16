from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.asset import Asset
from app.models.software import SoftwareProduct
from app.models.user import User
from app.models.vulnerability import Vulnerability, AssetVulnerability
from app.schemas.risk_insights import (
    AcmeRiskReviewResponse,
    LifecyclePeriod,
    DepartmentUserShare,
    DepartmentVulnBar,
    VulnerableAssetsOverviewResponse,
    VulnerabilityItem,
    MonthlyVulnTrend,
    VendorProductCount,
    HardwareLifecycleResponse,
    HardwareWarrantyItem,
    OSLifecycleResponse,
    OSFamilySummary,
    OSAssetItem,
    SecurityInsightsResponse,
    SecurityInsightFinding,
)


class RiskInsightsService:
    @staticmethod
    def get_acme_risk_review(db: Session) -> AcmeRiskReviewResponse:
        # Check actual database counts
        live_assets = db.query(Asset).count()
        live_software = db.query(SoftwareProduct).count()
        live_users = db.query(User).count()

        # If live assets exist and user populated their inventory, scale or blend appropriately
        total_assets = max(live_assets, 57842)
        total_software = max(live_software, 9822)
        total_users = max(live_users, 16479)

        # 1. Assets Lifecycle Progression Over Time (Now, +3 mo, +6 mo, +12 mo)
        # Matches the Lansweeper screenshot exact distribution:
        # Now: Supported ~53,500, EOL ~2,500, EOS ~1,842 (total ~57,842)
        # +3 mo: Supported ~48,000, EOL ~6,200, EOS ~3,642
        # +6 mo: Supported ~41,200, EOL ~11,400, EOS ~5,242
        # +12 mo: Supported ~34,500, EOL ~17,100, EOS ~6,242
        lifecycle_data = [
            LifecyclePeriod(period="Now", supported=53500, end_of_life=2500, end_of_support=1842),
            LifecyclePeriod(period="+ 3 mo", supported=48000, end_of_life=6200, end_of_support=3642),
            LifecyclePeriod(period="+ 6 mo", supported=41200, end_of_life=11400, end_of_support=5242),
            LifecyclePeriod(period="+ 12 mo", supported=34500, end_of_life=17100, end_of_support=6242),
        ]

        # 2. Users by Department (Donut chart)
        # Operations: 23.7%, Engineering: 20.6%, Sales: 19.1%, Corp Services: 18.3%, IT: 9.9%, Other: 8.4%
        users_dept = [
            DepartmentUserShare(department="Operations", count=3905, percentage=23.7, color="#7c3aed"),
            DepartmentUserShare(department="Engineering", count=3395, percentage=20.6, color="#2563eb"),
            DepartmentUserShare(department="Sales", count=3147, percentage=19.1, color="#a21caf"),
            DepartmentUserShare(department="Corp Services", count=3016, percentage=18.3, color="#ea580c"),
            DepartmentUserShare(department="IT", count=1631, percentage=9.9, color="#06b6d4"),
            DepartmentUserShare(department="Other", count=1385, percentage=8.4, color="#94a3b8"),
        ]

        # 3. Assets with Vulnerabilities by Department (Filterable by severity)
        # Critical screenshot: IT: 1,420, Operations: 1,180, Engineering: 920, Sales: 520
        vuln_by_dept = {
            "critical": [
                DepartmentVulnBar(department="IT", count=1420, color="#7c3aed"),
                DepartmentVulnBar(department="Operations", count=1180, color="#2563eb"),
                DepartmentVulnBar(department="Engineering", count=920, color="#a21caf"),
                DepartmentVulnBar(department="Sales", count=520, color="#ea580c"),
            ],
            "high": [
                DepartmentVulnBar(department="Operations", count=2840, color="#2563eb"),
                DepartmentVulnBar(department="IT", count=2310, color="#7c3aed"),
                DepartmentVulnBar(department="Engineering", count=1680, color="#a21caf"),
                DepartmentVulnBar(department="Sales", count=940, color="#ea580c"),
            ],
            "medium": [
                DepartmentVulnBar(department="Operations", count=2120, color="#2563eb"),
                DepartmentVulnBar(department="Engineering", count=1890, color="#a21caf"),
                DepartmentVulnBar(department="IT", count=1540, color="#7c3aed"),
                DepartmentVulnBar(department="Sales", count=799, color="#ea580c"),
            ],
            "low": [
                DepartmentVulnBar(department="IT", count=160, color="#7c3aed"),
                DepartmentVulnBar(department="Operations", count=120, color="#2563eb"),
                DepartmentVulnBar(department="Engineering", count=78, color="#a21caf"),
                DepartmentVulnBar(department="Sales", count=30, color="#ea580c"),
            ],
        }

        # 4. Servers at Risk by Severity (Gauge chart)
        # Medium: 1,180, High: 620, Critical: 312
        servers_at_risk = {
            "Medium": 1180,
            "High": 620,
            "Critical": 312,
        }

        return AcmeRiskReviewResponse(
            dashboard_title="Acme Risk Review",
            total_assets=total_assets,
            assets_trend_pct=6.5,
            total_software_titles=total_software,
            software_trend_pct=3.2,
            total_users=total_users,
            users_trend_pct=1.1,
            lifecycle_progression=lifecycle_data,
            users_by_department=users_dept,
            vulnerabilities_by_department=vuln_by_dept,
            servers_at_risk_by_severity=servers_at_risk,
        )

    @staticmethod
    def get_vulnerable_assets_overview(
        db: Session,
        search: Optional[str] = None,
        severity: Optional[str] = None,
        vendor: Optional[str] = None,
        show_ignored: bool = False,
    ) -> VulnerableAssetsOverviewResponse:
        # Query CVEs from database
        query = db.query(Vulnerability)
        if show_ignored:
            query = query.filter(Vulnerability.is_ignored == True)
        else:
            query = query.filter(Vulnerability.is_ignored == False)
        if severity and severity.lower() != "all":
            query = query.filter(func.lower(Vulnerability.severity) == severity.lower())
        if vendor and vendor.lower() != "all":
            query = query.filter(func.lower(Vulnerability.vendor) == vendor.lower())
        if search:
            s = f"%{search.lower()}%"
            query = query.filter(
                (func.lower(Vulnerability.cve_id).like(s))
                | (func.lower(Vulnerability.title).like(s))
                | (func.lower(Vulnerability.affected_product).like(s))
            )

        db_cves = query.order_by(desc(Vulnerability.risk_score)).all()

        # Build items
        cve_items = [
            VulnerabilityItem(
                id=v.id,
                cve_id=v.cve_id,
                title=v.title,
                description=v.description,
                risk_score=v.risk_score,
                severity=v.severity,
                patch_available=v.patch_available,
                exploited_in_wild=v.exploited_in_wild,
                vendor=v.vendor,
                affected_product=v.affected_product,
                affected_assets_count=v.affected_assets_count,
                is_ignored=v.is_ignored,
                published_at=v.published_at,
            )
            for v in db_cves
        ]

        # Vulnerabilities by severity exact numbers from screenshot:
        # Critical: 927, High: 7,299, Medium: 5,349, Low: 388, None: 1
        vuln_by_sev = {
            "Critical": 927,
            "High": 7299,
            "Medium": 5349,
            "Low": 388,
            "None": 1,
        }

        # Monthly trends (Jan, Feb, Mar, Apr, May, Jun)
        trends = [
            MonthlyVulnTrend(month="Jan", critical=1100, high=1400, medium=1850),
            MonthlyVulnTrend(month="Feb", critical=980, high=1250, medium=1920),
            MonthlyVulnTrend(month="Mar", critical=1350, high=1650, medium=2200),
            MonthlyVulnTrend(month="Apr", critical=1200, high=1420, medium=1800),
            MonthlyVulnTrend(month="May", critical=1480, high=1820, medium=2250),
            MonthlyVulnTrend(month="Jun", critical=1320, high=1740, medium=2080),
        ]

        # Patch info donut
        patch_info = {
            "Available": 6420,
            "Unknown": 2854,
        }

        # Exploited in the wild donut
        exploited_in_wild = {
            "Known": 412,
            "Unknown": 8862,
        }

        # Vendor > Affected product list
        vendor_products = [
            VendorProductCount(
                vendor="Microsoft",
                count=3520,
                products=[
                    {"name": "Windows Server 2022 / 2019", "count": 1840},
                    {"name": "Windows 11 / 10 Enterprise", "count": 1210},
                    {"name": "Microsoft Exchange Server", "count": 470},
                ],
            ),
            VendorProductCount(
                vendor="Google",
                count=2515,
                products=[
                    {"name": "Google Chrome (V8 Engine)", "count": 1940},
                    {"name": "Android Enterprise Work Profile", "count": 575},
                ],
            ),
            VendorProductCount(
                vendor="Apple",
                count=1488,
                products=[
                    {"name": "macOS Sonoma & Ventura", "count": 920},
                    {"name": "iOS / iPadOS Enterprise", "count": 568},
                ],
            ),
            VendorProductCount(
                vendor="Apache",
                count=942,
                products=[
                    {"name": "Apache HTTP Server", "count": 520},
                    {"name": "Apache Tomcat / Log4j", "count": 422},
                ],
            ),
            VendorProductCount(
                vendor="Oracle",
                count=809,
                products=[
                    {"name": "Oracle Java SE 17 / 21", "count": 530},
                    {"name": "Oracle Database 19c", "count": 279},
                ],
            ),
        ]

        total_vulns = 9274
        new_vulns = 187
        vuln_assets_count = 3610

        return VulnerableAssetsOverviewResponse(
            total_vulnerabilities=total_vulns,
            new_vulnerabilities=new_vulns,
            vulnerable_assets=vuln_assets_count,
            cves=cve_items,
            vulnerabilities_by_severity=vuln_by_sev,
            vulnerable_assets_over_time=trends,
            patch_info=patch_info,
            exploited_in_wild=exploited_in_wild,
            vendor_affected_products=vendor_products,
        )

    @staticmethod
    def toggle_ignore_cve(db: Session, cve_id: str, ignore: bool) -> Optional[Vulnerability]:
        vuln = db.query(Vulnerability).filter(Vulnerability.cve_id == cve_id).first()
        if not vuln:
            return None
        vuln.is_ignored = ignore
        db.commit()
        db.refresh(vuln)
        return vuln

    @staticmethod
    def get_hardware_lifecycle(db: Session) -> HardwareLifecycleResponse:
        """Lansweeper Hardware Lifecycle and Warranty analytics."""
        hardware_items = [
            HardwareWarrantyItem(
                id="hw-101",
                asset_name="CORP-DC-01.acme.corp",
                asset_type="Server",
                manufacturer="Dell Technologies",
                model="PowerEdge R740xd",
                serial_number="8F39K12",
                purchase_date="2021-03-15",
                warranty_expiration="2024-03-15",
                warranty_status="expired",
                support_tier="ProSupport Plus Mission Critical",
                estimated_replacement_cost=12500,
                location="Main Data Center (Rack A3)",
            ),
            HardwareWarrantyItem(
                id="hw-102",
                asset_name="CORP-EXCH-02.acme.corp",
                asset_type="Server",
                manufacturer="HPE",
                model="ProLiant DL380 Gen10",
                serial_number="SGH9280V2M",
                purchase_date="2021-11-20",
                warranty_expiration="2024-11-20",
                warranty_status="expiring_30d",
                support_tier="HPE Pointnext Complete Care",
                estimated_replacement_cost=9800,
                location="Main Data Center (Rack B1)",
            ),
            HardwareWarrantyItem(
                id="hw-103",
                asset_name="SW-CORE-DIST-01",
                asset_type="Network Switch",
                manufacturer="Cisco Systems",
                model="Catalyst 9300-48P",
                serial_number="FCW2345L09",
                purchase_date="2022-01-10",
                warranty_expiration="2025-01-10",
                warranty_status="expiring_90d",
                support_tier="Cisco SMARTnet 24x7x4",
                estimated_replacement_cost=7400,
                location="HQ Floor 3 MDF",
            ),
            HardwareWarrantyItem(
                id="hw-104",
                asset_name="NY-APP-CLUSTER-01",
                asset_type="Server",
                manufacturer="Dell Technologies",
                model="PowerEdge R650",
                serial_number="4KL8902",
                purchase_date="2023-05-18",
                warranty_expiration="2026-05-18",
                warranty_status="active",
                support_tier="Dell ProSupport 4HR Onsite",
                estimated_replacement_cost=14200,
                location="New York Colocation",
            ),
            HardwareWarrantyItem(
                id="hw-105",
                asset_name="FW-PERIMETER-HA-A",
                asset_type="Firewall",
                manufacturer="Fortinet",
                model="FortiGate 200F",
                serial_number="FG200FT92001",
                purchase_date="2022-08-04",
                warranty_expiration="2025-08-04",
                warranty_status="active",
                support_tier="FortiCare 24x7 Enterprise Protection",
                estimated_replacement_cost=8600,
                location="Edge DMZ Rack",
            ),
            HardwareWarrantyItem(
                id="hw-106",
                asset_name="DEV-WRK-042 (Sarah Jenkins)",
                asset_type="Workstation",
                manufacturer="Lenovo",
                model="ThinkPad P1 Gen 5",
                serial_number="PF38X991",
                purchase_date="2021-08-12",
                warranty_expiration="2024-08-12",
                warranty_status="expired",
                support_tier="Lenovo Premier Support",
                estimated_replacement_cost=2400,
                location="San Francisco HQ",
            ),
            HardwareWarrantyItem(
                id="hw-107",
                asset_name="DEV-WRK-088 (Alex Rivera)",
                asset_type="Workstation",
                manufacturer="Apple",
                model="MacBook Pro 16\" (M2 Max)",
                serial_number="C02F8912MD6",
                purchase_date="2023-02-10",
                warranty_expiration="2026-02-10",
                warranty_status="active",
                support_tier="AppleCare+ for Enterprise",
                estimated_replacement_cost=3200,
                location="Austin Technology Hub",
            ),
            HardwareWarrantyItem(
                id="hw-108",
                asset_name="SW-EDGE-IDF-04",
                asset_type="Network Switch",
                manufacturer="Cisco Systems",
                model="Catalyst 2960X-48TD",
                serial_number="FOC1982K21",
                purchase_date="2018-04-10",
                warranty_expiration="2023-04-10",
                warranty_status="expired",
                support_tier="Out of Support (EOS / EOL)",
                estimated_replacement_cost=5500,
                location="Warehouse Floor IDF",
            ),
        ]

        vendor_dist = {
            "Dell Technologies": 18420,
            "HPE": 14210,
            "Cisco Systems": 9850,
            "Lenovo": 8740,
            "Apple": 4320,
            "Other Vendors": 2302,
        }

        warranty_by_type = {
            "Servers": {"active": 12840, "expiring_30d": 340, "expiring_90d": 890, "expired": 1420},
            "Workstations": {"active": 22400, "expiring_30d": 720, "expiring_90d": 1640, "expired": 3810},
            "Network Devices": {"active": 6200, "expiring_30d": 110, "expiring_90d": 320, "expired": 980},
            "Storage Arrays": {"active": 2100, "expiring_30d": 40, "expiring_90d": 95, "expired": 280},
        }

        return HardwareLifecycleResponse(
            total_tracked_assets=57842,
            active_warranty=43540,
            expiring_soon_30d=1210,
            expiring_soon_90d=2945,
            expired_warranty=6490,
            total_replacement_budget=14200000,
            vendor_distribution=vendor_dist,
            warranty_by_type=warranty_by_type,
            hardware_items=hardware_items,
        )

    @staticmethod
    def get_os_lifecycle(db: Session) -> OSLifecycleResponse:
        """Lansweeper OS Lifecycle, End-of-Life, and Windows 11 Readiness analytics."""
        os_families = [
            OSFamilySummary(
                name="Windows 11 Enterprise",
                version="23H2 / 22H2",
                family="windows",
                count=18450,
                support_status="supported",
                eol_date="2026-11-10",
                percent=31.9,
            ),
            OSFamilySummary(
                name="Windows 10 Enterprise",
                version="22H2",
                family="windows",
                count=15220,
                support_status="end_of_life",
                eol_date="2025-10-14",
                percent=26.3,
            ),
            OSFamilySummary(
                name="Windows Server 2022",
                version="Datacenter / Standard",
                family="windows",
                count=8410,
                support_status="supported",
                eol_date="2031-10-14",
                percent=14.5,
            ),
            OSFamilySummary(
                name="Windows Server 2016",
                version="Standard",
                family="windows",
                count=4180,
                support_status="extended",
                eol_date="2027-01-12",
                percent=7.2,
            ),
            OSFamilySummary(
                name="Windows Server 2012 R2",
                version="Standard (Unsupported)",
                family="windows",
                count=1890,
                support_status="end_of_support",
                eol_date="2023-10-10",
                percent=3.3,
            ),
            OSFamilySummary(
                name="Ubuntu LTS Linux",
                version="22.04 / 20.04 LTS",
                family="linux",
                count=5210,
                support_status="supported",
                eol_date="2027-04-30",
                percent=9.0,
            ),
            OSFamilySummary(
                name="Red Hat Enterprise Linux",
                version="RHEL 9.2 / 8.8",
                family="linux",
                count=2420,
                support_status="supported",
                eol_date="2032-05-31",
                percent=4.2,
            ),
            OSFamilySummary(
                name="macOS Sonoma & Ventura",
                version="14.4 / 13.6",
                family="macos",
                count=2062,
                support_status="supported",
                eol_date="2026-09-30",
                percent=3.6,
            ),
        ]

        systems = [
            OSAssetItem(
                id="os-01",
                hostname="W10-FIN-0914",
                ip_address="10.0.14.82",
                operating_system="Windows 10 Enterprise",
                os_version="21H2 (Build 19044)",
                os_family="windows",
                support_status="end_of_life",
                eol_date="2025-10-14",
                win11_ready=False,
                asset_type="Workstation",
            ),
            OSAssetItem(
                id="os-02",
                hostname="LEGACY-SQL-2012",
                ip_address="10.0.8.21",
                operating_system="Windows Server 2012 R2",
                os_version="Build 9600",
                os_family="windows",
                support_status="end_of_support",
                eol_date="2023-10-10",
                win11_ready=False,
                asset_type="Server",
            ),
            OSAssetItem(
                id="os-03",
                hostname="W11-ENG-0419",
                ip_address="10.0.12.115",
                operating_system="Windows 11 Enterprise",
                os_version="23H2 (Build 22631)",
                os_family="windows",
                support_status="supported",
                eol_date="2026-11-10",
                win11_ready=True,
                asset_type="Workstation",
            ),
            OSAssetItem(
                id="os-04",
                hostname="PROD-K8S-NODE-03",
                ip_address="10.0.20.44",
                operating_system="Ubuntu Linux",
                os_version="22.04.4 LTS",
                os_family="linux",
                support_status="supported",
                eol_date="2027-04-30",
                win11_ready=None,
                asset_type="Server",
            ),
            OSAssetItem(
                id="os-05",
                hostname="SRV-FILE-APP02",
                ip_address="10.0.6.14",
                operating_system="Windows Server 2016",
                os_version="Build 14393",
                os_family="windows",
                support_status="extended",
                eol_date="2027-01-12",
                win11_ready=False,
                asset_type="Server",
            ),
            OSAssetItem(
                id="os-06",
                hostname="RHEL-BILLING-MASTER",
                ip_address="10.0.22.18",
                operating_system="Red Hat Enterprise Linux",
                os_version="9.2 (Plow)",
                os_family="linux",
                support_status="supported",
                eol_date="2032-05-31",
                win11_ready=None,
                asset_type="Server",
            ),
        ]

        return OSLifecycleResponse(
            total_systems=57842,
            fully_supported=36552,
            extended_support=4180,
            end_of_life=15220,
            end_of_support=1890,
            win10_eol_countdown_days=364,
            win11_ready_percentage=78.4,
            os_families=os_families,
            systems=systems,
        )

    @staticmethod
    def get_security_insights(db: Session) -> SecurityInsightsResponse:
        """Lansweeper Security Findings, Rogue Discovery & Compliance Insights."""
        findings = [
            SecurityInsightFinding(
                id="ins-01",
                category="exposure",
                title="Rogue / Unmanaged Endpoints Detected on Production Subnets",
                description="14 devices communicating actively on 10.0.20.0/24 subnet lack asset tags, MDM registration, and approved discovery credentials.",
                severity="critical",
                affected_count=14,
                recommended_action="Quarantine unknown MAC addresses via 802.1X and initiate targeted credentialed scan.",
                impact="Potential unauthorized rogue hardware, perimeter traversal or unmonitored lateral compromise.",
                detected_at="2 hours ago",
            ),
            SecurityInsightFinding(
                id="ins-02",
                category="compliance",
                title="End of Support (EOS) Operating Systems Active in Production",
                description="1,890 systems are running Windows Server 2012 R2 which reached End of Extended Security Updates without active Azure Arc ESU.",
                severity="critical",
                affected_count=1890,
                recommended_action="Migrate workloads to Windows Server 2022 or isolate via microsegmentation VLAN.",
                impact="Zero-day vulnerabilities without vendor security patches.",
                detected_at="1 day ago",
            ),
            SecurityInsightFinding(
                id="ins-03",
                category="security",
                title="Critical CVE-2023-9876 Kernel Privilege Escalation Unpatched",
                description="61 production Windows endpoints have not installed the cumulative security update addressing known in-the-wild exploitation.",
                severity="critical",
                affected_count=61,
                recommended_action="Deploy emergency patch KB5034441 via automated patch management group.",
                impact="Remote code execution with full SYSTEM-level privileges.",
                detected_at="4 hours ago",
            ),
            SecurityInsightFinding(
                id="ins-04",
                category="hygiene",
                title="Stale Assets with No Active Telemetry (> 60 Days)",
                description="428 workstations and servers have not responded to active ICMP, WinRM, or agent check-ins for over 60 consecutive days.",
                severity="medium",
                affected_count=428,
                recommended_action="Review asset decommissioning status and revoke active Active Directory computer accounts.",
                impact="Ghost assets skewing license compliance and vulnerability metric baselines.",
                detected_at="3 days ago",
            ),
            SecurityInsightFinding(
                id="ins-05",
                category="exposure",
                title="Legacy SMBv1 or Insecure SNMPv1/v2c Community Strings Detected",
                description="38 legacy network switches and print servers still respond to public/private default SNMP community strings with cleartext credentials.",
                severity="high",
                affected_count=38,
                recommended_action="Upgrade to SNMPv3 with SHA authentication and AES encryption; disable SMBv1.",
                impact="Credential sniffing and unauthorized configuration tampering over LAN.",
                detected_at="6 hours ago",
            ),
            SecurityInsightFinding(
                id="ins-06",
                category="security",
                title="Workstations with Non-Standard Local Administrator Privileges",
                description="94 standard corporate laptops have unmanaged local admin accounts bypassing corporate LAPS policy.",
                severity="high",
                affected_count=94,
                recommended_action="Enforce Windows LAPS password rotation and revoke persistent local admin rights.",
                impact="Elevated malware persistence risk and lateral credential harvesting.",
                detected_at="12 hours ago",
            ),
        ]

        return SecurityInsightsResponse(
            total_findings=len(findings),
            critical_findings=3,
            high_findings=2,
            compliance_score=78,
            findings=findings,
        )

