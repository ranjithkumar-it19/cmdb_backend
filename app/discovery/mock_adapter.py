import hashlib
from typing import Any, Dict, Optional
from app.discovery.base import BaseDiscoveryAdapter, DiscoveryError


class MockDiscoveryAdapter(BaseDiscoveryAdapter):
    """
    Deterministic Sandbox Discovery Adapter.
    Generates consistent, realistic asset observations based on the target IP or hostname,
    allowing full end-to-end testing of discovery jobs, reconciliation, and change tracking
    without requiring external physical infrastructure.
    """

    adapter_name: str = "mock"

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return True

    def test_connectivity(self, target: str, credentials_ref: Optional[str] = None, timeout: int = 10) -> bool:
        # Simulate target 192.168.1.99 as an unreachable host
        if target.endswith(".99") or "offline" in target:
            return False
        return True

    def collect(
        self,
        target: str,
        credentials_ref: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Generate deterministic observation based on hash of target."""
        if not self.test_connectivity(target):
            raise DiscoveryError(
                message=f"Target {target} unreachable (host timeout or network partition)",
                error_type="unreachable",
                target=target,
            )

        # Hash target to generate deterministic attributes
        h = hashlib.sha256(target.encode()).hexdigest()
        val = int(h[:8], 16)

        # Determine device profile based on target hash
        profiles = ["windows_server", "linux_db", "network_switch", "workstation"]
        profile = profiles[val % len(profiles)]

        if profile == "windows_server":
            return {
                "hostname": f"win-srv-{h[:4]}.corp.local",
                "ip": target,
                "serial_number": f"WIN-SRV-{h[:8].upper()}",
                "bios_uuid": f"4c4c4544-004a-4d10-8032-{h[:12]}",
                "manufacturer": "Dell Inc.",
                "model": "PowerEdge R750",
                "operating_system": "Microsoft Windows Server 2022 Datacenter",
                "operating_system_version": "21H2",
                "architecture": "x64",
                "cpu_info": "Intel(R) Xeon(R) Silver 4314 CPU @ 2.40GHz (32 Cores)",
                "memory_gb": 64.0,
                "storage_gb": 1024.0,
                "domain_or_workgroup": "CORP",
                "asset_type": "server",
                "mac_addresses": f"00:50:56:{h[0:2]}:{h[2:4]}:{h[4:6]}",
                "status": "active",
                "installed_software": [
                    {"name": "CrowdStrike Falcon Sensor", "publisher": "CrowdStrike, Inc.", "version": "7.15.18204", "architecture": "x64"},
                    {"name": "Microsoft SQL Server 2022", "publisher": "Microsoft Corporation", "version": "16.0.1000.6", "architecture": "x64"},
                    {"name": "Google Chrome", "publisher": "Google LLC", "version": "129.0.6668.71", "architecture": "x64"},
                ],
            }
        elif profile == "linux_db":
            return {
                "hostname": f"pg-node-{h[:4]}.internal",
                "ip": target,
                "serial_number": f"VMware-{h[:8].upper()}",
                "machine_id": f"3a8b{h[:28]}",
                "manufacturer": "VMware, Inc.",
                "model": "VMware Virtual Platform",
                "operating_system": "Ubuntu 22.04.4 LTS",
                "operating_system_version": "22.04",
                "architecture": "x86_64",
                "cpu_info": "AMD EPYC 7763 64-Core Processor (16 vCPUs)",
                "memory_gb": 32.0,
                "storage_gb": 500.0,
                "asset_type": "virtual_machine",
                "mac_addresses": f"00:0C:29:{h[0:2]}:{h[2:4]}:{h[4:6]}",
                "status": "active",
                "installed_software": [
                    {"name": "postgresql-16", "publisher": "PostgreSQL Global Development Group", "version": "16.2-1.pgdg22.04+1", "architecture": "amd64"},
                    {"name": "openssh-server", "publisher": "Ubuntu Developers", "version": "1:8.9p1-3ubuntu0.6", "architecture": "amd64"},
                    {"name": "nginx", "publisher": "nginx inc", "version": "1.24.0", "architecture": "amd64"},
                ],
            }
        elif profile == "network_switch":
            return {
                "hostname": f"sw-core-{h[:4]}",
                "ip": target,
                "serial_number": f"FOC{h[:8].upper()}",
                "manufacturer": "Cisco Systems",
                "model": "Catalyst 9300 48-Port PoE+",
                "operating_system": "Cisco IOS-XE",
                "operating_system_version": "17.9.4a",
                "asset_type": "network_device",
                "mac_addresses": f"00:2A:6A:{h[0:2]}:{h[2:4]}:{h[4:6]}",
                "status": "active",
                "location": "Datacenter Rack A-04",
                "installed_software": [],
            }
        else:
            return {
                "hostname": f"ws-sec-{h[:4]}.corp.local",
                "ip": target,
                "serial_number": f"LEN-{h[:8].upper()}",
                "manufacturer": "Lenovo",
                "model": "ThinkPad T14s Gen 4",
                "operating_system": "Windows 11 Enterprise",
                "operating_system_version": "23H2",
                "architecture": "x64",
                "cpu_info": "13th Gen Intel(R) Core(TM) i7-1365U",
                "memory_gb": 16.0,
                "storage_gb": 512.0,
                "domain_or_workgroup": "CORP",
                "asset_type": "workstation",
                "mac_addresses": f"E4:54:E8:{h[0:2]}:{h[2:4]}:{h[4:6]}",
                "status": "active",
                "installed_software": [
                    {"name": "Slack", "publisher": "Slack Technologies LLC", "version": "4.38.125", "architecture": "x64"},
                    {"name": "Visual Studio Code", "publisher": "Microsoft Corporation", "version": "1.93.1", "architecture": "x64"},
                ],
            }
