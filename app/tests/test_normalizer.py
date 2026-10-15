import pytest
from app.reconciliation.normalizer import Normalizer


def test_hostname_normalization():
    assert Normalizer.normalize_hostname("  SRV-DC01.corp.local. ") == "srv-dc01.corp.local"
    assert Normalizer.extract_short_hostname("SRV-DC01.corp.local") == "srv-dc01"
    assert Normalizer.normalize_hostname("") is None
    assert Normalizer.normalize_hostname(None) is None


def test_mac_normalization():
    assert Normalizer.normalize_mac("005056abcdef") == "00:50:56:AB:CD:EF"
    assert Normalizer.normalize_mac("00-50-56-ab-cd-ef") == "00:50:56:AB:CD:EF"
    assert Normalizer.normalize_mac("invalid_mac") is None

    macs = Normalizer.normalize_mac_list("00:11:22:33:44:55, 66-77-88-99-aa-bb")
    assert len(macs) == 2
    assert "00:11:22:33:44:55" in macs
    assert "66:77:88:99:AA:BB" in macs


def test_serial_normalization():
    assert Normalizer.normalize_serial("  vmw-12345-abc  ") == "VMW-12345-ABC"
    # Generic placeholders filtered out
    assert Normalizer.normalize_serial("To be filled by O.E.M.") is None
    assert Normalizer.normalize_serial("None") is None
    assert Normalizer.normalize_serial("0123456789") is None
    assert Normalizer.normalize_serial("ab") is None


def test_ip_normalization():
    assert Normalizer.normalize_ip("192.168.1.50") == "192.168.1.50"
    assert Normalizer.normalize_ip("999.999.999.999") is None
    assert Normalizer.normalize_ip("not-an-ip") is None


def test_os_normalization():
    win = Normalizer.normalize_os("Microsoft Windows Server 2022 Datacenter")
    assert win["name"] == "Windows Server 2022"
    assert win["family"] == "Windows"

    ubuntu = Normalizer.normalize_os("Ubuntu 22.04.3 LTS")
    assert ubuntu["name"] == "Ubuntu"
    assert ubuntu["version"] == "22.04"
    assert ubuntu["family"] == "Linux"


def test_manufacturer_normalization():
    assert Normalizer.normalize_manufacturer("Hewlett-Packard") == "HP"
    assert Normalizer.normalize_manufacturer("Dell Inc.") == "Dell"
    assert Normalizer.normalize_manufacturer("VMware, Inc.") == "VMware"
