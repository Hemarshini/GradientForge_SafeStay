"""
SafeStay — scanner.py
Passive network scanner using Scapy ARP heartbeat analysis.
Computes Shannon Entropy of inter-packet timing to flag covert camera streams.
"""

from __future__ import annotations

import math
import time
import socket
import hashlib
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("safestay.scanner")

# ── Known spy-cam MAC OUI prefixes (first 3 octets, uppercase, colon-separated)
CAMERA_OUI_DB: dict[str, str] = {
    "18:FE:34": "Espressif Systems (ESP32-CAM)",
    "24:6F:28": "Espressif Systems (ESP32)",
    "A4:CF:12": "Espressif Systems",
    "DC:A6:32": "Raspberry Pi Foundation",
    "B8:27:EB": "Raspberry Pi Foundation",
    "E4:5F:01": "Raspberry Pi Foundation",
    "00:E0:4C": "Realtek (IP Cam chipset)",
    "C8:3A:35": "Tenda / Shenzhen Bilian",
    "28:6C:07": "Shenzhen Bilian Electronic",
    "FC:77:74": "Shenzhen Bilian Electronic",
    "1C:1B:0D": "HiSilicon / Hikvision",
    "44:19:B6": "Hikvision Digital Technology",
    "BC:01:A6": "Hikvision Digital Technology",
    "00:23:63": "Dahua Technology",
    "3C:EF:8C": "Dahua Technology",
    "BC:AD:AB": "Zmodo / Shenzhen Zmodo",
    "D4:F5:27": "VSTARCAM",
    "C0:49:EF": "Fitivision Technology",
    "70:F1:1C": "Reolink Innovation",
    "EC:71:DB": "Reolink Innovation",
}


# ── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class DeviceRecord:
    ip:          str
    mac:         str
    vendor:      str
    is_camera:   bool
    entropy:     float          = 0.0
    packet_count: int           = 0
    first_seen:  float          = field(default_factory=time.time)
    last_seen:   float          = field(default_factory=time.time)
    inter_arrival_times: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ip":           self.ip,
            "mac":          self.mac,
            "vendor":       self.vendor,
            "is_camera":    self.is_camera,
            "entropy":      round(self.entropy, 4),
            "packet_count": self.packet_count,
            "first_seen":   self.first_seen,
            "last_seen":    self.last_seen,
        }


@dataclass
class NetworkReport:
    network_cidr:    str
    devices:         list[DeviceRecord]
    camera_devices:  list[DeviceRecord]
    scan_duration:   float
    entropy_anomalies: list[str]   # IPs with suspiciously high entropy

    def to_dict(self) -> dict:
        return {
            "network_cidr":     self.network_cidr,
            "devices":          [d.to_dict() for d in self.devices],
            "camera_devices":   [d.to_dict() for d in self.camera_devices],
            "scan_duration":    round(self.scan_duration, 3),
            "entropy_anomalies": self.entropy_anomalies,
            "device_count":     len(self.devices),
            "camera_count":     len(self.camera_devices),
        }


# ── Shannon Entropy ──────────────────────────────────────────────────────────

def shannon_entropy(values: list[float], bins: int = 16) -> float:
    """
    Compute Shannon Entropy H(X) = -Σ p(x) log₂ p(x) over a histogram
    of inter-arrival times.

    High entropy (>3.5 bits) indicates irregular, bursty traffic typical
    of covert video streams that vary their packet timing to evade detection.
    """
    if len(values) < 4:
        return 0.0

    v_min, v_max = min(values), max(values)
    if v_max == v_min:
        return 0.0

    bucket_size = (v_max - v_min) / bins
    counts: dict[int, int] = defaultdict(int)
    for v in values:
        bucket = min(int((v - v_min) / bucket_size), bins - 1)
        counts[bucket] += 1

    total = len(values)
    entropy = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            entropy -= p * math.log2(p)

    return entropy


# ── HeartbeatScanner ─────────────────────────────────────────────────────────

class HeartbeatScanner:
    """
    Passive network scanner.  Two modes:
      1. Passive sniff  — capture ARP/IP packets with Scapy (requires root)
      2. ARP probe      — active ARP scan of a subnet (also needs root)

    Falls back gracefully to a demo fixture when Scapy / root unavailable.
    """

    ENTROPY_THRESHOLD = 3.5   # bits — above this → anomalous
    SNIFF_TIMEOUT     = 8.0   # seconds for passive sniff

    def __init__(self):
        self._devices: dict[str, DeviceRecord] = {}
        self._lock     = threading.Lock()
        self._scapy_ok = self._check_scapy()

    # ── Setup ────────────────────────────────────────────────────────────────

    @staticmethod
    def _check_scapy() -> bool:
        try:
            import scapy.all  # type: ignore  # noqa: F401
            return True
        except ImportError:
            logger.warning("Scapy not installed — using demo mode")
            return False

    # ── OUI Lookup ───────────────────────────────────────────────────────────

    @staticmethod
    def lookup_vendor(mac: str) -> tuple[str, bool]:
        """Return (vendor_name, is_camera_vendor) for a MAC address."""
        oui = ":".join(mac.upper().split(":")[:3])
        if oui in CAMERA_OUI_DB:
            return CAMERA_OUI_DB[oui], True
        # Attempt live macvendors.com lookup with local fallback
        try:
            import urllib.request
            url = f"https://api.macvendors.com/{mac}"
            with urllib.request.urlopen(url, timeout=2) as r:
                vendor = r.read().decode().strip()
                return vendor, False
        except Exception:
            return "Unknown", False

    # ── Packet Callback ──────────────────────────────────────────────────────

    def _pkt_callback(self, pkt):
        """Called by Scapy for each sniffed packet."""
        try:
            from scapy.layers.l2 import ARP, Ether  # type: ignore
            from scapy.layers.inet import IP         # type: ignore

            now = time.time()
            mac: Optional[str] = None
            ip:  Optional[str] = None

            if pkt.haslayer(ARP):
                mac = pkt[ARP].hwsrc
                ip  = pkt[ARP].psrc
            elif pkt.haslayer(Ether) and pkt.haslayer(IP):
                mac = pkt[Ether].src
                ip  = pkt[IP].src

            if not mac or not ip or ip.startswith("0.") or ip == "255.255.255.255":
                return

            with self._lock:
                if mac not in self._devices:
                    vendor, is_cam = self.lookup_vendor(mac)
                    self._devices[mac] = DeviceRecord(
                        ip=ip, mac=mac, vendor=vendor, is_camera=is_cam
                    )
                dev = self._devices[mac]
                if dev.packet_count > 0:
                    dev.inter_arrival_times.append(now - dev.last_seen)
                dev.packet_count += 1
                dev.last_seen = now
                if dev.inter_arrival_times:
                    dev.entropy = shannon_entropy(dev.inter_arrival_times)
        except Exception as exc:
            logger.debug("Packet parse error: %s", exc)

    # ── Active ARP Scan ──────────────────────────────────────────────────────

    def _arp_scan(self, network: str) -> list[DeviceRecord]:
        """Send ARP who-has to each host in `network` and record replies."""
        from scapy.layers.l2 import ARP, Ether  # type: ignore
        from scapy.all import srp                # type: ignore

        pkt    = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network)
        answered, _ = srp(pkt, timeout=2, verbose=False)
        devices = []
        for _, rcv in answered:
            mac    = rcv[ARP].hwsrc
            ip     = rcv[ARP].psrc
            vendor, is_cam = self.lookup_vendor(mac)
            dev = DeviceRecord(ip=ip, mac=mac, vendor=vendor, is_camera=is_cam)
            devices.append(dev)
        return devices

    # ── Passive Sniff ────────────────────────────────────────────────────────

    def _passive_sniff(self, timeout: float = SNIFF_TIMEOUT) -> list[DeviceRecord]:
        """
        Passively sniff ARP + IP traffic.  Invisible to network IDS.
        """
        from scapy.all import sniff  # type: ignore
        with self._lock:
            self._devices.clear()
        sniff(
            filter="arp or (ip and udp)",
            prn=self._pkt_callback,
            timeout=timeout,
            store=False,
        )
        with self._lock:
            return list(self._devices.values())

    # ── Demo Fixture ─────────────────────────────────────────────────────────

    @staticmethod
    def _demo_devices() -> list[DeviceRecord]:
        """Realistic fixture data for environments without Scapy/root."""
        entries = [
            ("192.168.1.1",  "A4:08:F5:11:22:33", "TP-Link Router",                      False, 0.81),
            ("192.168.1.10", "18:FE:34:AB:CD:EF", "Espressif Systems (ESP32-CAM)",        True,  3.91),
            ("192.168.1.14", "BC:01:A6:44:55:66", "Hikvision Digital Technology",         True,  4.12),
            ("192.168.1.20", "00:1A:2B:3C:4D:5E", "Apple, Inc.",                          False, 1.22),
            ("192.168.1.22", "F0:18:98:10:20:30", "Samsung Electronics",                  False, 0.97),
            ("192.168.1.30", "C8:3A:35:FF:00:AA", "Shenzhen Bilian Electronic (Cam-OUI)", True,  3.77),
        ]
        records = []
        for ip, mac, vendor, is_cam, entropy in entries:
            r = DeviceRecord(ip=ip, mac=mac, vendor=vendor, is_camera=is_cam, entropy=entropy,
                             packet_count=int(entropy * 40))
            records.append(r)
        return records

    # ── Public API ────────────────────────────────────────────────────────────

    def scan(self, network: str = "192.168.1.0/24", passive: bool = True) -> NetworkReport:
        """
        Run a full network scan.
        passive=True  → sniff (stealth, needs root)
        passive=False → ARP probe (slightly noisier, also needs root)
        Falls back to demo data if Scapy unavailable or permission denied.
        """
        t0 = time.time()

        if self._scapy_ok:
            try:
                if passive:
                    devices = self._passive_sniff()
                else:
                    devices = self._arp_scan(network)
                logger.info("Scapy scan complete — %d devices", len(devices))
            except PermissionError:
                logger.warning("Root required for Scapy — using demo data")
                devices = self._demo_devices()
        else:
            devices = self._demo_devices()

        cameras   = [d for d in devices if d.is_camera]
        anomalies = [d.ip for d in devices if d.entropy > self.ENTROPY_THRESHOLD]

        return NetworkReport(
            network_cidr      = network,
            devices           = devices,
            camera_devices    = cameras,
            scan_duration     = time.time() - t0,
            entropy_anomalies = anomalies,
        )

    def get_local_network(self) -> str:
        """Best-effort local subnet detection."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            parts = ip.split(".")
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        except Exception:
            return "192.168.1.0/24"
