"""
SafeStay — main.py
FastAPI entry point.  Provides REST API for:
  • AI lens detection (YOLOv8)
  • Network heartbeat scanning (Scapy + Shannon Entropy)
  • RSA-signed forensic PDF generation
  • Integrity verification
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from detector  import SafeStayEngine, ScanResult
from scanner   import HeartbeatScanner, NetworkReport
from forensics import ForensicReportBuilder, IntegrityVerifier

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("safestay.api")

# ── App Init ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "SafeStay Detection API",
    description = "Hidden camera detection: YOLOv8 + Scapy + RSA forensics",
    version     = "2.3.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ── Singletons ────────────────────────────────────────────────────────────────
_engine   = SafeStayEngine(confidence=float(os.environ.get("YOLO_CONFIDENCE", "0.40")))
_scanner  = HeartbeatScanner()
_forensics = ForensicReportBuilder()
_verifier  = IntegrityVerifier()

# ── In-memory session state ───────────────────────────────────────────────────
_state: dict = {
    "last_scan_result":    None,
    "last_network_report": None,
    "last_report_path":    None,
    "last_report_meta":    None,
    "sessions":            [],
}


# ── Request / Response Models ─────────────────────────────────────────────────

class ScanRequest(BaseModel):
    source:      int | str = Field(0,    description="Camera index or video path")
    num_frames:  int        = Field(12,  ge=1, le=60, description="Frames to analyse")
    network_match: bool     = Field(False)
    ir_detected:   bool     = Field(False)

class NetworkScanRequest(BaseModel):
    network: str  = Field("auto", description="CIDR or 'auto' for auto-detect")
    passive: bool = Field(True,   description="True=passive sniff, False=ARP probe")

class VerifyRequest(BaseModel):
    scan_data:     dict
    expected_hash: str

class ReportRequest(BaseModel):
    session_id: Optional[str] = None


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {
        "status":  "ok",
        "service": "SafeStay Detection API v2.3.0",
        "ts":      int(time.time()),
        "model_loaded": _engine.model is not None,
    }


# ── AI Detection ──────────────────────────────────────────────────────────────

@app.post("/scan/ai", tags=["Detection"])
def scan_ai(req: ScanRequest):
    """
    Run YOLOv8 + Hough Circle lens detection on `num_frames` from `source`.
    Returns detections with 3D coordinates mapped to room space.
    """
    try:
        result: ScanResult = _engine.run_session(
            source        = req.source,
            num_frames    = req.num_frames,
            network_match = req.network_match,
            ir_detected   = req.ir_detected,
        )
        data = result.to_dict()
        _state["last_scan_result"] = data
        _state["sessions"].append(data)
        logger.info("AI scan complete — level=%s peak=%.3f", data["overall_level"], data["peak_score"])
        return JSONResponse(data)
    except Exception as exc:
        logger.exception("AI scan failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Network Scan ──────────────────────────────────────────────────────────────

@app.post("/scan/network", tags=["Detection"])
def scan_network(req: NetworkScanRequest):
    """
    Run passive Scapy heartbeat analysis.
    Computes Shannon Entropy per device — high entropy flags covert video streams.
    """
    try:
        network = _scanner.get_local_network() if req.network == "auto" else req.network
        report: NetworkReport = _scanner.scan(network=network, passive=req.passive)
        data = report.to_dict()
        _state["last_network_report"] = data

        # Fusion logic: update last AI scan with network match if camera vendor found
        if data["camera_count"] > 0 and _state["last_scan_result"]:
            _state["last_scan_result"]["network_match"] = True
            # Re-evaluate fusion CRITICAL
            last = _state["last_scan_result"]
            if last.get("peak_score", 0) > 0.60:
                last["fusion_critical"] = True
                last["overall_level"]   = "CRITICAL"
                last["peak_score"]      = max(last["peak_score"], 0.90)

        logger.info("Network scan done — %d devices, %d cameras, anomalies=%s",
                    data["device_count"], data["camera_count"], data["entropy_anomalies"])
        return JSONResponse(data)
    except Exception as exc:
        logger.exception("Network scan failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Fusion Scan ───────────────────────────────────────────────────────────────

@app.post("/scan/full", tags=["Detection"])
def full_scan(ai_req: ScanRequest, bg: BackgroundTasks):
    """
    Orchestrated full scan:
      1. AI lens detection
      2. Network heartbeat scan
      3. Apply fusion CRITICAL rule
    Returns merged result.
    """
    # Step 1: AI
    try:
        result = _engine.run_session(
            source        = ai_req.source,
            num_frames    = ai_req.num_frames,
            network_match = False,
            ir_detected   = ai_req.ir_detected,
        )
    except Exception as exc:
        raise HTTPException(500, f"AI scan error: {exc}")

    # Step 2: Network
    try:
        network = _scanner.get_local_network()
        net_report = _scanner.scan(network=network, passive=True)
        has_cam_vendor = len(net_report.camera_devices) > 0
    except Exception:
        net_report = None
        has_cam_vendor = False

    # Step 3: Fusion CRITICAL rule
    ai_data = result.to_dict()
    ai_data["network_match"] = has_cam_vendor
    if result.peak_score > 0.60 and has_cam_vendor:
        ai_data["fusion_critical"] = True
        ai_data["overall_level"]   = "CRITICAL"
        ai_data["peak_score"]      = max(result.peak_score, 0.90)

    _state["last_scan_result"]    = ai_data
    _state["last_network_report"] = net_report.to_dict() if net_report else None
    _state["sessions"].append(ai_data)

    return JSONResponse({
        "ai_scan":      ai_data,
        "network_scan": _state["last_network_report"],
    })


# ── Report ────────────────────────────────────────────────────────────────────

@app.post("/generate-report", tags=["Forensics"])
def generate_report(req: ReportRequest):
    """
    Generate an RSA-signed, SHA-256 certified PDF evidence report.
    Embeds AI detections, 3D coordinates, network table, and forensic hashes.
    """
    scan_data = _state.get("last_scan_result")
    if not scan_data:
        # Generate a demo report if no scan has run yet
        scan_data = _demo_scan_data()

    net_report = _state.get("last_network_report")

    try:
        meta = _forensics.build(scan_data=scan_data, network_report=net_report)
        _state["last_report_path"] = meta["path"]
        _state["last_report_meta"] = meta
        logger.info("Report generated: %s", meta["path"])
        return JSONResponse(meta)
    except Exception as exc:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/report/download", tags=["Forensics"])
def download_report():
    """Download the most recently generated PDF report."""
    path = _state.get("last_report_path")
    if not path or not Path(path).exists():
        raise HTTPException(404, "No report found — call /generate-report first")
    return FileResponse(
        path,
        media_type   = "application/pdf",
        filename     = "SafeStay_Forensic_Report.pdf",
    )


# ── Integrity Verification ────────────────────────────────────────────────────

@app.post("/verify-integrity", tags=["Forensics"])
def verify_integrity(req: VerifyRequest):
    """
    Re-hash the submitted scan data and compare to the expected SHA-256.
    This powers the 'Verify Integrity' button in the dashboard.
    """
    result = _verifier.verify(req.scan_data, req.expected_hash)
    status = 200 if result["verified"] else 409
    return JSONResponse(result, status_code=status)


@app.get("/verify-last", tags=["Forensics"])
def verify_last():
    """Auto-verify the last generated report against stored scan data."""
    meta = _state.get("last_report_meta")
    scan = _state.get("last_scan_result")
    if not meta or not scan:
        raise HTTPException(404, "No report or scan data in memory")
    result = _verifier.verify(scan, meta["sha256_hash"])
    result["coord_hash"]          = meta.get("coord_hash")
    result["rsa_signature_start"] = (meta.get("rsa_signature") or "")[:32] + "…"
    return JSONResponse(result)


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats", tags=["System"])
def stats():
    last = _state.get("last_scan_result") or {}
    net  = _state.get("last_network_report") or {}
    return {
        "sessions_total":     len(_state["sessions"]),
        "last_level":         last.get("overall_level", "NONE"),
        "last_peak_score":    last.get("peak_score", 0.0),
        "last_camera_count":  last.get("camera_count", 0),
        "last_fusion":        last.get("fusion_critical", False),
        "network_cameras":    net.get("camera_count", 0),
        "entropy_anomalies":  net.get("entropy_anomalies", []),
        "report_ready":       _state["last_report_path"] is not None,
    }


# ── Demo Helper ───────────────────────────────────────────────────────────────

def _demo_scan_data() -> dict:
    """Pre-baked demo scan for report generation without a prior scan."""
    return {
        "session_id":      "demo_" + uuid.uuid4().hex[:8],
        "frames_analysed": 12,
        "peak_score":      0.94,
        "overall_level":   "CRITICAL",
        "network_match":   True,
        "ir_detected":     True,
        "fusion_critical": True,
        "camera_count":    2,
        "detections": [
            {
                "frame_id":      4,
                "bbox":          [192, 120, 333, 230],
                "ai_confidence": 0.87,
                "host_object":   "smoke detector",
                "is_high_risk":  True,
                "hough_radius":  11.4,
                "coord_3d":      {"x": 1.80, "y": 2.95, "z": 2.40},
                "threat_score":  0.94,
                "threat_level":  "CRITICAL",
                "frame_hash":    "a3f9e1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1",
                "timestamp":     time.time(),
            },
            {
                "frame_id":      7,
                "bbox":          [384, 264, 461, 326],
                "ai_confidence": 0.61,
                "host_object":   "clock",
                "is_high_risk":  True,
                "hough_radius":  7.2,
                "coord_3d":      {"x": 3.60, "y": 3.20, "z": 1.82},
                "threat_score":  0.71,
                "threat_level":  "HIGH",
                "frame_hash":    "b4a0f2e3d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0f1e2d3c4b5a6f7e8d9c0b1a2",
                "timestamp":     time.time(),
            },
        ],
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info("SafeStay API starting on port %d", port)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
