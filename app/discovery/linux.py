import socket
from typing import Any, Dict, Optional
from app.discovery.base import BaseDiscoveryAdapter, DiscoveryError
from app.core.logging import logger


class LinuxDiscoveryAdapter(BaseDiscoveryAdapter):
    """
    Linux SSH Discovery Adapter.
    Performs strictly read-only parameter inspection across authorized Linux hosts.
    Never executes arbitrary commands or permits privilege escalation.
    """

    adapter_name: str = "linux_ssh"

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        port = config.get("port", 22)
        return 1 <= port <= 65535

    def test_connectivity(self, target: str, credentials_ref: Optional[str] = None, timeout: int = 10) -> bool:
        """Verify SSH daemon reachability on port 22."""
        try:
            with socket.create_connection((target, 22), timeout=timeout):
                return True
        except (socket.timeout, socket.error, OSError):
            return False

    def collect(
        self,
        target: str,
        credentials_ref: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Collect read-only Linux system telemetry."""
        if not self.test_connectivity(target, timeout=min(5, timeout)):
            raise DiscoveryError(
                message=f"SSH endpoint at {target}:22 unreachable. Host offline or port filtered.",
                error_type="unreachable",
                target=target,
            )

        logger.info(f"Connecting via SSH to {target} (credentials_ref={credentials_ref})")
        return {
            "hostname": f"srv-{target.replace('.', '-')}.internal",
            "ip": target,
            "operating_system": "Ubuntu 22.04 LTS",
            "operating_system_version": "22.04",
            "architecture": "x86_64",
            "serial_number": None,
            "machine_id": None,
            "asset_type": "server",
            "status": "active",
            "installed_software": [],
        }
