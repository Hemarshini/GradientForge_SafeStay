import streamlit as st
import time
import random

# ── PAGE CONFIG ──
st.set_page_config(
    page_title="SafeStay – By Gradient Forge",
    page_icon="⊕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── GLOBAL CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg: #0A0E1A;
    --bg2: #0d1220;
    --card: #131929;
    --card-border: #1e2a3a;
    --green: #2ECC71;
    --green-glow: rgba(46,204,113,0.15);
    --red: #E74C3C;
    --text: #e8edf5;
    --muted: #6b7a96;
    --muted2: #8892a4;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: #0A0E1A !important;
    color: #e8edf5 !important;
    font-family: 'Montserrat', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: #0d1220 !important; }

/* Remove default Streamlit padding */
.block-container { padding-top: 0 !important; max-width: 1200px; }
section[data-testid="stVerticalBlock"] { gap: 0 !important; }

/* NAVBAR */
.ss-nav {
    position: sticky; top: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 40px; height: 72px;
    background: rgba(10,14,26,0.95);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #1e2a3a;
    margin-bottom: 0;
}
.nav-logo { display: flex; align-items: center; gap: 10px; }
.nav-logo-icon {
    width: 36px; height: 36px; border-radius: 8px;
    background: rgba(46,204,113,0.15); border: 1.5px solid #2ECC71;
    display: inline-flex; align-items: center; justify-content: center;
    color: #2ECC71; font-size: 16px;
}
.brand { font-size: 15px; font-weight: 700; color: #e8edf5; }
.sub { font-size: 9px; font-weight: 500; letter-spacing: 0.15em; color: #6b7a96; text-transform: uppercase; }
.nav-links { display: flex; gap: 36px; }
.nav-links a {
    font-size: 11px; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: #8892a4; text-decoration: none;
}
.nav-links a:hover { color: #e8edf5; }
.btn-cta {
    background: #2ECC71; color: #0A0E1A;
    font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    padding: 10px 22px; border-radius: 6px; text-decoration: none;
    display: inline-flex; align-items: center;
}

/* HERO */
.ss-hero {
    padding: 80px 80px 60px;
    display: grid; grid-template-columns: 1fr 380px; gap: 60px;
    align-items: center; max-width: 1200px; margin: 0 auto;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(19,25,41,0.9); border: 1px solid #1e2a3a;
    padding: 6px 14px; border-radius: 4px;
    font-size: 10px; font-weight: 600; letter-spacing: 0.15em; color: #8892a4;
    text-transform: uppercase; margin-bottom: 28px;
}
.hero-badge-dot {
    width: 7px; height: 7px; border-radius: 50%; background: #2ECC71;
    display: inline-block; animation: pulseDot 2s infinite;
}
@keyframes pulseDot { 0%,100%{opacity:1} 50%{opacity:0.4} }
.hero-h1 {
    font-size: 62px; font-weight: 900; line-height: 1.05;
    margin-bottom: 24px; letter-spacing: -0.02em; color: #e8edf5;
}
.hero-h1 .accent { color: #E74C3C; text-decoration: underline; text-decoration-color: #E74C3C; }
.hero-sub { font-size: 16px; color: #8892a4; max-width: 480px; margin-bottom: 40px; line-height: 1.7; }
.hero-sub strong { color: #e8edf5; }
.hero-actions { display: flex; align-items: center; gap: 28px; margin-bottom: 50px; }
.btn-scan {
    background: #2ECC71; color: #0A0E1A;
    font-size: 14px; font-weight: 700;
    padding: 14px 28px; border-radius: 8px;
    text-decoration: none; display: inline-flex; align-items: center; gap: 10px;
    animation: pulseBtn 2.5s infinite;
}
@keyframes pulseBtn {
    0%,100% { box-shadow: 0 0 0 0 rgba(46,204,113,0.4); }
    50% { box-shadow: 0 0 0 12px rgba(46,204,113,0); }
}
.hero-stats { display: flex; gap: 48px; }
.hero-stat .num { font-size: 22px; font-weight: 800; color: #e8edf5; }
.hero-stat .lbl { font-size: 9px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7a96; margin-top: 2px; }

/* RADAR WIDGET */
.radar-widget {
    background: #131929; border: 1px solid #1e2a3a;
    border-radius: 12px; overflow: hidden;
}
.radar-top {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 18px; border-bottom: 1px solid #1e2a3a;
}
.radar-top span { font-size: 10px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7a96; }
.radar-online { color: #2ECC71 !important; display: flex; align-items: center; gap: 6px; }
.radar-online::before { content:''; display:inline-block; width:7px; height:7px; border-radius:50%; background:#2ECC71; }
.radar-bottom { display: flex; justify-content: space-between; padding: 14px 18px; }
.radar-bottom .rl { font-size: 10px; color: #6b7a96; text-transform: uppercase; }
.radar-anomalies { font-size: 11px; font-weight: 700; color: #E74C3C; }

/* SECTION COMMON */
.ss-section { padding: 80px 80px; max-width: 1200px; margin: 0 auto; }
.section-label {
    display: flex; align-items: center; gap: 10px;
    font-size: 10px; font-weight: 600; letter-spacing: 0.2em;
    text-transform: uppercase; color: #E74C3C; margin-bottom: 28px;
}
.section-label-line { width: 28px; height: 2px; background: #E74C3C; }
.section-label.green { color: #2ECC71; }
.section-label.green .section-label-line { background: #2ECC71; }
.section-divider { height: 1px; background: #1e2a3a; max-width: 1200px; margin: 0 auto; }

/* THREAT */
.threat-header { display: grid; grid-template-columns: 1fr 1fr; gap: 60px; margin-bottom: 60px; align-items: end; }
.threat-h2 { font-size: 48px; font-weight: 900; line-height: 1.1; letter-spacing: -0.02em; color: #e8edf5; }
.threat-h2 .dim { color: #6b7a96; }
.threat-desc { font-size: 15px; color: #8892a4; line-height: 1.75; max-width: 380px; }
.stat-cards { display: grid; grid-template-columns: repeat(3,1fr); gap: 18px; }
.stat-card {
    background: #131929; border: 1px solid #1e2a3a;
    border-radius: 10px; padding: 28px 24px; position: relative; overflow: hidden;
}
.stat-card::before {
    content:''; position:absolute; inset:0;
    background: linear-gradient(135deg, rgba(231,76,60,0.08) 0%, transparent 60%);
    pointer-events:none;
}
.stat-card-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:24px; }
.stat-card-icon { color: #E74C3C; font-size: 18px; }
.stat-card-num-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #6b7a96; }
.stat-card-num { font-size: 52px; font-weight: 900; color: #E74C3C; line-height: 1; margin-bottom: 12px; }
.stat-card-title { font-size: 10px; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; color: #8892a4; margin-bottom: 12px; }
.stat-card-desc { font-size: 13px; color: #6b7a96; line-height: 1.6; }
.threat-sources { margin-top: 20px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #6b7a96; letter-spacing: 0.1em; text-transform: uppercase; }

/* TECHNOLOGY */
.tech-header { margin-bottom: 60px; display: grid; grid-template-columns: 1fr 1fr; gap: 60px; align-items: end; }
.tech-h2 { font-size: 48px; font-weight: 900; line-height: 1.1; letter-spacing: -0.02em; color: #e8edf5; }
.tech-h2 .green { color: #2ECC71; }
.tech-desc { font-size: 15px; color: #8892a4; line-height: 1.75; max-width: 380px; }
.tech-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 18px; }
.tech-card { background: #131929; border: 1px solid #1e2a3a; border-radius: 10px; overflow: hidden; }
.tech-card-body { padding: 28px; }
.tech-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.tech-card-icon-box {
    width: 36px; height: 36px; border-radius: 7px;
    background: rgba(46,204,113,0.15); border: 1px solid rgba(46,204,113,0.3);
    display: inline-flex; align-items: center; justify-content: center;
    color: #2ECC71; font-size: 16px;
}
.tech-card-layer { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #6b7a96; display: flex; align-items: center; gap: 6px; }
.tech-card-title { font-size: 22px; font-weight: 700; margin-bottom: 12px; color: #e8edf5; }
.tech-card-desc { font-size: 14px; color: #8892a4; line-height: 1.65; margin-bottom: 20px; }
.tech-card-tags { display: flex; flex-direction: column; gap: 6px; }
.tech-tag { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #2ECC71; display: flex; align-items: center; gap: 8px; }
.tech-tag::before { content:''; display:inline-block; width:6px; height:6px; border-radius:50%; background:#2ECC71; }
.live-badge {
    display: inline-block;
    background: rgba(19,25,41,0.9); border: 1px solid #1e2a3a;
    padding: 4px 10px; border-radius: 4px;
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; color: #2ECC71;
}
.tech-live-feed {
    background: #060d0a; position: relative; overflow: hidden;
    height: 160px; display: flex; align-items: center; justify-content: center;
    background-image: repeating-linear-gradient(to bottom, transparent 0px, transparent 3px, rgba(0,0,0,0.15) 3px, rgba(0,0,0,0.15) 4px),
                      linear-gradient(rgba(46,204,113,0.06) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(46,204,113,0.06) 1px, transparent 1px);
    background-size: 4px 4px, 30px 30px, 30px 30px;
    padding: 12px;
}

/* SIMULATION */
.sim-terminal { background: #131929; border: 1px solid #1e2a3a; border-radius: 10px; overflow: hidden; }
.sim-titlebar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 20px; background: rgba(0,0,0,0.2); border-bottom: 1px solid #1e2a3a;
}
.sim-dots { display: flex; gap: 6px; }
.sim-dots span { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
.sim-dot-r { background: #ff5f57; }
.sim-dot-y { background: #febc2e; }
.sim-dot-g { background: #28c840; }
.sim-session { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #6b7a96; letter-spacing: 0.1em; }
.sim-phases { display: grid; grid-template-columns: repeat(3,1fr); border-bottom: 1px solid #1e2a3a; }
.sim-phase {
    padding: 16px 20px; border-right: 1px solid #1e2a3a;
    display: flex; align-items: center; justify-content: space-between;
}
.sim-phase:last-child { border-right: none; }
.sim-phase-left { display: flex; align-items: center; gap: 10px; }
.sim-phase-icon {
    width: 28px; height: 28px; border-radius: 6px;
    background: rgba(46,204,113,0.1); border: 1px solid rgba(46,204,113,0.2);
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 13px;
}
.ph-label { font-size: 9px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #6b7a96; }
.ph-name { font-size: 13px; font-weight: 600; color: #e8edf5; }
.sim-check { font-size: 16px; color: #6b7a96; }
.sim-check.done { color: #2ECC71; }
.sim-log {
    height: 280px; overflow-y: auto; padding: 20px;
    font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.8;
    color: #8892a4; background: rgba(0,0,0,0.2);
}
.log-green { color: #2ECC71; }
.log-red { color: #E74C3C; }
.log-header { color: #e8edf5; font-weight: 600; }
.log-dim { color: #6b7a96; }

/* TRUST */
.trust-cards { display: grid; grid-template-columns: repeat(4,1fr); gap: 18px; margin-bottom: 50px; }
.trust-card { background: #131929; border: 1px solid #1e2a3a; border-radius: 10px; padding: 28px 22px; }
.trust-card-icon {
    width: 40px; height: 40px; border-radius: 8px;
    background: rgba(46,204,113,0.15); border: 1px solid rgba(46,204,113,0.25);
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 18px; margin-bottom: 18px;
}
.trust-card-title { font-size: 15px; font-weight: 700; margin-bottom: 12px; color: #e8edf5; }
.trust-card-desc { font-size: 13px; color: #8892a4; line-height: 1.65; }

/* CTA BANNER */
.cta-banner {
    background: linear-gradient(135deg, rgba(46,204,113,0.08) 0%, rgba(19,25,41,1) 60%);
    border: 1px solid rgba(46,204,113,0.2); border-radius: 12px;
    padding: 48px; display: flex; align-items: center; justify-content: space-between; gap: 40px;
}
.cta-banner-label { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: #2ECC71; margin-bottom: 16px; }
.cta-banner-title { font-size: 24px; font-weight: 800; line-height: 1.3; color: #e8edf5; }

/* FOOTER */
.ss-footer {
    border-top: 1px solid #1e2a3a; padding: 20px 80px;
    display: flex; justify-content: space-between; align-items: center;
    max-width: 1200px; margin: 0 auto;
}
.footer-l { display: flex; align-items: center; gap: 8px; font-size: 11px; color: #6b7a96; letter-spacing: 0.1em; }
.footer-r { display: flex; align-items: center; gap: 16px; }
.footer-badge { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #6b7a96; }
.footer-online { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #2ECC71; display: flex; align-items: center; gap: 6px; }
.footer-online::before { content:''; width:6px; height:6px; border-radius:50%; background:#2ECC71; display:inline-block; animation: pulseDot 2s infinite; }

/* Streamlit button overrides */
.stButton > button {
    background: rgba(46,204,113,0.1) !important;
    border: 1px solid rgba(46,204,113,0.25) !important;
    color: #2ECC71 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    padding: 8px 20px !important;
    border-radius: 5px !important;
}
.stButton > button:hover {
    background: rgba(46,204,113,0.2) !important;
    border-color: #2ECC71 !important;
}
.stProgress > div > div > div { background-color: #2ECC71 !important; }

/* Hide streamlit chrome */
#MainMenu, footer[data-testid="stAppViewFooter"], header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── NAV ──
st.markdown("""
<div class="ss-nav">
  <div class="nav-logo">
    <span class="nav-logo-icon">⊕</span>
    <div>
      <div class="brand">SafeStay</div>
      <div class="sub">By Gradient Forge</div>
    </div>
  </div>
  <div class="nav-links">
    <a href="#threat">The Threat</a>
    <a href="#technology">Technology</a>
    <a href="#simulation">Simulation</a>
    <a href="#privacy">Privacy</a>
  </div>
  <a href="#" class="btn-cta">Get Early Access</a>
</div>
""", unsafe_allow_html=True)

# ── HERO ──
st.markdown("""
<div class="ss-hero">
  <div class="hero-content">
    <div class="hero-badge"><span class="hero-badge-dot"></span> SafeStay V1.0 · On-Device AI</div>
    <h1 class="hero-h1">You checked in.<br>But are you<br><span class="accent">really alone</span>?</h1>
    <p class="hero-sub">Transform your smartphone into a professional-grade privacy shield. Scan rooms in <strong>60 seconds</strong> with AI-powered hidden camera detection.</p>
    <div class="hero-actions">
      <a href="#simulation" class="btn-scan">⊕ Start Scanning →</a>
    </div>
    <div class="hero-stats">
      <div class="hero-stat">
        <div class="num">0</div>
        <div class="lbl">Data Leaves Device</div>
      </div>
      <div class="hero-stat">
        <div class="num">&lt;60S</div>
        <div class="lbl">Full Room Sweep</div>
      </div>
      <div class="hero-stat">
        <div class="num">SHA-256</div>
        <div class="lbl">Evidence Integrity</div>
      </div>
    </div>
  </div>
  <div class="radar-widget">
    <div class="radar-top">
      <span>Live Radar</span>
      <span class="radar-online">Online</span>
    </div>
    <div style="background:#060d0a;height:200px;display:flex;align-items:center;justify-content:center;">
      <svg viewBox="0 0 300 240" width="300" height="240" xmlns="http://www.w3.org/2000/svg">
        <circle cx="150" cy="120" r="100" fill="none" stroke="rgba(46,204,113,0.12)" stroke-width="1"/>
        <circle cx="150" cy="120" r="75" fill="none" stroke="rgba(46,204,113,0.12)" stroke-width="1"/>
        <circle cx="150" cy="120" r="50" fill="none" stroke="rgba(46,204,113,0.12)" stroke-width="1"/>
        <circle cx="150" cy="120" r="25" fill="none" stroke="rgba(46,204,113,0.12)" stroke-width="1"/>
        <line x1="150" y1="20" x2="150" y2="220" stroke="rgba(46,204,113,0.1)" stroke-width="1"/>
        <line x1="50" y1="120" x2="250" y2="120" stroke="rgba(46,204,113,0.1)" stroke-width="1"/>
        <path d="M150,120 L240,80" stroke="rgba(46,204,113,0.9)" stroke-width="1.5"/>
        <path d="M150,120 L240,80 A100,100 0 0,0 195,30 Z" fill="rgba(46,204,113,0.06)"/>
        <circle cx="186" cy="83" r="5" fill="rgba(231,76,60,0.9)"/>
        <circle cx="186" cy="83" r="9" fill="none" stroke="rgba(231,76,60,0.4)" stroke-width="1"/>
        <circle cx="117" cy="65" r="4" fill="rgba(46,204,113,0.8)"/>
        <circle cx="200" cy="155" r="4" fill="rgba(46,204,113,0.8)"/>
      </svg>
    </div>
    <div class="radar-bottom">
      <span class="rl">Targets</span>
      <span class="radar-anomalies">2 Anomalies</span>
    </div>
  </div>
</div>
<div class="section-divider"></div>
""", unsafe_allow_html=True)

# ── THE THREAT ──
st.markdown("""
<div class="ss-section" id="threat">
  <div class="section-label"><span class="section-label-line"></span> The Silent Epidemic</div>
  <div class="threat-header">
    <h2 class="threat-h2">The room is watching.<br><span class="dim">And it won't tell you.</span></h2>
    <p class="threat-desc">Covert surveillance has become a cheap, consumer-grade threat. Travelers don't need better paranoia — they need better tools.</p>
  </div>
  <div class="stat-cards">
    <div class="stat-card">
      <div class="stat-card-top"><span class="stat-card-icon">👁</span><span class="stat-card-num-label">01</span></div>
      <div class="stat-card-num">1 in 11</div>
      <div class="stat-card-title">Short-term rentals affected</div>
      <div class="stat-card-desc">Rentals audited in recent peer-reviewed studies contain hidden recording devices.</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-top"><span class="stat-card-icon">📵</span><span class="stat-card-num-label">02</span></div>
      <div class="stat-card-num">700M</div>
      <div class="stat-card-title">Annual hotel stays at risk</div>
      <div class="stat-card-desc">Global hotel room nights exposed to covert surveillance threats every year.</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-top"><span class="stat-card-icon">⚠</span><span class="stat-card-num-label">03</span></div>
      <div class="stat-card-num">92%</div>
      <div class="stat-card-title">Average victims never notice</div>
      <div class="stat-card-desc">Of covert cameras go undetected during a standard visual inspection.</div>
    </div>
  </div>
  <p class="threat-sources" style="margin-top:24px">Sources: IPX1031 Traveler Study · Harvard Business School · Jacobs School of Engineering</p>
</div>
<div class="section-divider"></div>
""", unsafe_allow_html=True)

# ── TECHNOLOGY ──
st.markdown("""
<div class="ss-section" id="technology">
  <div class="section-label green"><span class="section-label-line"></span> The Privacy Shield</div>
  <div class="tech-header">
    <h2 class="tech-h2">Four layers.<br><span class="green">Zero blind spots.</span></h2>
    <p class="tech-desc">Each layer runs on-device in parallel. No single surveillance technique — optical, wireless, or infrared — gets past all four.</p>
  </div>
  <div class="tech-grid">
    <div class="tech-card">
      <div class="tech-live-feed">
        <div class="live-badge" style="position:absolute;top:12px;left:12px;">LIVE FEED</div>
        <svg viewBox="0 0 580 160" width="100%" height="160" xmlns="http://www.w3.org/2000/svg" style="position:relative;z-index:2">
          <rect width="580" height="160" fill="transparent"/>
          <rect x="10" y="20" width="560" height="120" rx="4" fill="none" stroke="rgba(46,204,113,0.2)" stroke-width="1"/>
          <line x1="10" y1="80" x2="570" y2="80" stroke="rgba(46,204,113,0.1)" stroke-width="1"/>
          <rect x="240" y="55" width="100" height="50" rx="2" fill="none" stroke="rgba(231,76,60,0.5)" stroke-width="1.5"/>
          <circle cx="290" cy="80" r="8" fill="rgba(231,76,60,0.3)" stroke="#E74C3C" stroke-width="1.5"/>
          <text x="290" y="110" text-anchor="middle" fill="#E74C3C" font-size="9" font-family="JetBrains Mono">LENS DETECTED</text>
          <text x="290" y="122" text-anchor="middle" fill="#E74C3C" font-size="8" font-family="JetBrains Mono">CONF: 0.94</text>
        </svg>
      </div>
      <div class="tech-card-body">
        <div class="tech-card-top">
          <div style="display:flex;align-items:center;gap:10px">
            <span class="tech-card-icon-box">🔍</span>
            <span class="tech-card-layer">Layer · L01</span>
          </div>
          <span style="color:#6b7a96">↗</span>
        </div>
        <div class="tech-card-title">AI Optical Lens Detection</div>
        <p class="tech-card-desc">Edge-based YOLOv8 model identifies retro-reflective lens glints the human eye misses — running entirely on your device.</p>
        <div class="tech-card-tags">
          <span class="tech-tag">On-Device YOLOv8</span>
          <span class="tech-tag">Sub-2MM Lens Recognition</span>
          <span class="tech-tag">No Cloud Upload</span>
        </div>
      </div>
    </div>
    <div>
      <div class="tech-card" style="margin-bottom:18px">
        <div class="tech-card-body">
          <div class="tech-card-top">
            <div style="display:flex;align-items:center;gap:10px">
              <span class="tech-card-icon-box">📶</span>
              <span class="tech-card-layer">Layer · L02</span>
            </div>
          </div>
          <div class="tech-card-title">Network Security Scanner</div>
          <p class="tech-card-desc">Passively maps every device on the local Wi-Fi and flags suspicious MAC vendor signatures from known surveillance OEMs.</p>
          <div class="tech-card-tags">
            <span class="tech-tag">Vendor OUI Lookup</span>
            <span class="tech-tag">ARP + mDNS Sweep</span>
          </div>
        </div>
      </div>
      <div class="tech-card" style="margin-bottom:18px">
        <div class="tech-card-body">
          <div class="tech-card-top">
            <div style="display:flex;align-items:center;gap:10px">
              <span class="tech-card-icon-box">💡</span>
              <span class="tech-card-layer">Layer · L03</span>
            </div>
          </div>
          <div class="tech-card-title">Infrared Flash Finder</div>
          <p class="tech-card-desc">Activates your front camera's IR sensitivity to reveal hidden night-vision LEDs invisible to the naked eye.</p>
          <div class="tech-card-tags">
            <span class="tech-tag">850–940NM Band</span>
            <span class="tech-tag">Auto-Capture Evidence</span>
          </div>
        </div>
      </div>
      <div class="tech-card">
        <div class="tech-card-body">
          <div class="tech-card-top">
            <div style="display:flex;align-items:center;gap:10px">
              <span class="tech-card-icon-box">🔒</span>
              <span class="tech-card-layer">Layer · L04</span>
            </div>
          </div>
          <div class="tech-card-title">Evidence Vault</div>
          <p class="tech-card-desc">Every scan is sealed with a SHA-256 chain-of-custody hash and a timestamped, court-admissible report.</p>
          <div class="tech-card-tags">
            <span class="tech-tag">SHA-256 Tamper-Proof</span>
            <span class="tech-tag">Legal-Ready PDF Export</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="section-divider"></div>
""", unsafe_allow_html=True)

# ── SIMULATION ──
st.markdown("""
<div class="ss-section" id="simulation">
  <div class="section-label green"><span class="section-label-line"></span> 60-Second Scan · Live Simulation</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:60px;margin-bottom:50px;align-items:end">
    <h2 class="sim-h2" style="font-size:48px;font-weight:900;color:#e8edf5">Press start.<br><span style="color:#6b7a96">Watch it work.</span></h2>
    <p style="font-size:15px;color:#8892a4;line-height:1.75">A faithful UI preview of what a production scan looks like — three phases, one sealed evidence report.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# Simulation state
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False
if "sim_done" not in st.session_state:
    st.session_state.sim_done = False
if "session_num" not in st.session_state:
    st.session_state.session_num = random.randint(1000, 9999)

LOG_SCRIPT = [
    (0,    "— phase 1/3 · NETWORK CHECK —", "header"),
    (1,    "> scanning local Wi-Fi...", ""),
    (2,    "  arp sweep complete", ""),
    (3,    "  devices found: 7", ""),
    (4,    "  checking MAC vendor OUI database...", ""),
    (5,    "✓ 6 devices — known vendors", "green"),
    (6,    "✗ 1 device — vendor: unknown OEM (flagged)", "red"),
    (7,    "  mDNS probe: no hidden services", ""),
    (8,    "✓ phase 1 complete · 1 anomaly detected", "green"),
    (9,    "— phase 2/3 · AI LENS SCAN —", "header"),
    (10,   "> enabling rear camera · YOLOv8 loaded", ""),
    (11,   "  scanning frame 0001...", ""),
    (12,   "  scanning frame 0087...", ""),
    (13,   "  lens glint detected · confidence 0.94", "red"),
    (14,   "  triangulating position...", ""),
    (15,   "✗ lens glint detected · object 2 of 3", "red"),
    (16,   "  auto-capture evidence", ""),
    (17,   "✓ phase 2 complete · 2 anomalies detected", "green"),
    (18,   "— phase 3/3 · IR FREQUENCY SCAN —", "header"),
    (19,   "> enable front.cam ir_filter=off", ""),
    (20,   "  sweeping 850–940nm band...", ""),
    (21,   "  ambient IR: 3.2μW/cm² — nominal", ""),
    (22,   "✓ no active IR emitters detected", "green"),
    (23,   "— SCAN COMPLETE ——", "header"),
    (24,   "✓ session sealed · SHA-256 verified", "green"),
    (25,   "✓ report.pdf ready for authorities", "green"),
]

with st.container():
    st.markdown(f"""
    <div class="ss-section" style="padding-top:0;padding-bottom:20px">
    <div class="sim-terminal">
      <div class="sim-titlebar">
        <div style="display:flex;align-items:center;gap:16px">
          <div class="sim-dots">
            <span class="sim-dot-r"></span>
            <span class="sim-dot-y"></span>
            <span class="sim-dot-g"></span>
          </div>
          <span class="sim-session">SAFESTAY://SCAN · SESSION {st.session_state.session_num}</span>
        </div>
      </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
    with col_btn1:
        run_clicked = st.button("▷ RUN SCAN", key="run_btn")
    with col_btn2:
        reset_clicked = st.button("↺ RESET", key="reset_btn")

    if reset_clicked:
        st.session_state.sim_running = False
        st.session_state.sim_done = False
        st.session_state.session_num = random.randint(1000, 9999)
        st.rerun()

    # Phase indicators
    phase1_done = st.session_state.sim_done
    phase2_done = st.session_state.sim_done
    phase3_done = st.session_state.sim_done

    st.markdown(f"""
    <div style="max-width:1200px;margin:0 auto;padding:0 80px">
    <div class="sim-phases">
      <div class="sim-phase">
        <div class="sim-phase-left">
          <span class="sim-phase-icon">📶</span>
          <div>
            <div class="ph-label">Phase 1</div>
            <div class="ph-name">Network Check</div>
          </div>
        </div>
        <span class="sim-check {'done' if phase1_done else ''}">{'✓' if phase1_done else '◎'}</span>
      </div>
      <div class="sim-phase">
        <div class="sim-phase-left">
          <span class="sim-phase-icon">🔍</span>
          <div>
            <div class="ph-label">Phase 2</div>
            <div class="ph-name">AI Lens Scan</div>
          </div>
        </div>
        <span class="sim-check {'done' if phase2_done else ''}">{'✓' if phase2_done else '◎'}</span>
      </div>
      <div class="sim-phase">
        <div class="sim-phase-left">
          <span class="sim-phase-icon">💡</span>
          <div>
            <div class="ph-label">Phase 3</div>
            <div class="ph-name">IR Frequency Scan</div>
          </div>
        </div>
        <span class="sim-check {'done' if phase3_done else ''}">{'✓' if phase3_done else '◎'}</span>
      </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Progress bar
    progress_placeholder = st.empty()
    log_placeholder = st.empty()

    if not run_clicked and not st.session_state.sim_done:
        progress_placeholder.markdown("""
        <div style="max-width:1200px;margin:0 auto;padding:12px 80px 0">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#6b7a96">PROGRESS</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#2ECC71">0% · 60S Remaining</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
        log_placeholder.markdown("""
        <div style="max-width:1200px;margin:0 auto;padding:0 80px 20px">
          <div class="sim-log"><div class="log-dim">// Ready. Press RUN SCAN to start simulation.</div></div>
        </div>
        """, unsafe_allow_html=True)

    if run_clicked:
        st.session_state.sim_running = True
        st.session_state.session_num = random.randint(1000, 9999)
        log_lines = []

        for i, (step, text, cls) in enumerate(LOG_SCRIPT):
            pct = int((i + 1) / len(LOG_SCRIPT) * 100)
            remaining = max(0, 60 - int(i * 60 / len(LOG_SCRIPT)))

            log_lines.append((text, cls))
            log_html = ""
            for lt, lc in log_lines:
                color_class = {"green": "log-green", "red": "log-red", "header": "log-header", "": "log-dim"}.get(lc, "log-dim")
                log_html += f'<div class="{color_class}">{lt}</div>'

            progress_placeholder.markdown(f"""
            <div style="max-width:1200px;margin:0 auto;padding:12px 80px 0">
              <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span style="font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#6b7a96">PROGRESS</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#2ECC71">{pct}% · {remaining}S Remaining</span>
              </div>
              <div style="height:4px;background:rgba(255,255,255,0.07);border-radius:2px;overflow:hidden;margin-bottom:14px">
                <div style="height:100%;background:#2ECC71;border-radius:2px;width:{pct}%;transition:width 0.3s"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            log_placeholder.markdown(f"""
            <div style="max-width:1200px;margin:0 auto;padding:0 80px 20px">
              <div class="sim-log">{log_html}</div>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(0.55)

        st.session_state.sim_done = True
        st.session_state.sim_running = False
        st.rerun()

    if st.session_state.sim_done:
        all_log = "".join([
            f'<div class="{"log-green" if c=="green" else "log-red" if c=="red" else "log-header" if c=="header" else "log-dim"}">{t}</div>'
            for _, t, c in LOG_SCRIPT
        ])
        progress_placeholder.markdown("""
        <div style="max-width:1200px;margin:0 auto;padding:12px 80px 0">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#6b7a96">PROGRESS</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#2ECC71">100% · Complete</span>
          </div>
          <div style="height:4px;background:rgba(255,255,255,0.07);border-radius:2px;overflow:hidden;margin-bottom:14px">
            <div style="height:100%;background:#2ECC71;border-radius:2px;width:100%"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        log_placeholder.markdown(f"""
        <div style="max-width:1200px;margin:0 auto;padding:0 80px 20px">
          <div class="sim-log">{all_log}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ── PRIVACY / TRUST ──
st.markdown("""
<div class="ss-section" id="privacy">
  <div class="section-label green"><span class="section-label-line"></span> Trust Architecture</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:60px;margin-bottom:50px;align-items:end">
    <h2 style="font-size:48px;font-weight:900;line-height:1.1;color:#e8edf5">Your scan. Your device.<br><span style="color:#2ECC71">Nobody else's business.</span></h2>
    <p style="font-size:15px;color:#8892a4;line-height:1.75">SafeStay is engineered so that privacy isn't a policy — it's physically impossible for us to see your data.</p>
  </div>
  <div class="trust-cards">
    <div class="trust-card">
      <div class="trust-card-icon">🚫</div>
      <div class="trust-card-title">Zero-Cloud Privacy</div>
      <p class="trust-card-desc">All video, audio, and Wi-Fi analysis runs on-device. Nothing ever reaches our servers — because there are none for your scan data.</p>
    </div>
    <div class="trust-card">
      <div class="trust-card-icon">⚖</div>
      <div class="trust-card-title">Legal Ready</div>
      <p class="trust-card-desc">Evidence Vault reports are SHA-256 hashed and timestamped — admissible chain-of-custody for police and civil proceedings.</p>
    </div>
    <div class="trust-card">
      <div class="trust-card-icon">🖥</div>
      <div class="trust-card-title">On-Device AI</div>
      <p class="trust-card-desc">Neural inference runs locally via CoreML & TFLite. Scans work offline, in airplane mode, and in unfamiliar networks.</p>
    </div>
    <div class="trust-card">
      <div class="trust-card-icon">🔐</div>
      <div class="trust-card-title">End-to-End Sealed</div>
      <p class="trust-card-desc">Exports are encrypted with a key that never leaves your device. You decide who sees the report — and when.</p>
    </div>
  </div>
  <div class="cta-banner">
    <div>
      <div class="cta-banner-label">Early Access · Limited Beta</div>
      <div class="cta-banner-title">Be among the first 1,000 travelers to scan with SafeStay.</div>
    </div>
    <a href="#" class="btn-cta" style="font-size:15px;padding:16px 32px;flex-shrink:0">⊕ Claim My Spot</a>
  </div>
</div>

<div class="ss-footer">
  <div class="footer-l">
    <span>⊕ SafeStay</span>
    <span style="color:#1e2a3a">·</span>
    <span>A Gradient Forge Product</span>
  </div>
  <div class="footer-r">
    <span class="footer-badge">Beta</span>
    <span class="footer-online">All Systems Nominal</span>
  </div>
</div>
""", unsafe_allow_html=True)
