import ipaddress
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DiscoveryError(Exception):
    def __init__(self, message: str, error_type: str = "general_error", target: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.target = target


class BaseDiscoveryAdapter(ABC):
    """Abstract Base Class for all IT Asset Discovery Adapters."""

    adapter_name: str = "base"

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate adapter-specific source configuration."""
        pass

    @abstractmethod
    def test_connectivity(self, target: str, credentials_ref: Optional[str] = None, timeout: int = 10) -> bool:
        """Verify reachability and authentication to target."""
        pass

    @abstractmethod
    def collect(
        self,
        target: str,
        credentials_ref: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute read-only asset telemetry collection and return a structured observation dict."""
        pass

    def validate_target_in_scope(self, target: str, scope_definition: str) -> bool:
        """
        Verify that a target host or IP is strictly within the administrator-authorized scope.
        Never scan targets outside defined scope.
        """
        if not scope_definition:
            return False

        try:
            allowed_scopes: List[str] = json.loads(scope_definition)
        except Exception:
            allowed_scopes = [s.strip() for s in scope_definition.split(",") if s.strip()]

        if "*" in allowed_scopes:
            return True

        # Check IP network containment
        try:
            target_ip = ipaddress.ip_address(target.strip())
            for scope in allowed_scopes:
                try:
                    if "/" in scope:
                        network = ipaddress.ip_network(scope.strip(), strict=False)
                        if target_ip in network:
                            return True
                    else:
                        allowed_ip = ipaddress.ip_address(scope.strip())
                        if target_ip == allowed_ip:
                            return True
                except ValueError:
                    continue
        except ValueError:
            # Target is a hostname/FQDN
            target_host = target.strip().lower()
            for scope in allowed_scopes:
                scope_clean = scope.strip().lower()
                if target_host == scope_clean or target_host.endswith("." + scope_clean):
                    return True

        return False
