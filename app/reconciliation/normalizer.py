import re
from typing import Optional, List, Dict, Any

# Generic invalid serial numbers often returned by virtual machines or unconfigured boards
GENERIC_SERIALS = {
    "NONE", "NULL", "TO BE FILLED BY O.E.M.", "DEFAULT STRING",
    "0123456789", "123456789", "UNKNOWN", "N/A", "NOT SPECIFIED", "SYSTEM SERIAL NUMBER"
}


class Normalizer:
    """Enterprise Normalization Engine for IT Asset Attributes."""

    @staticmethod
    def normalize_hostname(hostname: Optional[str]) -> Optional[str]:
        """Normalize hostname to lowercase and trimmed."""
        if not hostname:
            return None
        cleaned = hostname.strip().lower().rstrip(".")
        # Strip illegal characters from hostname
        cleaned = re.sub(r"[^\w\.-]", "", cleaned)
        return cleaned or None

    @staticmethod
    def extract_short_hostname(hostname: Optional[str]) -> Optional[str]:
        """Extract short hostname from FQDN."""
        normalized = Normalizer.normalize_hostname(hostname)
        if not normalized:
            return None
        return normalized.split(".")[0]

    @staticmethod
    def normalize_mac(mac: Optional[str]) -> Optional[str]:
        """Normalize MAC address to standard XX:XX:XX:XX:XX:XX format."""
        if not mac:
            return None
        cleaned = re.sub(r"[^0-9a-fA-F]", "", mac.strip().upper())
        if len(cleaned) == 12:
            return ":".join(cleaned[i:i+2] for i in range(0, 12, 2))
        return None

    @staticmethod
    def normalize_mac_list(macs: Any) -> List[str]:
        """Normalize a list or comma-separated string of MAC addresses."""
        if not macs:
            return []
        if isinstance(macs, str):
            # Try splitting by comma, space, or semicolon
            parts = re.split(r"[,;\s]+", macs)
        elif isinstance(macs, (list, tuple, set)):
            parts = list(macs)
        else:
            return []

        results = []
        for p in parts:
            norm = Normalizer.normalize_mac(str(p))
            if norm and norm not in results:
                results.append(norm)
        return results

    @staticmethod
    def normalize_serial(serial: Optional[str]) -> Optional[str]:
        """Normalize hardware serial number, filtering out invalid placeholders."""
        if not serial:
            return None
        cleaned = serial.strip().upper()
        if cleaned in GENERIC_SERIALS or len(cleaned) < 3:
            return None
        return cleaned

    @staticmethod
    def normalize_ip(ip: Optional[str]) -> Optional[str]:
        """Clean and validate IPv4 address format."""
        if not ip:
            return None
        cleaned = ip.strip()
        pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        if re.match(pattern, cleaned):
            return cleaned
        return None

    @staticmethod
    def normalize_os(os_name: Optional[str]) -> Dict[str, Optional[str]]:
        """Classify and standardize operating system name and version."""
        if not os_name:
            return {"name": "Unknown", "version": None, "family": "Unknown"}

        cleaned = os_name.strip()
        lower = cleaned.lower()

        # Windows detection
        if "windows" in lower:
            family = "Windows"
            if "server 2025" in lower:
                return {"name": "Windows Server 2025", "version": "2025", "family": family}
            if "server 2022" in lower:
                return {"name": "Windows Server 2022", "version": "2022", "family": family}
            if "server 2019" in lower:
                return {"name": "Windows Server 2019", "version": "2019", "family": family}
            if "server 2016" in lower:
                return {"name": "Windows Server 2016", "version": "2016", "family": family}
            if "server 2012" in lower:
                return {"name": "Windows Server 2012", "version": "2012", "family": family}
            if "11" in lower:
                return {"name": "Windows 11", "version": "11", "family": family}
            if "10" in lower:
                return {"name": "Windows 10", "version": "10", "family": family}
            return {"name": cleaned, "version": None, "family": family}

        # Linux detection
        if any(d in lower for d in ["ubuntu", "debian", "red hat", "rhel", "centos", "rocky", "fedora", "alpine", "suse", "linux"]):
            family = "Linux"
            if "ubuntu" in lower:
                ver_match = re.search(r"\b(24\.04|22\.04|20\.04|18\.04)\b", lower)
                return {"name": "Ubuntu", "version": ver_match.group(1) if ver_match else None, "family": family}
            if "debian" in lower:
                ver_match = re.search(r"\b(12|11|10)\b", lower)
                return {"name": "Debian", "version": ver_match.group(1) if ver_match else None, "family": family}
            if "red hat" in lower or "rhel" in lower:
                ver_match = re.search(r"\b(9\.\d|8\.\d|7\.\d)\b", lower)
                return {"name": "Red Hat Enterprise Linux", "version": ver_match.group(1) if ver_match else None, "family": family}
            if "centos" in lower:
                return {"name": "CentOS", "version": None, "family": family}
            if "rocky" in lower:
                return {"name": "Rocky Linux", "version": None, "family": family}
            return {"name": cleaned, "version": None, "family": family}

        # macOS / Darwin
        if "mac" in lower or "darwin" in lower or "os x" in lower:
            return {"name": "macOS", "version": None, "family": "macOS"}

        # Network OS
        if "cisco" in lower or "ios" in lower:
            return {"name": "Cisco IOS", "version": None, "family": "Network OS"}

        return {"name": cleaned, "version": None, "family": "Other"}

    @staticmethod
    def normalize_manufacturer(mfg: Optional[str]) -> Optional[str]:
        """Standardize hardware manufacturer names."""
        if not mfg:
            return None
        cleaned = mfg.strip()
        lower = cleaned.lower()

        if "dell" in lower:
            return "Dell"
        if "hp" in lower or "hewlett-packard" in lower or "hewlett packard" in lower:
            return "HP"
        if "lenovo" in lower:
            return "Lenovo"
        if "microsoft" in lower:
            return "Microsoft"
        if "vmware" in lower:
            return "VMware"
        if "cisco" in lower:
            return "Cisco"
        if "apple" in lower:
            return "Apple"
        if "amazon" in lower or "aws" in lower:
            return "Amazon Web Services"
        if "google" in lower:
            return "Google Cloud"
        return cleaned

    @staticmethod
    def normalize_software_name(name: Optional[str]) -> Optional[str]:
        """Standardize software application names."""
        if not name:
            return None
        cleaned = name.strip()
        # Remove noisy architecture suffixes like (x64), (x86), (64-bit)
        cleaned = re.sub(r"\s*\((?:x64|x86|64-bit|32-bit)\)", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
