"""
SafeStay — forensics.py
RSA-2048 signing + ReportLab PDF evidence vault generation.
Implements SHA-256 integrity verification for the 3D scan data.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from reportlab.lib           import colors
from reportlab.lib.enums     import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units     import mm
from reportlab.platypus      import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

import logging
logger = logging.getLogger("safestay.forensics")

# ── Colour palette ────────────────────────────────────────────────────────────
C_BG    = colors.HexColor("#0D1117")
C_PANEL = colors.HexColor("#161B22")
C_GREEN = colors.HexColor("#2ECC71")
C_RED   = colors.HexColor("#E74C3C")
C_AMBER = colors.HexColor("#F39C12")
C_GREY  = colors.HexColor("#8B949E")
C_WHITE = colors.HexColor("#F0F6FC")


# ── RSA Key Manager ───────────────────────────────────────────────────────────

class RSAKeyManager:
    """
    Manages RSA-2048 key pair for signing scan certificates.
    Keys are persisted to disk and loaded from ENV variables when set.
    """

    def __init__(self, key_dir: Path = Path(".keys")):
        self.key_dir     = key_dir
        self.private_key = None
        self.public_key  = None
        self._load_or_generate()

    def _load_or_generate(self):
        """Load from ENV / disk, or generate a fresh key pair."""
        try:
            from cryptography.hazmat.primitives              import serialization
            from cryptography.hazmat.primitives.asymmetric   import rsa
            from cryptography.hazmat.backends                import default_backend

            priv_pem = os.environ.get("SAFESTAY_PRIVATE_KEY_PEM")
            pub_pem  = os.environ.get("SAFESTAY_PUBLIC_KEY_PEM")

            if priv_pem and pub_pem:
                self.private_key = serialization.load_pem_private_key(
                    priv_pem.encode(), password=None, backend=default_backend()
                )
                self.public_key = serialization.load_pem_public_key(
                    pub_pem.encode(), backend=default_backend()
                )
                logger.info("RSA keys loaded from environment")
                return

            # Try disk cache
            priv_path = self.key_dir / "private.pem"
            pub_path  = self.key_dir / "public.pem"
            if priv_path.exists() and pub_path.exists():
                with open(priv_path, "rb") as f:
                    self.private_key = serialization.load_pem_private_key(
                        f.read(), password=None, backend=default_backend()
                    )
                with open(pub_path, "rb") as f:
                    self.public_key = serialization.load_pem_public_key(
                        f.read(), backend=default_backend()
                    )
                logger.info("RSA keys loaded from disk")
                return

            # Generate new pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
            self._save_keys()
            logger.info("New RSA-2048 key pair generated")

        except ImportError:
            logger.warning("cryptography library not installed — RSA signing disabled")

    def _save_keys(self):
        """Persist key pair to .keys/ directory."""
        from cryptography.hazmat.primitives import serialization
        self.key_dir.mkdir(exist_ok=True)
        with open(self.key_dir / "private.pem", "wb") as f:
            f.write(self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        with open(self.key_dir / "public.pem", "wb") as f:
            f.write(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ))

    def sign(self, data: bytes) -> Optional[str]:
        """
        RSA-PSS sign `data`.  Returns base64-encoded signature or None if
        the cryptography library is unavailable.
        """
        if self.private_key is None:
            return None
        try:
            from cryptography.hazmat.primitives            import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            sig = self.private_key.sign(data, padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ), hashes.SHA256())
            return base64.b64encode(sig).decode()
        except Exception as exc:
            logger.error("RSA sign failed: %s", exc)
            return None

    def verify(self, data: bytes, signature_b64: str) -> bool:
        """Verify an RSA-PSS signature."""
        if self.public_key is None:
            return False
        try:
            from cryptography.hazmat.primitives            import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            sig = base64.b64decode(signature_b64)
            self.public_key.verify(sig, data, padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ), hashes.SHA256())
            return True
        except Exception:
            return False

    def public_pem(self) -> str:
        """Return the public key as a PEM string (for embedding in reports)."""
        if self.public_key is None:
            return "RSA UNAVAILABLE"
        from cryptography.hazmat.primitives import serialization
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()


# ── Integrity Verifier ────────────────────────────────────────────────────────

class IntegrityVerifier:
    """
    SHA-256 based tamper detection for scan data.
    Provides the 'Verify Integrity' button logic.
    """

    @staticmethod
    def hash_scan_data(scan_data: dict) -> str:
        """Deterministic SHA-256 of canonicalised scan data JSON."""
        canonical = json.dumps(scan_data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def hash_detection_coords(detections: list[dict]) -> str:
        """Hash the 3D coordinates of all detections — used for 3D integrity proof."""
        coords = [
            {"x": d["coord_3d"]["x"], "y": d["coord_3d"]["y"], "z": d["coord_3d"]["z"]}
            for d in detections
        ]
        canonical = json.dumps(coords, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    def verify(cls, scan_data: dict, expected_hash: str) -> dict:
        """
        Re-hash scan data and compare to the certificate hash.
        Returns a verification result dict.
        """
        computed = cls.hash_scan_data(scan_data)
        match    = computed == expected_hash
        return {
            "verified":      match,
            "computed_hash": computed,
            "expected_hash": expected_hash,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
        }


# ── PDF Report Builder ────────────────────────────────────────────────────────

class ForensicReportBuilder:
    """
    Generates a ReportLab PDF evidence certificate.
    Embeds RSA signature, SHA-256 hashes, 3D detection coordinates,
    and network device tables.
    """

    def __init__(self):
        self.rsa = RSAKeyManager()
        self.verifier = IntegrityVerifier()

    def _styles(self):
        base = getSampleStyleSheet()
        return {
            "title":   ParagraphStyle("T",  parent=base["Normal"], fontSize=22,
                                      textColor=C_WHITE, alignment=TA_CENTER,
                                      fontName="Helvetica-Bold"),
            "sub":     ParagraphStyle("S",  parent=base["Normal"], fontSize=9,
                                      textColor=C_GREY,  alignment=TA_CENTER),
            "h2":      ParagraphStyle("H2", parent=base["Normal"], fontSize=12,
                                      textColor=C_WHITE, fontName="Helvetica-Bold",
                                      spaceAfter=4),
            "mono":    ParagraphStyle("M",  parent=base["Normal"], fontSize=7,
                                      textColor=C_GREY,  fontName="Courier",
                                      alignment=TA_CENTER),
            "body":    ParagraphStyle("B",  parent=base["Normal"], fontSize=8,
                                      textColor=C_GREY,  alignment=TA_CENTER),
            "verdict_critical": ParagraphStyle("VC", parent=base["Normal"], fontSize=16,
                                               textColor=C_RED, alignment=TA_CENTER,
                                               fontName="Helvetica-Bold"),
            "verdict_clean":    ParagraphStyle("VK", parent=base["Normal"], fontSize=16,
                                               textColor=C_GREEN, alignment=TA_CENTER,
                                               fontName="Helvetica-Bold"),
        }

    def _verdict_table(self, level: str, styles: dict) -> Table:
        is_critical = level in ("CRITICAL", "HIGH")
        style_key   = "verdict_critical" if is_critical else "verdict_clean"
        icon        = "⚠" if is_critical else "✓"
        text        = f"{icon}  THREAT LEVEL: {level}"
        border_col  = C_RED if is_critical else C_GREEN
        bg_hex      = "#1a0a0a" if is_critical else "#0a1a0a"

        tbl = Table([[Paragraph(text, styles[style_key])]], colWidths=["100%"])
        tbl.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 2,  border_col),
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(bg_hex)),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        return tbl

    def _ai_table(self, scan_data: dict, styles: dict) -> Table:
        dets = scan_data.get("detections", [])
        peak = scan_data.get("peak_score", 0)

        data = [
            ["Metric",               "Value"],
            ["Frames Analysed",      str(scan_data.get("frames_analysed", "—"))],
            ["Total Detections",     str(len(dets))],
            ["Peak Threat Score",    f"{peak*100:.1f}%"],
            ["Overall Level",        scan_data.get("overall_level", "—")],
            ["Fusion CRITICAL",      "YES" if scan_data.get("fusion_critical") else "NO"],
            ["Network Match",        "YES" if scan_data.get("network_match")   else "NO"],
            ["IR Detected",          "YES" if scan_data.get("ir_detected")     else "NO"],
        ]
        tbl = Table(data, colWidths=[80*mm, 80*mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_PANEL),
            ("TEXTCOLOR",  (0, 0), (-1, 0), C_GREEN),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("TEXTCOLOR",  (0, 1), (-1, -1), C_WHITE),
            ("BACKGROUND", (0, 1), (-1, -1), C_BG),
            ("GRID",       (0, 0), (-1, -1), 0.5, C_GREY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return tbl

    def _coord_table(self, detections: list[dict], styles: dict) -> Table:
        data = [["Frame", "Bbox (px)", "3D Coord (m)", "Score", "Level", "SHA-256 (16)"]]
        for d in detections[:10]:   # cap at 10 rows for readability
            c  = d.get("coord_3d", {})
            b  = d.get("bbox", [0, 0, 0, 0])
            data.append([
                str(d.get("frame_id", "?")),
                f"{b[0]},{b[1]}→{b[2]},{b[3]}",
                f"({c.get('x','?')}, {c.get('y','?')}, {c.get('z','?')})",
                f"{d.get('threat_score', 0)*100:.1f}%",
                d.get("threat_level", "—"),
                d.get("frame_hash", "")[:16] + "…",
            ])
        tbl = Table(data, colWidths=[12*mm, 35*mm, 40*mm, 16*mm, 20*mm, 37*mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_GREEN),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 7),
            ("TEXTCOLOR",     (0, 1), (-1, -1), C_WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_BG, C_PANEL]),
            ("GRID",          (0, 0), (-1, -1), 0.4, C_GREY),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    def _network_table(self, network_report: Optional[dict], styles: dict) -> Table:
        data = [["IP Address", "MAC Address", "Vendor / Risk", "Entropy"]]
        if network_report:
            for d in network_report.get("devices", [])[:8]:
                risk  = "⚠ " if d.get("is_camera") else "✓ "
                color_flag = d.get("is_camera", False)
                data.append([
                    d.get("ip", "?"),
                    d.get("mac", "?"),
                    risk + d.get("vendor", "Unknown"),
                    f"{d.get('entropy', 0):.2f} bits",
                ])
        else:
            data.append(["—", "—", "Network scan not run", "—"])

        tbl = Table(data, colWidths=[30*mm, 45*mm, 70*mm, 20*mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_PANEL),
            ("TEXTCOLOR",  (0, 0), (-1, 0), C_GREEN),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("TEXTCOLOR",  (0, 1), (-1, -1), C_WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_BG, C_PANEL]),
            ("GRID",       (0, 0), (-1, -1), 0.4, C_GREY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    def build(
        self,
        scan_data:      dict,
        network_report: Optional[dict] = None,
        output_path:    Optional[Path] = None,
    ) -> dict:
        """
        Build and save the forensic PDF.  Returns a dict with:
          path, sha256_hash, rsa_signature, coord_hash, generated_at
        """
        import tempfile
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(tempfile.gettempdir()) / f"SafeStay_Report_{ts}.pdf"

        styles = self._styles()
        ts_now = datetime.now(timezone.utc)

        # Compute hashes BEFORE building document
        scan_hash  = self.verifier.hash_scan_data(scan_data)
        coord_hash = self.verifier.hash_detection_coords(scan_data.get("detections", []))
        signature  = self.rsa.sign(scan_hash.encode()) or "RSA_UNAVAILABLE"

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=18*mm, rightMargin=18*mm,
            topMargin=18*mm,  bottomMargin=18*mm,
        )

        story = [
            Spacer(1, 4*mm),
            Paragraph("🛡 SafeStay", styles["title"]),
            Paragraph("Forensic Hidden Camera Detection Report", styles["sub"]),
            Paragraph(f"Generated: {ts_now.strftime('%d %B %Y, %H:%M:%S')} UTC", styles["sub"]),
            Spacer(1, 4*mm),
            HRFlowable(width="100%", thickness=1, color=C_GREY),
            Spacer(1, 5*mm),

            # ── Verdict ──────────────────────────────────────────────────
            self._verdict_table(scan_data.get("overall_level", "UNKNOWN"), styles),
            Spacer(1, 7*mm),

            # ── AI Analysis ──────────────────────────────────────────────
            Paragraph("AI Vision Analysis", styles["h2"]),
            self._ai_table(scan_data, styles),
            Spacer(1, 6*mm),

            # ── 3D Detections ─────────────────────────────────────────────
            Paragraph("3D Detection Coordinates", styles["h2"]),
            Paragraph(
                "Each row maps a YOLOv8 bounding box to a 3D room coordinate (metres). "
                "SHA-256 column hashes the raw pixel region for tamper evidence.",
                ParagraphStyle("note", parent=styles["sub"], alignment=TA_LEFT,
                               textColor=C_GREY, fontSize=7.5),
            ),
            Spacer(1, 3*mm),
            self._coord_table(scan_data.get("detections", []), styles),
            Spacer(1, 6*mm),

            # ── Network ───────────────────────────────────────────────────
            Paragraph("Network Scan Results", styles["h2"]),
            self._network_table(network_report, styles),
            Spacer(1, 8*mm),

            # ── Integrity Footer ──────────────────────────────────────────
            HRFlowable(width="100%", thickness=0.5, color=C_GREY),
            Spacer(1, 3*mm),
            Paragraph(f"SCAN DATA SHA-256:  {scan_hash}", styles["mono"]),
            Spacer(1, 2*mm),
            Paragraph(f"3D COORDS SHA-256:  {coord_hash}", styles["mono"]),
            Spacer(1, 2*mm),
            Paragraph(f"RSA-PSS SIGNATURE (first 64 chars):  {signature[:64]}…", styles["mono"]),
            Spacer(1, 3*mm),
            Paragraph(
                "This certificate is cryptographically signed. Use the 'Verify Integrity' "
                "function in the SafeStay dashboard to confirm authenticity.",
                styles["body"],
            ),
            Spacer(1, 2*mm),
            Paragraph(
                "⚠ If hidden camera signals are detected, physically inspect flagged locations "
                "and report findings to property management or local law enforcement.",
                ParagraphStyle("warn", parent=styles["body"],
                               textColor=C_AMBER, fontSize=7.5),
            ),
        ]

        doc.build(story)
        logger.info("Forensic PDF saved: %s", output_path)

        return {
            "path":          str(output_path),
            "download":      "/api/report/download",
            "sha256_hash":   scan_hash,
            "coord_hash":    coord_hash,
            "rsa_signature": signature,
            "generated_at":  ts_now.isoformat(),
            "status":        "ok",
        }
