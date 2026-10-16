from typing import Dict, Type, Optional
from app.discovery.base import BaseDiscoveryAdapter
from app.discovery.mock_adapter import MockDiscoveryAdapter
from app.discovery.windows import WindowsDiscoveryAdapter
from app.discovery.linux import LinuxDiscoveryAdapter
from app.discovery.snmp import SnmpDiscoveryAdapter


class DiscoveryAdapterRegistry:
    """Registry managing available discovery adapters."""

    _adapters: Dict[str, Type[BaseDiscoveryAdapter]] = {
        "mock": MockDiscoveryAdapter,
        "ip_range": MockDiscoveryAdapter,
        "windows_winrm": WindowsDiscoveryAdapter,
        "windows": WindowsDiscoveryAdapter,
        "linux_ssh": LinuxDiscoveryAdapter,
        "linux": LinuxDiscoveryAdapter,
        "snmp": SnmpDiscoveryAdapter,
        "cloud": MockDiscoveryAdapter,
    }

    @classmethod
    def get_adapter(cls, source_type: str) -> Optional[BaseDiscoveryAdapter]:
        adapter_cls = cls._adapters.get(source_type)
        if adapter_cls:
            return adapter_cls()
        return None

    @classmethod
    def list_supported_sources(cls) -> Dict[str, str]:
        return {
            "mock": "Mock Sandbox Collector (Local Deterministic Test)",
            "windows_winrm": "Windows WinRM Agentless Collector",
            "linux_ssh": "Linux SSH Agentless Collector",
            "snmp": "SNMPv3/v2c Network Infrastructure Collector",
            "csv": "CSV File Ingestion Importer",
        }
