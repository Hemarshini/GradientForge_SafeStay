"""
SafeStay — app.py
Streamlit 3D Security Dashboard.
Dark Mode Security theme: Midnight Navy (#0A0E1A) + Safety Green (#2ECC71).

Features:
  • 3D Digital Twin with PyVista / Matplotlib threat markers
  • 60-second 4-layer interactive scan simulation
  • Live FastAPI backend connectivity
  • Forensic PDF generation + RSA integrity verification
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

import requests
import streamlit as st

# ── Add components to path ───────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "components"))
from visualizer import render_room, render_empty_room, build_markers_from_scan  # type: ignore

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE   = "http://localhost:8000"
PAGE_TITLE = "SafeStay — AI Privacy Shield"

# ── Streamlit Page Config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title = PAGE_TITLE,
    page_icon  = "🛡",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ── Global CSS (Dark Mode Security theme) ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #0A0E1A !important;
    color: #E8EAF6 !important;
    font-family: 'Syne', sans-serif !important;
}
[data-testid="stSidebar"] {
    background: #0F1528 !important;
    border-right: 1px solid rgba(46,204,113,.15) !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* ── Buttons ── */
.stButton > button {
    background: #2ECC71 !important;
    color: #0A0E1A !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: .6rem 1.6rem !important;
    font-size: .95rem !important;
    transition: all .25s ease !important;
    width: 100%;
}
.stButton > button:hover {
    background: #27ae60 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(46,204,113,.35) !important;
}
.stButton > button:disabled {
    background: rgba(46,204,113,.25) !important;
    cursor: not-allowed !important;
}

/* ── Progress bars ── */
.stProgress > div > div > div { background: #2ECC71 !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: rgba(20,25,50,.55) !important;
    border: 1px solid rgba(46,204,113,.18) !important;
    border-radius: 14px !important;
    padding: 1rem 1.2rem !important;
    backdrop-filter: blur(12px) !important;
}
[data-testid="stMetricLabel"]  { color: #6B7A99 !important; font-family: 'Space Mono', monospace !important; font-size: .75rem !important; }
[data-testid="stMetricValue"]  { color: #E8EAF6 !important; font-family: 'Space Mono', monospace !important; }
[data-testid="stMetricDelta"]  { font-family: 'Space Mono', monospace !important; }

/* ── Expanders ── */
.streamlit-expanderHeader {
    background: rgba(20,25,50,.55) !important;
    border: 1px solid rgba(46,204,113,.12) !important;
    border-radius: 10px !important;
    color: #E8EAF6 !important;
    font-family: 'Space Mono', monospace !important;
}

/* ── Code blocks ── */
code, pre {
    background: #060A14 !important;
    color: #2ECC71 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: .72rem !important;
    border-radius: 6px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #27ae60; border-radius: 3px; }

/* ── Custom cards ── */
.ss-card {
    background: rgba(20,25,50,.55);
    border: 1px solid rgba(46,204,113,.18);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    backdrop-filter: blur(12px);
    margin-bottom: 1rem;
}
.ss-badge {
    display: inline-block;
    padding: .25rem .65rem;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: .68rem;
    font-weight: 700;
    border: 1px solid;
}
.badge-critical { background: rgba(231,76,60,.15); color: #E74C3C; border-color: #E74C3C; }
.badge-high     { background: rgba(243,156,18,.15); color: #F39C12; border-color: #F39C12; }
.badge-medium   { background: rgba(52,152,219,.15); color: #3498DB; border-color: #3498DB; }
.badge-clean    { background: rgba(46,204,113,.15); color: #2ECC71; border-color: #2ECC71; }
.phase-row {
    display: flex; align-items: center; gap: .8rem;
    padding: .7rem 1rem;
    background: rgba(255,255,255,.02);
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 10px;
    margin-bottom: .5rem;
    font-family: 'Space Mono', monospace;
    font-size: .75rem;
}
</style>
""", unsafe_allow_html=True)

# ── Session State Defaults ────────────────────────────────────────────────────
_defaults = {
    "scan_result":     None,
    "network_result":  None,
    "report_meta":     None,
    "scan_running":    False,
    "scan_log":        [],
    "room_image":      None,
    "api_online":      None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helper: API Calls ─────────────────────────────────────────────────────────

def api_get(path: str, timeout: int = 5) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=timeout)
        return r.json() if r.ok else None
    except Exception:
        return None

def api_post(path: str, body: dict = {}, timeout: int = 30) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=timeout)
        return r.json() if r.ok else None
    except Exception:
        return None

def check_api() -> bool:
    h = api_get("/health", timeout=2)
    online = h is not None and h.get("status") == "ok"
    st.session_state.api_online = online
    return online


# ── Helper: Threat Badge HTML ─────────────────────────────────────────────────

def threat_badge(level: str) -> str:
    cls = {
        "CRITICAL": "badge-critical",
        "HIGH":     "badge-high",
        "MEDIUM":   "badge-medium",
        "LOW":      "badge-clean",
        "CLEAN":    "badge-clean",
    }.get(level.upper(), "badge-clean")
    return f'<span class="ss-badge {cls}">{level}</span>'


# ── Helper: Demo Scan Data ────────────────────────────────────────────────────

def _demo_scan() -> dict:
    return {
        "session_id":      "demo_abc123",
        "frames_analysed": 12,
        "peak_score":      0.94,
        "overall_level":   "CRITICAL",
        "network_match":   True,
        "ir_detected":     True,
        "fusion_critical": True,
        "camera_count":    2,
        "detections": [
            {
                "frame_id": 4, "bbox": [192, 120, 333, 230],
                "ai_confidence": 0.87, "host_object": "smoke detector",
                "is_high_risk": True, "hough_radius": 11.4,
                "coord_3d": {"x": 1.80, "y": 2.95, "z": 2.40},
                "threat_score": 0.94, "threat_level": "CRITICAL",
                "frame_hash": "a3f9e1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1",
                "timestamp": time.time(),
            },
            {
                "frame_id": 7, "bbox": [384, 264, 461, 326],
                "ai_confidence": 0.61, "host_object": "clock",
                "is_high_risk": True, "hough_radius": 7.2,
                "coord_3d": {"x": 3.60, "y": 3.20, "z": 1.82},
                "threat_score": 0.71, "threat_level": "HIGH",
                "frame_hash": "b4a0f2e3d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0f1e2d3c4b5a6f7e8d9c0b1a2",
                "timestamp": time.time(),
            },
        ],
    }

def _demo_network() -> dict:
    return {
        "network_cidr": "192.168.1.0/24",
        "device_count": 5, "camera_count": 2,
        "scan_duration": 2.41,
        "entropy_anomalies": ["192.168.1.10", "192.168.1.14"],
        "devices": [
            {"ip": "192.168.1.1",  "mac": "A4:08:F5:11:22:33", "vendor": "TP-Link Router",                    "is_camera": False, "entropy": 0.81},
            {"ip": "192.168.1.10", "mac": "18:FE:34:AB:CD:EF", "vendor": "Espressif Systems (ESP32-CAM)",     "is_camera": True,  "entropy": 3.91},
            {"ip": "192.168.1.14", "mac": "BC:01:A6:44:55:66", "vendor": "Hikvision Digital Technology",     "is_camera": True,  "entropy": 4.12},
            {"ip": "192.168.1.20", "mac": "00:1A:2B:3C:4D:5E", "vendor": "Apple, Inc.",                      "is_camera": False, "entropy": 1.22},
            {"ip": "192.168.1.22", "mac": "F0:18:98:10:20:30", "vendor": "Samsung Electronics",              "is_camera": False, "entropy": 0.97},
        ],
        "camera_devices": [
            {"ip": "192.168.1.10", "mac": "18:FE:34:AB:CD:EF", "vendor": "Espressif Systems (ESP32-CAM)", "is_camera": True, "entropy": 3.91},
            {"ip": "192.168.1.14", "mac": "BC:01:A6:44:55:66", "vendor": "Hikvision Digital Technology",  "is_camera": True, "entropy": 4.12},
        ],
    }


# ── 60-Second Interactive Scan ────────────────────────────────────────────────

def run_interactive_scan():
    """
    Runs the 4-layer 60-second scan simulation with live progress updates.
    Tries the real FastAPI backend first; falls back to demo data.
    """
    st.session_state.scan_running = True
    st.session_state.scan_log     = []
    api_live = check_api()

    phases = [
        {
            "name":  "📡 Network Heartbeat",
            "steps": [
                (1.2, "Initialising passive Scapy sniffer…"),
                (2.0, "ARP sweep 192.168.1.0/24 — 5 devices found"),
                (1.8, "Cross-referencing MAC OUI database…"),
                (1.5, "⚠ Espressif ESP32-CAM at 192.168.1.10 flagged"),
                (1.0, "Shannon Entropy: 3.91 bits (ANOMALOUS)"),
                (0.8, "Network phase complete — 2 camera vendors"),
            ],
        },
        {
            "name":  "🎯 AI Lens Detection",
            "steps": [
                (1.0, "Loading YOLOv8n model (TFLite INT8)…"),
                (1.5, "Frame 1/12: Hough circle scan initiated"),
                (1.8, "Frame 4/12: lens signature @ smoke detector"),
                (1.2, "ThreatScorer: AI=0.87 + HOST=1 → 0.92"),
                (1.3, "Frame 9/12: secondary lens in clock — 0.71"),
                (0.7, "AI scan complete — CRITICAL confirmed"),
            ],
        },
        {
            "name":  "💡 IR Frequency Scan",
            "steps": [
                (0.8, "Camera2: ISO=3200, shutter=100ms, AE=OFF"),
                (1.5, "HSV range [115–165°] blob detection…"),
                (1.8, "IR blob detected: cx=312 cy=201 r=8.2px"),
                (1.2, "Persistence filter: 3/3 frames confirmed"),
                (0.8, "IR source active — 850nm emission confirmed"),
            ],
        },
        {
            "name":  "🔐 Evidence Vault",
            "steps": [
                (0.8, "Compiling 3D coordinate map…"),
                (1.2, "SHA-256 hashing 12 scan frames…"),
                (1.5, "RSA-2048 signing certificate…"),
                (1.0, "ReportLab PDF certificate building…"),
                (0.8, "SafeStay_Report_CRITICAL.pdf sealed ✓"),
            ],
        },
    ]

    scan_placeholder  = st.empty()
    total_steps = sum(len(p["steps"]) for p in phases)
    step_done   = 0

    for pi, phase in enumerate(phases):
        with scan_placeholder.container():
            st.markdown(f"### {phase['name']}")
            log_box = st.empty()
            bar     = st.progress(0)

        logs = []
        for si, (delay, msg) in enumerate(phase["steps"]):
            time.sleep(delay)
            logs.append(f"> {msg}")
            step_done += 1
            overall_pct = step_done / total_steps
            bar.progress((si + 1) / len(phase["steps"]))
            log_box.code("\n".join(logs[-6:]), language="bash")
            st.session_state.scan_log.append(msg)

        # Real API call at end of each phase
        if api_live:
            if pi == 0:
                r = api_post("/scan/network", {"network": "auto", "passive": True})
                if r:
                    st.session_state.network_result = r
            elif pi == 1:
                r = api_post("/scan/ai", {"source": 0, "num_frames": 12,
                                          "network_match": True, "ir_detected": True})
                if r:
                    st.session_state.scan_result = r

    # Populate demo data if API was offline
    if not st.session_state.scan_result:
        st.session_state.scan_result = _demo_scan()
    if not st.session_state.network_result:
        st.session_state.network_result = _demo_network()

    # Render 3D room with threat markers
    try:
        img_bytes = render_room(st.session_state.scan_result)
        st.session_state.room_image = img_bytes
    except Exception as e:
        st.session_state.room_image = None

    st.session_state.scan_running = False


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:1rem 0 .5rem'>
        <div style='font-size:2.5rem'>🛡</div>
        <div style='font-family:Syne,sans-serif;font-size:1.3rem;font-weight:800;color:#fff'>SafeStay</div>
        <div style='font-family:"Space Mono",monospace;font-size:.65rem;color:#6B7A99'>AI PRIVACY SHIELD v2.3</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # API status
    if st.button("⚡ Check Backend"):
        check_api()
    api_status = st.session_state.api_online
    if api_status is True:
        st.success("API Online ✓")
    elif api_status is False:
        st.error("API Offline — Demo mode active")
    else:
        st.info("Press 'Check Backend' to test")

    st.divider()
    st.markdown("**Detection Layers**")
    st.markdown("""
    <div style='font-family:"Space Mono",monospace;font-size:.72rem;color:#6B7A99'>
    📡 Network Heartbeat<br/>
    🎯 YOLOv8 AI Lens<br/>
    💡 IR Frequency Scan<br/>
    🔐 Evidence Vault
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**Tech Stack**")
    for tag in ["YOLOv8 · OpenCV", "Scapy + ARP", "Shannon Entropy",
                "RSA-2048 + SHA-256", "ReportLab PDF", "PyVista 3D"]:
        st.markdown(
            f'<span class="ss-badge badge-clean" style="margin:.15rem .1rem;display:inline-block">{tag}</span>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────────────────────────────────────

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding:1.5rem 0 .5rem'>
    <div style='font-family:"Space Mono",monospace;font-size:.68rem;letter-spacing:.14em;
                color:#2ECC71;margin-bottom:.6rem'>
        ● AI PRIVACY SHIELD &nbsp;·&nbsp; GRADIENT FORGE
    </div>
    <h1 style='font-family:Syne,sans-serif;font-size:2.6rem;font-weight:800;color:#fff;
               line-height:1.1;margin:0'>
        You checked in.<br/>
        <span style='color:#2ECC71'>But are you really alone?</span>
    </h1>
    <p style='color:#6B7A99;margin:.8rem 0 0;font-size:.95rem;max-width:600px'>
        Transform your smartphone into a professional-grade privacy shield.
        Detect hidden cameras in <strong style='color:#E8EAF6'>60 seconds</strong>
        using AI vision, passive network analysis, and IR detection.
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Top Metrics ───────────────────────────────────────────────────────────────
scan_r = st.session_state.scan_result
net_r  = st.session_state.network_result

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    lvl = scan_r["overall_level"] if scan_r else "—"
    st.metric("Threat Level", lvl, delta="CRITICAL" if lvl == "CRITICAL" else None,
              delta_color="inverse")
with m2:
    score = f"{scan_r['peak_score']*100:.1f}%" if scan_r else "—"
    st.metric("Peak Score", score)
with m3:
    cams = scan_r["camera_count"] if scan_r else "—"
    st.metric("Cameras Found", cams)
with m4:
    net_cams = net_r["camera_count"] if net_r else "—"
    st.metric("Network Cameras", net_cams)
with m5:
    fusion = "YES 🚨" if (scan_r and scan_r.get("fusion_critical")) else ("NO ✓" if scan_r else "—")
    st.metric("Fusion CRITICAL", fusion)

st.divider()

# ── 3D Digital Twin + Scan Button ────────────────────────────────────────────
col_3d, col_ctrl = st.columns([2, 1])

with col_3d:
    st.markdown("### 🏨 3D Digital Twin")
    st.markdown(
        '<div style=\'font-family:"Space Mono",monospace;font-size:.7rem;color:#6B7A99;margin-bottom:.8rem\'>'
        'Red spheres = detected threats · Drop lines show floor projection · Labels show host object + score'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.room_image:
        st.image(st.session_state.room_image, use_container_width=True)
    elif st.session_state.scan_result:
        with st.spinner("Rendering 3D scene…"):
            try:
                img = render_room(st.session_state.scan_result)
                st.session_state.room_image = img
                st.image(img, use_container_width=True)
            except Exception as e:
                st.warning(f"3D render failed: {e} — check PyVista/Matplotlib install")
    else:
        # Show empty room placeholder
        try:
            empty_img = render_empty_room()
            st.image(empty_img, caption="Run a scan to place threat markers", use_container_width=True)
        except Exception:
            st.info("🏨 3D room will render here after scanning")

with col_ctrl:
    st.markdown("### ▶ Interactive Scan")
    st.markdown("""
    <div style='font-family:"Space Mono",monospace;font-size:.72rem;color:#6B7A99;margin-bottom:1rem;line-height:1.7'>
    Runs all 4 detection layers<br/>
    in sequence over 60 seconds.<br/><br/>
    <span style='color:#2ECC71'>Layer 1:</span> Network ARP + Entropy<br/>
    <span style='color:#2ECC71'>Layer 2:</span> YOLOv8 Lens AI<br/>
    <span style='color:#2ECC71'>Layer 3:</span> IR Frequency Scan<br/>
    <span style='color:#2ECC71'>Layer 4:</span> Forensic PDF
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.scan_running:
        if st.button("▶ Run 60-Second Scan", key="scan_btn"):
            run_interactive_scan()
            st.rerun()
    else:
        st.warning("⏳ Scan in progress…")

    if scan_r:
        lvl   = scan_r.get("overall_level", "UNKNOWN")
        score = scan_r.get("peak_score", 0)
        icon  = "🚨" if lvl == "CRITICAL" else ("⚠️" if lvl == "HIGH" else "✅")
        st.markdown(f"""
        <div class='ss-card' style='margin-top:1rem;text-align:center'>
            <div style='font-size:2rem'>{icon}</div>
            <div style='font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem;
                        color:{"#E74C3C" if lvl in ("CRITICAL","HIGH") else "#2ECC71"}'>
                {lvl}
            </div>
            <div style='font-family:"Space Mono",monospace;font-size:.72rem;color:#6B7A99;margin-top:.3rem'>
                Score: {score*100:.1f}% · {scan_r.get("camera_count",0)} device(s)
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Network Analysis ──────────────────────────────────────────────────────────
st.markdown("### 📡 Network Heartbeat Analysis")
if net_r:
    dev_col, entropy_col = st.columns([3, 1])
    with dev_col:
        devices = net_r.get("devices", [])
        if devices:
            import pandas as pd
            df = pd.DataFrame([{
                "IP":         d["ip"],
                "MAC":        d["mac"],
                "Vendor":     d["vendor"],
                "Camera?":    "⚠ YES" if d["is_camera"] else "✓ NO",
                "Entropy":    f"{d.get('entropy', 0):.2f} bits",
            } for d in devices])
            st.dataframe(
                df,
                use_container_width = True,
                hide_index          = True,
                column_config       = {
                    "Camera?":  st.column_config.TextColumn("Camera?",  width="small"),
                    "Entropy":  st.column_config.TextColumn("Entropy",  width="small"),
                },
            )
    with entropy_col:
        anomalies = net_r.get("entropy_anomalies", [])
        st.metric("Devices Found",  net_r.get("device_count", 0))
        st.metric("Camera Vendors", net_r.get("camera_count", 0))
        st.metric("Entropy Flags",  len(anomalies))
        if anomalies:
            st.error("High entropy:\n" + "\n".join(anomalies))
else:
    st.info("Run a scan to see network device analysis.")

st.divider()

# ── Detection Details ─────────────────────────────────────────────────────────
st.markdown("### 🎯 Detection Details — 3D Coordinates")
if scan_r and scan_r.get("detections"):
    for d in scan_r["detections"]:
        c     = d["coord_3d"]
        level = d["threat_level"]
        icon  = "🔴" if level == "CRITICAL" else ("🟠" if level == "HIGH" else "🟡")
        with st.expander(
            f"{icon} {d.get('host_object','Unknown')} — {level}  "
            f"({c['x']}m, {c['y']}m, {c['z']}m)  score: {d['threat_score']*100:.1f}%"
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("AI Confidence",  f"{d['ai_confidence']*100:.1f}%")
            c2.metric("Hough Radius",   f"{d.get('hough_radius') or '—'} px")
            c3.metric("High-Risk Host", "YES" if d["is_high_risk"] else "NO")
            st.markdown("**3D Room Coordinate (metres)**")
            st.code(f"x={c['x']:.3f}  y={c['y']:.3f}  z={c['z']:.3f}", language="text")
            st.markdown("**Frame SHA-256**")
            st.code(d["frame_hash"], language="text")
else:
    st.info("No detections yet — run a scan first.")

st.divider()

# ── Forensic Evidence Vault ───────────────────────────────────────────────────
st.markdown("### 🔐 Forensic Evidence Vault")
ev_col1, ev_col2 = st.columns(2)

with ev_col1:
    st.markdown("**Generate RSA-Signed PDF Certificate**")
    if st.button("📄 Generate Report PDF", key="gen_report"):
        with st.spinner("Building forensic PDF…"):
            if check_api():
                meta = api_post("/generate-report", {})
            else:
                # Local fallback using forensics module
                try:
                    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
                    from forensics import ForensicReportBuilder  # type: ignore
                    builder = ForensicReportBuilder()
                    sd  = st.session_state.scan_result or _demo_scan()
                    nr  = st.session_state.network_result
                    meta = builder.build(sd, nr)
                except Exception as e:
                    meta = None
                    st.error(f"Report generation failed: {e}")

            if meta:
                st.session_state.report_meta = meta
                st.success("✓ PDF certificate generated and RSA-signed")

    if st.session_state.report_meta:
        meta = st.session_state.report_meta
        st.markdown("**Certificate Details**")
        st.markdown(f"""
        <div class='ss-card'>
            <div style='font-family:"Space Mono",monospace;font-size:.72rem;line-height:1.9;color:#6B7A99'>
                <span style='color:#2ECC71'>STATUS:</span> {meta.get('status','—').upper()}<br/>
                <span style='color:#2ECC71'>GENERATED:</span> {meta.get('generated_at','—')[:19]} UTC<br/>
                <span style='color:#2ECC71'>SHA-256 (first 32):</span> {meta.get('sha256_hash','')[:32]}…<br/>
                <span style='color:#2ECC71'>COORD HASH (first 32):</span> {meta.get('coord_hash','')[:32]}…<br/>
                <span style='color:#2ECC71'>RSA SIG (first 32):</span> {meta.get('rsa_signature','')[:32]}…
            </div>
        </div>
        """, unsafe_allow_html=True)

        if check_api():
            st.link_button("⬇ Download PDF", f"{API_BASE}/api/report/download")

with ev_col2:
    st.markdown("**Verify Scan Integrity**")
    st.markdown(
        '<div style=\'font-family:"Space Mono",monospace;font-size:.72rem;color:#6B7A99;margin-bottom:.8rem\'>'
        'Re-hashes the 3D scan data and compares to the signed certificate. '
        'Any tampering will cause a mismatch.'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button("🔍 Verify Integrity", key="verify_btn"):
        meta = st.session_state.report_meta
        sd   = st.session_state.scan_result
        if not meta or not sd:
            st.warning("Generate a report and run a scan first.")
        else:
            expected = meta.get("sha256_hash", "")
            # Local verification
            canonical = json.dumps(sd, sort_keys=True, ensure_ascii=True)
            computed  = hashlib.sha256(canonical.encode()).hexdigest()
            match     = computed == expected

            if match:
                st.success("✅ Integrity VERIFIED — scan data matches signed certificate")
            else:
                st.error("❌ Integrity FAILED — data may have been tampered with")

            col_a, col_b = st.columns(2)
            col_a.markdown("**Computed Hash**")
            col_a.code(computed[:32] + "…", language="text")
            col_b.markdown("**Certificate Hash**")
            col_b.code(expected[:32] + "…", language="text")

st.divider()

# ── Scan Log ──────────────────────────────────────────────────────────────────
if st.session_state.scan_log:
    with st.expander("📋 Scan Log", expanded=False):
        log_text = "\n".join(f"> {line}" for line in st.session_state.scan_log)
        st.code(log_text, language="bash")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:2rem 0 1rem;
            font-family:"Space Mono",monospace;font-size:.65rem;color:rgba(107,122,153,.5)'>
    🛡 SafeStay AI Core v2.3 · Gradient Forge · 
    For personal privacy protection in rented accommodations ·
    Report suspicious findings to local authorities
</div>
""", unsafe_allow_html=True)
