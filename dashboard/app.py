"""
Power Grid Monitoring System - Streamlit Dashboard
Real-time operator dashboard with live charts, alerts panel, and ML forecasting.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import os

# ─── Config ───────────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="⚡ Power Grid Monitoring – SA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@300;400;500;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Control Room dark background */
  .stApp { background: #050a14; }

  /* System status bar */
  .status-bar {
    background: #0a1520;
    border: 1px solid rgba(0,212,255,0.3);
    border-radius: 6px;
    padding: 0.6rem 1.2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.82rem;
    letter-spacing: 0.5px;
    margin-bottom: 1rem;
  }
  .status-ok   { color: #00e676; }
  .status-warn { color: #ffab40; }
  .status-crit { color: #ff5252; animation: blink 1s step-start infinite; }
  @keyframes blink { 50% { opacity: 0.4; } }

  /* Main title */
  .dashboard-title {
    font-size: 1.6rem; font-weight: 800; letter-spacing: 2px;
    color: #00d4ff;
    font-family: 'Share Tech Mono', monospace;
    text-transform: uppercase;
    margin-bottom: 0;
  }
  .dashboard-subtitle { color: #4a6080; font-size: 0.8rem; margin-bottom: 0.8rem; letter-spacing: 1px; }

  /* KPI Cards — dense control style */
  .kpi-card {
    background: #080f1e;
    border: 1px solid #1a2d45;
    border-top: 2px solid #00d4ff;
    border-radius: 4px; padding: 0.8rem 1rem;
  }
  .kpi-card.warn { border-top-color: #ffab40; }
  .kpi-card.crit { border-top-color: #ff5252; }
  .kpi-label { color: #4a6080; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.2px; }
  .kpi-value { font-size: 1.7rem; font-weight: 700; color: #e8eaf6; font-family: 'Share Tech Mono', monospace; margin: 0.15rem 0; }
  .kpi-sub   { font-size: 0.72rem; color: #4a6080; }
  .kpi-status { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.8px; margin-top: 0.3rem; }
  .kpi-ok    { color: #00e676 !important; }
  .kpi-warn  { color: #ffab40 !important; }
  .kpi-crit  { color: #ff5252 !important; }

  /* Section headers */
  .section-header {
    font-size: 0.78rem; font-weight: 700; color: #4a6080;
    border-left: 3px solid #00d4ff; padding-left: 0.6rem;
    margin: 1.2rem 0 0.5rem 0;
    text-transform: uppercase; letter-spacing: 1px;
    font-family: 'Share Tech Mono', monospace;
  }

  /* Decision panel */
  .decision-panel {
    background: #060d1a;
    border: 1px solid #1a2d45;
    border-left: 3px solid #7b61ff;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    font-size: 0.82rem;
  }
  .decision-title { color: #7b61ff; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 0.5rem; font-family: 'Share Tech Mono', monospace; }
  .decision-item { color: #a0b0c8; margin: 0.3rem 0; padding-left: 0.5rem; border-left: 1px solid #1a2d45; }

  /* Incident row */
  .incident-row {
    background: #080f1e;
    border: 1px solid #1a2d45;
    border-left: 3px solid #ff5252;
    border-radius: 3px; padding: 0.4rem 0.8rem;
    margin-bottom: 0.3rem;
    font-size: 0.82rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
  }
  .incident-warn { border-left-color: #ffab40; }

  /* Alert Badges */
  .badge-critical { background: rgba(255,82,82,0.15);  color: #ff5252; border: 1px solid rgba(255,82,82,0.5); border-radius: 3px; padding: 1px 7px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px; }
  .badge-high     { background: rgba(255,171,64,0.15); color: #ffab40; border: 1px solid rgba(255,171,64,0.5); border-radius: 3px; padding: 1px 7px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px; }
  .badge-medium   { background: rgba(255,238,88,0.12); color: #ffee58; border: 1px solid rgba(255,238,88,0.4); border-radius: 3px; padding: 1px 7px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px; }
  .badge-low      { background: rgba(0,230,118,0.10);  color: #00e676; border: 1px solid rgba(0,230,118,0.4); border-radius: 3px; padding: 1px 7px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #060d1a;
    border-right: 1px solid #0d1e30;
  }

  /* Hide Streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1rem; }

  /* Compact radio buttons in sidebar */
  .stRadio > div { gap: 0.2rem; }
  .stRadio label { font-size: 0.85rem !important; color: #8892a4 !important; }
</style>
""", unsafe_allow_html=True)


# ─── API Helpers ──────────────────────────────────────────────────────────────

def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None


def api_post(path: str, json: dict = None):
    try:
        r = requests.post(f"{API_BASE}{path}", json=json, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None


# ─── Colour helpers ───────────────────────────────────────────────────────────

def risk_color(risk: float) -> str:
    if risk >= 0.8: return "#ff5252"
    if risk >= 0.5: return "#ffab40"
    if risk >= 0.3: return "#ffee58"
    return "#00e676"


def load_color(pct: float) -> str:
    if pct >= 100: return "#ff5252"
    if pct >= 85:  return "#ffab40"
    if pct >= 70:  return "#ffee58"
    return "#00e676"


def severity_badge(sev: str) -> str:
    return f'<span class="badge-{sev}">{sev.upper()}</span>'


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div style="color:#00d4ff;font-size:1rem;font-weight:800;font-family:monospace;letter-spacing:2px">⚡ GRID MONITOR</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#4a6080;font-size:0.72rem;letter-spacing:1px;margin-bottom:0.5rem">SA NATIONAL GRID — LIVE OPS</div>', unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🖥️ Operations Dashboard", "🗺️ Grid Map", "📡 Grid Nodes", "🔮 Predictive Analysis", "🚨 Incident Management", "🔴 Load Shedding", "🖥️ IT Architecture"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    auto_refresh = st.toggle("🔁 Auto-refresh (30s)", value=False)
    if auto_refresh:
        time.sleep(0.5)
        st.rerun()

    st.markdown("---")
    st.markdown(f'<div style="color:#2a4060;font-size:0.7rem;font-family:monospace">⚡ ESKOM-STYLE GRID MONITOR<br>FastAPI + ML BACKEND<br>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)



# ─── Page: Operations Dashboard ─────────────────────────────────────────────

if page == "🖥️ Operations Dashboard":

    summary = api_get("/analytics/summary")
    if not summary:
        st.error("❌ SYSTEM OFFLINE — Cannot connect to API. Ensure backend is running on port 8000.")
        st.stop()

    # ─── Robust Data Aggregation (Manual Sum for Accuracy) ───
    subs_list = api_get("/substations/")
    if subs_list:
        aggr_rows = []
        for s in subs_list:
            sub = s["substation"]
            lr = s["latest_reading"]
            aggr_rows.append({
                "Load (MW)": lr["load_mw"] if lr else 0,
                "Capacity (MW)": sub["capacity_mw"],
            })
        df_aggr = pd.DataFrame(aggr_rows)
        total_load = df_aggr["Load (MW)"].sum()
        total_capacity = df_aggr["Capacity (MW)"].sum()
        load_pct = (total_load / total_capacity * 100) if total_capacity > 0 else 0
    else:
        # Fallback if raw list fails
        total_load = summary.get("total_load_mw", 0)
        total_capacity = summary.get("total_capacity_mw", 1)
        load_pct = summary.get("avg_load_percentage", 0)

    # 🚨 CRITICAL: Define k for template compatibility 🚨
    k = summary
    freq = summary.get("grid_frequency_avg", 50.0)
    risk_score = summary.get("overload_risk_score", 0.0)
    critical_count = summary.get("critical_alerts", 0)
    active_count = summary.get("active_alerts", 0)
    now_str = datetime.now().strftime("%H:%M:%S")

    # ── Determine System Status ──
    if risk_score >= 70 or critical_count >= 3:
        sys_status = "CRITICAL"; sys_class = "status-crit"
        alert_level = "CRITICAL — IMMEDIATE ACTION REQUIRED"; alert_class = "status-crit"
        load_status = "OVERLOAD RISK"
    elif risk_score >= 40 or load_pct >= 85:
        sys_status = "WARNING"; sys_class = "status-warn"
        alert_level = "ELEVATED"; alert_class = "status-warn"
        load_status = "HIGH DEMAND"
    else:
        sys_status = "STABLE"; sys_class = "status-ok"
        alert_level = "NORMAL"; alert_class = "status-ok"
        load_status = "NOMINAL"

    # ═══════════ SYSTEM STATUS BAR ═══════════
    st.markdown(f"""
    <div class="status-bar">
        <span>🖥️ <b>SOUTH AFRICAN NATIONAL GRID CONTROL CENTRE</b></span>
        <span>SYSTEM STATUS: <span class="{sys_class}">■ {sys_status}</span></span>
        <span>⚡ GRID LOAD: <span class="{sys_class}">{load_pct:.1f}% — {load_status}</span></span>
        <span>🚨 ALERT LEVEL: <span class="{alert_class}">{alert_level}</span></span>
        <span style="color:#2a4060">LAST SYNC: <span style="color:#4a6080">{now_str}</span></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="dashboard-title">⚡ NATIONAL GRID OPERATIONS</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">REAL-TIME MONITORING — SOUTH AFRICAN POWER GRID INFRASTRUCTURE</div>', unsafe_allow_html=True)

    # ═══════════ KPI CARDS ROW ═══════════
    load_cls = "crit" if load_pct >= 90 else ("warn" if load_pct >= 75 else "")
    freq_cls  = "crit" if abs(freq-50) > 0.25 else ("warn" if abs(freq-50) > 0.1 else "")
    risk_cls  = "crit" if risk_score >= 70 else ("warn" if risk_score >= 40 else "")
    alert_cls = "crit" if critical_count > 0 else ""

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">🔌 Grid Nodes</div>
          <div class="kpi-value">{k['total_substations']}</div>
          <div class="kpi-sub">{k['online_count']} ONLINE / {k['fault_count']} FAULT</div>
          <div class="kpi-status kpi-ok">● OPERATIONAL</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card {load_cls}">
          <div class="kpi-label">⚡ Total Grid Load</div>
          <div class="kpi-value kpi-{load_cls if load_cls else 'ok'}">{total_load:,.0f} MW</div>
          <div class="kpi-sub">OF {total_capacity:,.0f} MW CAPACITY</div>
          <div class="kpi-status kpi-{load_cls if load_cls else 'ok'}">● {load_status}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card {load_cls}">
          <div class="kpi-label">📊 Avg Load Factor</div>
          <div class="kpi-value kpi-{load_cls if load_cls else 'ok'}">{load_pct:.1f}%</div>
          <div class="kpi-sub">NATIONAL AVERAGE</div>
          <div class="kpi-status kpi-{load_cls if load_cls else 'ok'}">● {'EXCEEDS THRESHOLD' if load_pct >= 90 else 'WITHIN LIMITS'}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card {freq_cls}">
          <div class="kpi-label">〜 Grid Frequency</div>
          <div class="kpi-value kpi-{freq_cls if freq_cls else 'ok'}">{freq:.3f} Hz</div>
          <div class="kpi-sub">NOMINAL: 50.000 Hz</div>
          <div class="kpi-status kpi-{freq_cls if freq_cls else 'ok'}">● {'DEVIATION DETECTED' if freq_cls else 'STABLE'}</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="kpi-card {alert_cls}">
          <div class="kpi-label">🚨 Active Incidents</div>
          <div class="kpi-value kpi-{alert_cls if alert_cls else 'ok'}">{active_count}</div>
          <div class="kpi-sub">{critical_count} CRITICAL — {'ACTION REQUIRED' if critical_count > 0 else 'MONITORING'}</div>
          <div class="kpi-status kpi-{alert_cls if alert_cls else 'ok'}">● {'URGENT' if critical_count > 0 else 'MONITORED'}</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="kpi-card {risk_cls}">
          <div class="kpi-label">🔥 Overload Risk</div>
          <div class="kpi-value kpi-{risk_cls if risk_cls else 'ok'}">{risk_score:.1f}/100</div>
          <div class="kpi-sub">GRID STABILITY INDEX</div>
          <div class="kpi-status kpi-{risk_cls if risk_cls else 'ok'}">● {'DANGER ZONE' if risk_score >= 70 else 'SAFE ZONE'}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ═══════════ CRITICAL INCIDENT BANNER ═══════════
    if critical_count > 0:
        st.error(f"🚨 CRITICAL GRID INCIDENTS DETECTED — {critical_count} NODES REQUIRE IMMEDIATE OPERATOR INTERVENTION")

    # ═══════════ MAIN CONTENT — 3 COLUMN CONTROL ROOM LAYOUT ═══════════
    col_main, col_side = st.columns([3, 1])

    with col_main:
        # Load Curve
        st.markdown('<div class="section-header">📈 NATIONAL LOAD CURVE — LAST 24 HOURS</div>', unsafe_allow_html=True)
        curve = api_get("/analytics/load-curve", {"hours": 24})
        if curve:
            df_curve = pd.DataFrame(curve)
            df_curve["timestamp"] = pd.to_datetime(df_curve["timestamp"])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_curve["timestamp"], y=df_curve["total_load_mw"],
                name="Total Load (MW)", line=dict(color="#00d4ff", width=2),
                fill="tozeroy", fillcolor="rgba(0,212,255,0.06)"
            ))
            fig.add_trace(go.Scatter(
                x=df_curve["timestamp"], y=df_curve["avg_load_pct"],
                name="Avg Load %", line=dict(color="#7b61ff", width=1.5, dash="dot"), yaxis="y2"
            ))
            fig.add_hline(y=df_curve["total_load_mw"].quantile(0.92),
                          line_dash="dot", line_color="#ff5252", opacity=0.4,
                          annotation_text="HIGH LOAD THRESHOLD")
            fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=260,
                margin=dict(l=0, r=0, t=5, b=0),
                legend=dict(orientation="h", y=1.05, font=dict(size=10)),
                yaxis=dict(title="MW", gridcolor="rgba(255,255,255,0.04)", titlefont=dict(size=10)),
                yaxis2=dict(title="%", overlaying="y", side="right", gridcolor="rgba(255,255,255,0.02)", titlefont=dict(size=10)),
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)"),
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Province Heat + Peak Hours side by side ──
        pc1, pc2 = st.columns(2)
        with pc1:
            st.markdown('<div class="section-header">🔮 PROVINCE LOAD DISTRIBUTION</div>', unsafe_allow_html=True)
            heatmap = api_get("/analytics/province-heatmap")
            if heatmap:
                provinces = list(heatmap.keys())
                load_vals = [heatmap[p]["avg_load_pct"] for p in provinces]
                colors_h = [load_color(v) for v in load_vals]
                fig_h = go.Figure(go.Bar(x=load_vals, y=provinces, orientation="h",
                    marker=dict(color=colors_h, opacity=0.9),
                    text=[f"{v:.1f}%" for v in load_vals], textposition="inside",
                ))
                fig_h.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", height=220, margin=dict(l=0, r=0, t=5, b=0),
                    xaxis=dict(title="Load %", range=[0, 120], gridcolor="rgba(255,255,255,0.04)", titlefont=dict(size=10)),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.02)", tickfont=dict(size=9)),
                )
                fig_h.add_vline(x=90, line_dash="dot", line_color="#ff5252", opacity=0.5)
                st.plotly_chart(fig_h, use_container_width=True)

        with pc2:
            st.markdown('<div class="section-header">📊 PEAK HOURS DETECTION</div>', unsafe_allow_html=True)
            if curve:
                df_peak = pd.DataFrame(curve)
                df_peak["hour"] = pd.to_datetime(df_peak["timestamp"]).dt.hour
                df_peak["demand"] = df_peak["total_load_mw"]
                peak_hours = df_peak.groupby("hour")["demand"].mean().reset_index()
                fig_peak = px.bar(peak_hours, x="hour", y="demand",
                    labels={"hour": "Hour", "demand": "Avg MW"},
                    color="demand", color_continuous_scale="OrRd"
                )
                fig_peak.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", height=220, margin=dict(l=0, r=0, t=5, b=0),
                    coloraxis_showscale=False,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.03)", titlefont=dict(size=10)),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", titlefont=dict(size=10)),
                )
                st.plotly_chart(fig_peak, use_container_width=True)

        # ── Future Grid Risk ──
        st.markdown('<div class="section-header">🔮 PREDICTIVE ANALYSIS — NEXT 3 HOURS</div>', unsafe_allow_html=True)
        forecast_data = api_get("/forecast")
        if forecast_data:
            if "error" in forecast_data:
                st.warning(f"⚠️ FORECAST UNAVAILABLE — {forecast_data['error']}. Run the training script.")
            elif forecast_data.get("predictions"):
                df_future = pd.DataFrame({
                    "Hour": forecast_data["future_hours"],
                    "Predicted Demand (MW)": forecast_data["predictions"]
                })
                df_future["Hour Label"] = df_future["Hour"].apply(lambda x: f"{x:02d}:00")
                fig_future = px.line(df_future, x="Hour Label", y="Predicted Demand (MW)", markers=True)
                fig_future.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", height=180, margin=dict(l=0, r=0, t=5, b=0),
                )
                fig_future.update_traces(line=dict(color="#00d4ff", width=2.5), marker=dict(size=8, color="#ff5252"))
                st.plotly_chart(fig_future, use_container_width=True)
                if "mae" in forecast_data:
                    st.caption(f"📡 MODEL MAE: {forecast_data['mae']:.1f} MW | 🔄 Retrained periodically | {forecast_data.get('note','')}")

                fc_cols = st.columns(len(forecast_data["risk_levels"]))
                for i, (col, risk_lv) in enumerate(zip(fc_cols, forecast_data["risk_levels"])):
                    hour_lbl = df_future.iloc[i]["Hour Label"]
                    color = {"CRITICAL": "#ff5252", "HIGH": "#ffab40", "MEDIUM": "#ffee58"}.get(risk_lv, "#00e676")
                    with col:
                        st.markdown(f'<div style="background:#080f1e;border:1px solid #1a2d45;border-top:2px solid {color};border-radius:4px;padding:0.4rem 0.6rem;text-align:center"><div style="color:#4a6080;font-size:0.65rem;font-weight:700">{hour_lbl}</div><div style="color:{color};font-size:0.85rem;font-weight:700">{risk_lv}</div></div>', unsafe_allow_html=True)

        # ── Incident Ticker ──
        st.markdown('<div class="section-header">🚨 ACTIVE INCIDENTS — LATEST 8</div>', unsafe_allow_html=True)
        active_alerts = api_get("/alerts/active")
        if active_alerts:
            for a in active_alerts[:8]:
                sev = a["severity"]
                border = "#ff5252" if sev == "critical" else "#ffab40" if sev == "high" else "#ffee58"
                ts = a["created_at"][:19].replace("T", " ")
                st.markdown(f"""
                <div style="background:#080f1e;border:1px solid #1a2d45;border-left:3px solid {border};border-radius:3px;
                            padding:0.35rem 0.7rem;margin-bottom:0.25rem;display:flex;align-items:center;gap:0.8rem;font-size:0.8rem;">
                    <span class="badge-{sev}">{sev.upper()}</span>
                    <span style="color:#a0b0c8;flex:1">{a['message']}</span>
                    <span style="color:#2a4060;font-size:0.72rem;font-family:monospace">{ts}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#00e676;font-size:0.82rem;padding:0.5rem">✅ NO ACTIVE INCIDENTS</div>', unsafe_allow_html=True)

    with col_side:
        # ── System Risk Indicator ──
        st.markdown('<div class="section-header">🧠 SYSTEM RECOMMENDATION</div>', unsafe_allow_html=True)

        # Dynamic risk logic based on active critical alerts
        if summary.get("critical_alerts", 0) > 0:
            current_risk_display = "CRITICAL"
        elif summary.get("active_alerts", 0) > 3 or load_pct > 85:
            current_risk_display = "HIGH"
        elif summary.get("active_alerts", 0) > 0 or load_pct > 70:
            current_risk_display = "MEDIUM"
        else:
            current_risk_display = "LOW"

        # FALLBACK: Also check seeded Assignment Alerts for assignment compliance
        assignment_alerts = api_get("/alerts")
        if assignment_alerts and isinstance(assignment_alerts, list) and len(assignment_alerts) > 0:
            # If the assignment-specific logic detects high risk, prioritize it 
            seeded_risk = assignment_alerts[-1].get("risk_level", "LOW")
            if seeded_risk in ["CRITICAL", "HIGH"] and current_risk_display not in ["CRITICAL", "HIGH"]:
                current_risk_display = seeded_risk

        current_risk = current_risk_display # Normalize variable name
        rec_color = {"CRITICAL": "#ff5252", "HIGH": "#ffab40", "MEDIUM": "#ffee58"}.get(current_risk, "#00e676")

        if current_risk == "CRITICAL":
            recs = ["Activate backup generation", "Initiate load shedding Stage 3+", "Alert all provinces", "Contact Emergency Response"]
        elif current_risk == "HIGH":
            recs = ["Reduce industrial load by 10%", "Monitor KZN demand spike", "Standby backup units", "Alert NOC operators"]
        elif current_risk == "MEDIUM":
            recs = ["Watch Gauteng load growth", "Increase hydro output", "Monitor overnight demand", "Standard protocols active"]
        else:
            recs = ["System operating normally", "Continue monitoring", "Next forecast in 1 hour", "No action required"]

        st.markdown(f"""
        <div class="decision-panel">
            <div class="decision-title">🧠 AI DECISION SUPPORT</div>
            <div style="color:{rec_color};font-size:0.75rem;font-weight:700;margin-bottom:0.5rem">RISK LEVEL: {current_risk}</div>
            {''.join([f'<div class="decision-item">▶ {r}</div>' for r in recs])}
        </div>""", unsafe_allow_html=True)

        # ── Province heatmap mini ──
        st.markdown('<div class="section-header" style="margin-top:1rem">📡 NODE STATUS</div>', unsafe_allow_html=True)
        heatmap = api_get("/analytics/province-heatmap")
        if heatmap:
            for province, data in list(heatmap.items())[:6]:
                pct = data.get("avg_load_pct", 0)
                color = load_color(pct)
                bar_width = min(int(pct), 100)
                st.markdown(f"""
                <div style="margin-bottom:0.4rem">
                    <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#4a6080;margin-bottom:2px">
                        <span>{province[:12]}</span><span style="color:{color}">{pct:.0f}%</span>
                    </div>
                    <div style="background:#0d1e30;border-radius:2px;height:4px">
                        <div style="background:{color};width:{bar_width}%;height:4px;border-radius:2px"></div>
                    </div>
                </div>""", unsafe_allow_html=True)

        # ── Forecast mini risk panel ──
        st.markdown('<div class="section-header" style="margin-top:1rem">⏱️ FUTURE RISK</div>', unsafe_allow_html=True)
        if forecast_data and forecast_data.get("risk_levels"):
            for i, r in enumerate(forecast_data["risk_levels"]):
                h = forecast_data["future_hours"][i]
                c = {"CRITICAL": "#ff5252", "HIGH": "#ffab40", "MEDIUM": "#ffee58"}.get(r, "#00e676")
                st.markdown(f'<div style="background:#080f1e;border:1px solid #1a2d45;border-left:2px solid {c};border-radius:3px;padding:0.3rem 0.6rem;margin-bottom:0.25rem;font-size:0.78rem;display:flex;justify-content:space-between"><span style="color:#4a6080">{h:02d}:00</span><span style="color:{c};font-weight:700">{r}</span></div>', unsafe_allow_html=True)

        # ── Last Updated ──
        st.markdown(f'<div style="margin-top:1rem;color:#2a4060;font-size:0.7rem;font-family:monospace;border-top:1px solid #0d1e30;padding-top:0.5rem">LAST UPDATED<br><span style="color:#4a6080">{now_str}</span></div>', unsafe_allow_html=True)

    # ── Assignment Risk Indicator ──
    st.markdown('<div class="section-header">🚦 GRID RISK STATUS</div>', unsafe_allow_html=True)
    if current_risk == "CRITICAL":
        st.error("🚨 CRITICAL OVERLOAD RISK — GRID STABILITY THREATENED. EXECUTE EMERGENCY PROTOCOLS.")
    elif current_risk == "HIGH":
        st.warning("⚡ HIGH DEMAND ALERT — OPERATOR ACTION RECOMMENDED. MONITOR ALL NODES.")
    elif current_risk == "MEDIUM":
        st.info("ℹ️ MEDIUM LOAD DETECTED — ELEVATED MONITORING ACTIVE. SYSTEM STABLE.")
    else:
        st.success("✅ GRID STABLE — ALL SYSTEMS NOMINAL. LOAD WITHIN SAFE PARAMETERS.")

    # ── Auto-resolve active alerts button ──
    active_alerts = api_get("/alerts/active")
    if active_alerts:
        if st.button("⚠️ RESOLVE ALL ACTIVE INCIDENTS", type="primary"):
            api_post("/alerts/resolve-all")
            st.success("All active incidents resolved.")
            st.rerun()



# ─── Page: Grid Map ───────────────────────────────────────────────────────────

elif page == "🗺️ Grid Map":
    st.markdown('<div class="dashboard-title">🗺️ Grid Infrastructure Map</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">Substation locations with real-time load colour coding</div>', unsafe_allow_html=True)

    subs = api_get("/substations/")
    if subs:
        rows = []
        for s in subs:
            sub = s["substation"]
            lr = s["latest_reading"]
            rows.append({
                "name": sub["name"],
                "province": sub["province"],
                "region": sub["region"],
                "lat": sub["latitude"],
                "lon": sub["longitude"],
                "capacity_mw": sub["capacity_mw"],
                "status": sub["status"],
                "load_pct": lr["load_percentage"] if lr else 0,
                "load_mw": lr["load_mw"] if lr else 0,
                "frequency_hz": lr["frequency_hz"] if lr else 50.0,
                "overload_risk": s["overload_risk"] or 0,
                "active_alerts": s["active_alerts"],
            })
        df_map = pd.DataFrame(rows)

        fig_map = px.scatter_mapbox(
            df_map, lat="lat", lon="lon",
            color="load_pct",
            size="capacity_mw",
            size_max=35,
            color_continuous_scale=["#00e676", "#ffee58", "#ffab40", "#ff5252"],
            range_color=[0, 110],
            hover_name="name",
            hover_data={
                "province": True, "load_pct": ":.1f", "load_mw": ":.0f",
                "capacity_mw": ":.0f", "frequency_hz": ":.3f", "status": True,
                "active_alerts": True, "lat": False, "lon": False,
            },
            mapbox_style="carto-darkmatter",
            zoom=4.5, center={"lat": -29.0, "lon": 25.0},
            height=600,
        )
        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="Load %", ticksuffix="%"),
        )
        st.plotly_chart(fig_map, use_container_width=True)

        st.markdown('<div class="section-header">📋 Substation Status Table</div>', unsafe_allow_html=True)
        df_display = df_map[["name", "province", "status", "capacity_mw", "load_mw", "load_pct", "frequency_hz", "active_alerts"]].copy()
        df_display.columns = ["Name", "Province", "Status", "Capacity (MW)", "Load (MW)", "Load %", "Freq (Hz)", "Alerts"]
        try:
            st.dataframe(df_display.style.background_gradient(subset=["Load %"], cmap="YlOrRd"), use_container_width=True)
        except Exception:
            st.dataframe(df_display, use_container_width=True)



# ─── Page: Grid Nodes ──────────────────────────────────────────────────────────

elif page == "📡 Grid Nodes":
    st.markdown('<div class="dashboard-title">📊 Substation Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">Drill into per-substation telemetry and historical data</div>', unsafe_allow_html=True)

    subs = api_get("/substations/")
    if not subs:
        st.error("No substation data available")
        st.stop()

    sub_names = [s["substation"]["name"] for s in subs]
    sub_ids   = {s["substation"]["name"]: s["substation"]["id"] for s in subs}

    selected_name = st.selectbox("Select Substation", sub_names)
    selected_id   = sub_ids[selected_name]
    hours_range   = st.slider("History (hours)", 6, 72, 24)

    readings = api_get(f"/substations/{selected_id}/readings", {"hours": hours_range})
    if not readings:
        st.warning("No readings found for selected substation / time range.")
        st.stop()

    df_r = pd.DataFrame(readings)
    df_r["timestamp"] = pd.to_datetime(df_r["timestamp"])

    # Mini KPIs
    latest = df_r.iloc[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val, unit in [
        (c1, "Load", latest["load_percentage"], "%"),
        (c2, "MW",   latest["load_mw"], " MW"),
        (c3, "Freq", latest["frequency_hz"], " Hz"),
        (c4, "PF",   latest["power_factor"], ""),
        (c5, "°C",   latest.get("temperature_celsius", "—"), "°C"),
    ]:
        cls = load_color(float(val)) if label == "Load" else "#c8d0e0"
        with col:
            st.markdown(f"""<div class="kpi-card">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value" style="color:{cls};font-size:1.6rem">{val}{unit}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")

    tab1, tab2, tab3 = st.tabs(["📈 Load Profile", "⚡ Electrical", "🌡️ Environmental"])

    with tab1:
        fig = go.Figure()
        cap = next(s["substation"]["capacity_mw"] for s in subs if s["substation"]["id"] == selected_id)
        cap_line = [cap] * len(df_r)
        fig.add_trace(go.Scatter(x=df_r["timestamp"], y=df_r["load_mw"], name="Load (MW)",
                                  line=dict(color="#00d4ff", width=2.5),
                                  fill="tozeroy", fillcolor="rgba(0,212,255,0.07)"))
        fig.add_trace(go.Scatter(x=df_r["timestamp"], y=cap_line, name="Capacity",
                                  line=dict(color="#ff5252", width=1.5, dash="dash")))
        fig.add_trace(go.Scatter(x=df_r["timestamp"], y=df_r["load_percentage"], name="Load %",
                                  line=dict(color="#7b61ff", width=1.5, dash="dot"), yaxis="y2"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", height=380,
                           yaxis=dict(title="MW", gridcolor="rgba(255,255,255,0.06)"),
                           yaxis2=dict(title="%", overlaying="y", side="right"),
                           legend=dict(orientation="h", y=1.05), margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2, fig3 = go.Figure(), go.Figure()
        fig2.add_trace(go.Scatter(x=df_r["timestamp"], y=df_r["frequency_hz"], name="Frequency (Hz)",
                                   line=dict(color="#ffab40", width=2)))
        fig2.add_hline(y=50.0, line_dash="dot", line_color="#ffffff", opacity=0.3, annotation_text="50 Hz")
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)", height=220,
                            yaxis=dict(gridcolor="rgba(255,255,255,0.06)"), margin=dict(l=0,r=0,t=10,b=0))

        fig3.add_trace(go.Scatter(x=df_r["timestamp"], y=df_r["power_factor"], name="Power Factor",
                                   line=dict(color="#7b61ff", width=2)))
        fig3.add_hline(y=0.90, line_dash="dot", line_color="#ffee58", opacity=0.5, annotation_text="Min 0.90")
        fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)", height=220,
                            yaxis=dict(gridcolor="rgba(255,255,255,0.06)"), margin=dict(l=0,r=0,t=10,b=0))

        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        if "temperature_celsius" in df_r.columns:
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=df_r["timestamp"], y=df_r["temperature_celsius"], name="Temp (°C)",
                                       line=dict(color="#ff6b6b", width=2), fill="tozeroy",
                                       fillcolor="rgba(255,107,107,0.07)"))
            if "humidity_percent" in df_r.columns:
                fig4.add_trace(go.Scatter(x=df_r["timestamp"], y=df_r["humidity_percent"], name="Humidity (%)",
                                           line=dict(color="#00d4ff", width=2), yaxis="y2"))
            fig4.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)", height=320,
                                yaxis=dict(title="°C", gridcolor="rgba(255,255,255,0.06)"),
                                yaxis2=dict(title="%", overlaying="y", side="right"),
                                margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig4, use_container_width=True)


# ─── Page: Predictive Analysis ────────────────────────────────────────────────

elif page == "🔮 Predictive Analysis":
    st.markdown('<div class="dashboard-title">🔮 Predictive Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">GBM-powered 6–24 hour ahead load & overload risk predictions</div>', unsafe_allow_html=True)

    subs = api_get("/substations/")
    if not subs:
        st.error("API unavailable")
        st.stop()

    sub_names = [s["substation"]["name"] for s in subs]
    sub_ids   = {s["substation"]["name"]: s["substation"]["id"] for s in subs}
    caps      = {s["substation"]["id"]: s["substation"]["capacity_mw"] for s in subs}

    col_form1, col_form2 = st.columns([2, 1])
    with col_form1:
        selected_name = st.selectbox("Select Substation", sub_names, key="fc_sub")
    with col_form2:
        hours_ahead = st.selectbox("Forecast Horizon", [6, 12, 24], index=0)

    selected_id = sub_ids[selected_name]

    if st.button("🔮 Run Substation ML Forecast", type="primary"):
        with st.spinner(f"Running persistent model forecast for {selected_name}..."):
            # URL encoding for names with spaces (e.g. Athena Substation)
            from urllib.parse import quote
            forecasts = api_get(f"/forecast/substation/{quote(selected_name)}")

        if forecasts and "predictions" in forecasts:
            df_fc = pd.DataFrame({
                "Time": pd.to_datetime(forecasts["forecast_times"]),
                "Predicted Load (MW)": forecasts["predictions"]
            })
            
            # Risk calculation for specific node
            cap = forecasts["capacity_mw"]
            df_fc["Load %"] = (df_fc["Predicted Load (MW)"] / cap * 100)
            
            max_load = df_fc["Load %"].max()
            risk_cls = ("🔴 CRITICAL" if max_load > 100 else
                        "🟠 HIGH" if max_load > 90 else
                        "🟡 MEDIUM" if max_load > 75 else "🟢 LOW")

            st.info(f"**Peak Predicted Load for {selected_name}: {max_load:.1f}% ({risk_cls})**")

            # Forecast chart
            fig_fc = go.Figure()
            fig_fc.add_trace(go.Scatter(
                x=df_fc["Time"], y=df_fc["Load %"],
                name="Predicted Load %", line=dict(color="#00d4ff", width=3),
                fill="tozeroy", fillcolor="rgba(0,212,255,0.1)"
            ))
            fig_fc.add_hline(y=100, line_dash="dash", line_color="#ff5252", annotation_text="CAPACITY", opacity=0.7)
            fig_fc.add_hline(y=90, line_dash="dot", line_color="#ffab40", annotation_text="WARN", opacity=0.5)
            
            fig_fc.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)", height=400,
                                  yaxis=dict(title="Load %", gridcolor="rgba(255,255,255,0.06)", range=[0, max(110, max_load+10)]),
                                  margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_fc, use_container_width=True)

            # Data table
            st.dataframe(
                df_fc.rename(columns={"Predicted Load (MW)": "Predicted MW"}),
                use_container_width=True
            )
        else:
            st.error("Forecast failed. Ensure the model is trained and API is active.")


# ─── Page: Incident Management ───────────────────────────────────────────

elif page == "🚨 Incident Management":
    st.markdown('<div class="dashboard-title">🚨 Operations Incident Room</div>', unsafe_allow_html=True)

    summary = api_get("/alerts/summary")
    if summary:
        col1, col2, col3, col4, col5 = st.columns(5)
        for col, sev, emoji in [
            (col1, "total",    "📋"),
            (col2, "critical", "🔴"),
            (col3, "high",     "🟠"),
            (col4, "medium",   "🟡"),
            (col5, "low",      "🟢"),
        ]:
            with col:
                st.metric(f"{emoji} {sev.title()}", summary.get(sev, 0))

    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        sev_filter = st.selectbox("Severity", ["All", "critical", "high", "medium", "low"])
    with col_f2:
        res_filter = st.selectbox("Status", ["Active", "Resolved", "All"])
    with col_f3:
        if st.button("🧹 Resolve ALL Active Alerts", type="secondary"):
            api_post("/alerts/resolve-all")
            st.success("All active alerts resolved")
            st.rerun()

    params = {}
    if sev_filter != "All": params["severity"] = sev_filter
    if res_filter == "Active": params["is_resolved"] = "false"
    elif res_filter == "Resolved": params["is_resolved"] = "true"

    alerts = api_get("/alerts/", params)
    if alerts:
        for a in alerts[:100]:
            with st.expander(
                f"{severity_badge(a['severity'])} | {a['alert_type']} — {a['message'][:70]}...",
                expanded=False
            ):
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Substation ID:** {a['substation_id']}")
                c1.write(f"**Type:** {a['alert_type']}")
                c2.write(f"**Metric:** {a['metric_value']} (threshold: {a['threshold_value']})")
                c2.write(f"**Created:** {a['created_at'][:19].replace('T',' ')}")
                c3.write(f"**Resolved:** {'✅ Yes' if a['is_resolved'] else '❌ No'}")
                if not a["is_resolved"]:
                    if st.button(f"✅ Resolve Alert #{a['id']}", key=f"res2_{a['id']}"):
                        api_post(f"/alerts/{a['id']}/resolve", {"resolved_by": "Operator"})
                        st.rerun()


# ─── Page: Load Shedding ──────────────────────────────────────────────────────

elif page == "🔴 Load Shedding":
    st.markdown('<div class="dashboard-title">🔴 Load Shedding Events</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">Historical and current load shedding stages by region</div>', unsafe_allow_html=True)

    events = api_get("/analytics/load-shedding")
    if not events:
        st.info("No load shedding events recorded.")
        st.stop()

    df_ls = pd.DataFrame(events)
    df_ls["started_at"] = pd.to_datetime(df_ls["started_at"])
    df_ls["ended_at"]   = pd.to_datetime(df_ls["ended_at"])
    df_ls["is_active"]  = df_ls["ended_at"].isna()

    active = df_ls[df_ls["is_active"]]
    if not active.empty:
        for _, row in active.iterrows():
            st.error(f"🔴 **STAGE {int(row['stage'])} LOAD SHEDDING ACTIVE** — {row['region']} | Since: {str(row['started_at'])[:16]} | Reason: {row['reason']}")

    # Stage timeline
    fig_ls = go.Figure()
    colors_ls = {1:"#4caf50",2:"#8bc34a",3:"#ffeb3b",4:"#ff9800",5:"#ff5722",6:"#f44336",7:"#b71c1c",8:"#880e4f"}
    for _, row in df_ls.iterrows():
        end = row["ended_at"] if pd.notna(row["ended_at"]) else datetime.utcnow()
        fig_ls.add_trace(go.Bar(
            x=[row["duration_hours"] or 2],
            y=[row["region"]],
            orientation="h",
            marker_color=colors_ls.get(int(row["stage"]), "#888"),
            name=f"Stage {int(row['stage'])}",
            hovertemplate=f"<b>{row['region']}</b><br>Stage {int(row['stage'])}<br>Duration: {row['duration_hours']}h<br>Affected: {row['affected_mw']} MW<extra></extra>",
            showlegend=False,
        ))
    fig_ls.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", height=350,
                          xaxis=dict(title="Duration (hours)", gridcolor="rgba(255,255,255,0.06)"),
                          margin=dict(l=0, r=0, t=10, b=0), barmode="group")
    st.plotly_chart(fig_ls, use_container_width=True)

    # Stage legend
    col_leg = st.columns(8)
    for i, (stage, col_) in enumerate(zip(range(1, 9), col_leg)):
        col_.markdown(
            f'<div style="background:{colors_ls[stage]};border-radius:6px;padding:4px 6px;text-align:center;font-size:0.78rem;color:#000;font-weight:700">Stage {stage}</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="section-header">📋 Event Log</div>', unsafe_allow_html=True)
    df_display = df_ls[["stage", "region", "started_at", "ended_at", "duration_hours", "affected_mw", "reason"]].copy()
    df_display.columns = ["Stage", "Region", "Started", "Ended", "Duration (h)", "Affected MW", "Reason"]
    st.dataframe(df_display, use_container_width=True)


# ─── Page: IT Architecture ────────────────────────────────────────────────────

elif page == "🖥️ IT Architecture":
    st.markdown('<div class="dashboard-title">🖥️ Enterprise IT Architecture</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subtitle">Mapping the 5 pillars of Information Technology within the Grid Monitor</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    pillars = [
        ("👥 People", "Operators, Engineers, NOC Managers", "Role-based views, recommendation engine, incident resolution workflows."),
        ("📊 Data", "Telemetry, Alerts, ML Models", "PostgreSQL persistence, validated JSON schemas, Pydantic data integrity."),
        ("🌐 Network", "Distributed Grid Nodes", "FastAPI REST communication, CORS security, real-time telemetry polling."),
        ("🛡️ Security", "Validation & Reliability", "Input scrubbing, error fallback modes, logging, data-layer isolation."),
        ("💾 HW/SW", "Host & Environment", "Optimized Python backend, Scikit-learn ML core, Streamlit UI engine, scalable DB.")
    ]
    for col, (title, hardware, desc) in zip(cols, pillars):
        with col:
            st.markdown(f"""
            <div style="background:#080f1e;border:1px solid #1a2d45;border-radius:6px;padding:1rem;height:240px">
                <div style="color:#00d4ff;font-weight:700;margin-bottom:0.5rem">{title}</div>
                <div style="color:#ffee58;font-size:0.75rem;font-weight:600;margin-bottom:0.5rem">CORE: {hardware}</div>
                <div style="color:#8892a4;font-size:0.8rem">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.code("""
# System Integration Overview (Enterprise standards)
Frontend  <-- [REST API] --> Backend [FastAPI]
                            |
                            +--> [Database] PostgreSQL
                            +--> [AI/ML] Scikit-learn model.pkl
                            +--> [Logs] Loguru / Standard Output
    """)
