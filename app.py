import time
import io
import json
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from utils.parsers import parse_discharge_summary
from utils.reminders import build_med_schedule, adherence_summary
from models.readmission_model import ReadmissionModel

st.set_page_config(page_title="AI Nurse Demo", layout="wide")

# --- Session State ---
if "patient" not in st.session_state:
    st.session_state.patient = {
        "name": "Demo Patient",
        "dob": "1960-01-01",
        "sex": "M",
        "caregivers": [],
        "consent_hospital_alerts": True,
        "timezone": "America/Chicago",
    }

if "discharge" not in st.session_state:
    st.session_state.discharge = {}

if "meds" not in st.session_state:
    st.session_state.meds = []

if "vitals" not in st.session_state:
    st.session_state.vitals = pd.DataFrame(columns=["ts", "hr", "spo2", "steps"])

if "risk_model" not in st.session_state:
    st.session_state.risk_model = ReadmissionModel()
    st.session_state.risk_model.train_synthetic(n=1500, seed=42)

if "risk_history" not in st.session_state:
    st.session_state.risk_history = []

if "alerts" not in st.session_state:
    st.session_state.alerts = []

st.title("🩺 AI Nurse — Post‑Discharge Prototype")

with st.sidebar:
    st.markdown("### Patient")
    st.write(st.session_state.patient)
    st.markdown("---")
    st.markdown("### Navigation")
    st.markdown("Use the tabs to try the demo workflow.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1) Upload Docs",
    "2) Meds & Reminders",
    "3) Wearable Monitor",
    "4) Risk & Explainability",
    "5) Alerts",
    "6) Daily Report",
])

# --- Tab 1: Upload Docs ---
with tab1:
    st.header("Upload Discharge Summary / Prescriptions")
    up = st.file_uploader("Upload a discharge summary (PDF or TXT)", type=["pdf", "txt"])
    if up is not None:
        parsed = parse_discharge_summary(up)
        st.session_state.discharge = parsed
        st.success("Parsed discharge summary!")
        st.json(parsed)

    st.subheader("Add Caregivers")
    cg_name = st.text_input("Caregiver name")
    cg_phone = st.text_input("Caregiver phone (for demo only)")
    cg_email = st.text_input("Caregiver email (for demo only)")
    if st.button("Add Caregiver"):
        if cg_name:
            st.session_state.patient["caregivers"].append({
                "name": cg_name, "phone": cg_phone, "email": cg_email
            })
            st.success(f"Added caregiver: {cg_name}")
    if st.session_state.patient["caregivers"]:
        st.write(pd.DataFrame(st.session_state.patient["caregivers"]))

# --- Tab 2: Meds & Reminders ---
with tab2:
    st.header("Medication List & Reminders")
    st.info("Enter meds manually or auto-import from parsed discharge meds if available.")
    colA, colB = st.columns(2)
    with colA:
        name = st.text_input("Medication name")
        dose = st.text_input("Dose, e.g., 5 mg")
        freq = st.selectbox("Frequency", ["qd (daily)", "bid (2x/day)", "tid (3x/day)", "qid (4x/day)"])
        start = st.date_input("Start date", pd.Timestamp.today())
        stop = st.date_input("Stop date (optional)", pd.Timestamp.today() + pd.Timedelta(days=14))
        if st.button("Add Medication"):
            st.session_state.meds.append({
                "name": name, "dose": dose, "freq": freq, "start": str(start), "stop": str(stop)
            })
            st.success(f"Added {name}")
    with colB:
        if st.button("Import from Discharge (demo)"):
            if st.session_state.discharge.get("medications"):
                st.session_state.meds.extend(st.session_state.discharge["medications"])
                st.success("Imported meds from parsed discharge.")
            else:
                st.warning("No meds found in parsed discharge.")
    if st.session_state.meds:
        st.write(pd.DataFrame(st.session_state.meds))

    st.subheader("Build Today's Reminder Schedule")
    if st.button("Generate Schedule for Today"):
        sched = build_med_schedule(st.session_state.meds, tz=st.session_state.patient["timezone"])
        st.session_state.today_schedule = sched
        st.write(pd.DataFrame(sched))

# --- Tab 3: Wearable Monitor ---
with tab3:
    st.header("Simulated Wearable Stream")
    st.caption("Click 'Start stream' to simulate vitals for ~30 seconds. Risk updates in the next tab.")

    col1, col2, col3 = st.columns(3)
    with col1:
        base_hr = st.number_input("Baseline HR", min_value=40, max_value=120, value=78)
    with col2:
        base_spo2 = st.number_input("Baseline SpO₂", min_value=80, max_value=100, value=95)
    with col3:
        activity = st.selectbox("Activity level", ["rest", "light", "walk"])

    if st.button("Start stream"):
        placeholder = st.empty()
        data = st.session_state.vitals.copy()
        for i in range(30):
            ts = pd.Timestamp.utcnow()
            hr_noise = np.random.normal(0, 2)
            if activity == "light":
                hr = base_hr + 5 + hr_noise
            elif activity == "walk":
                hr = base_hr + 15 + hr_noise
            else:
                hr = base_hr + hr_noise
            spo2 = base_spo2 + np.random.normal(0, 0.4)
            steps = max(0, int(np.random.normal(30 if activity!="rest" else 2, 5)))
            new = pd.DataFrame([{"ts": ts, "hr": hr, "spo2": spo2, "steps": steps}])
            data = pd.concat([data, new], ignore_index=True)
            st.session_state.vitals = data

            fig1 = px.line(data.tail(200), x="ts", y="hr", title="Heart Rate")
            fig2 = px.line(data.tail(200), x="ts", y="spo2", title="SpO₂")
            fig3 = px.bar(data.tail(50), x="ts", y="steps", title="Steps (interval)")
            placeholder.plotly_chart(fig1, use_container_width=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.plotly_chart(fig3, use_container_width=True)

            # simple alert logic
            alerts = []
            if spo2 < 88:
                alerts.append(("critical", f"Low SpO₂: {spo2:.1f}%"))
            if hr > 130 and activity == "rest":
                alerts.append(("critical", f"High resting HR: {hr:.0f} bpm"))
            for sev, msg in alerts:
                st.session_state.alerts.append({
                    "ts": str(ts), "severity": sev, "message": msg
                })
            time.sleep(1.0)
        st.success("Stream complete!")

# --- Tab 4: Risk & Explainability ---
with tab4:
    st.header("Readmission Risk")
    st.caption("Risk is computed from discharge features + latest wearable trends + meds complexity.")
    # Feature vector
    discharge = st.session_state.discharge
    meds_n = len(st.session_state.meds)
    vitals = st.session_state.vitals.tail(120)
    if vitals.empty:
        hr_rest = 80
        spo2_min = 94
        steps_sum = 2000
        sleep_eff = 0.85
    else:
        hr_rest = float(np.nanmedian(vitals["hr"]))
        spo2_min = float(np.nanmin(vitals["spo2"]))
        steps_sum = int(vitals["steps"].sum())
        sleep_eff = 0.85  # placeholder

    features = {
        "age": 65,
        "sex_male": 1 if st.session_state.patient["sex"] == "M" else 0,
        "dx_chf": 1 if "heart failure" in json.dumps(discharge).lower() else 0,
        "los_days": discharge.get("length_of_stay_days", 4),
        "prior_admits": discharge.get("prior_admissions_1y", 1),
        "meds_count": meds_n,
        "hr_rest": hr_rest,
        "spo2_min": spo2_min,
        "steps_sum": steps_sum,
        "sleep_eff": sleep_eff,
    }
    proba, shap_df = st.session_state.risk_model.predict_with_explain(features)
    band = "High" if proba >= 0.35 else ("Medium" if proba >= 0.18 else "Low")
    st.metric("Estimated 30‑day readmission risk", f"{proba*100:.1f}%", band)

    st.subheader("Top Factors (SHAP)")
    st.dataframe(shap_df.sort_values("abs_shap", ascending=False).head(8))

    st.session_state.risk_history.append({
        "ts": str(pd.Timestamp.utcnow()), "risk": float(proba), "band": band
    })
    hist = pd.DataFrame(st.session_state.risk_history)
    if not hist.empty:
        fig = px.line(hist, x="ts", y="risk", title="Risk over time")
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 5: Alerts ---
with tab5:
    st.header("Alerts & Escalation (Demo)")
    if st.session_state.alerts:
        df = pd.DataFrame(st.session_state.alerts)
        st.dataframe(df.sort_values("ts", ascending=False), use_container_width=True)
    else:
        st.info("No alerts yet. Generate some by running the wearable stream with low SpO₂.")

# --- Tab 6: Daily Report ---
with tab6:
    st.header("Daily Report (Prototype)")
    vit = st.session_state.vitals.tail(200)
    meds = st.session_state.meds
    risk = st.session_state.risk_history[-1]["risk"] if st.session_state.risk_history else np.nan
    rep = {
        "date": str(pd.Timestamp.now().date()),
        "patient": st.session_state.patient["name"],
        "risk": float(risk) if not np.isnan(risk) else None,
        "vitals_summary": {
            "hr_rest": float(np.nanmedian(vit["hr"])) if not vit.empty else None,
            "spo2_min": float(np.nanmin(vit["spo2"])) if not vit.empty else None,
            "steps_sum": int(vit["steps"].sum()) if not vit.empty else 0
        },
        "meds_count": len(meds),
        "alerts_24h": [a for a in st.session_state.alerts][-10:],
        "suggestions": [
            "Remember your evening dose if scheduled.",
            "Aim for 10–15 minutes of light walking today (if approved by your clinician).",
            "If you feel chest pain or severe breathlessness, seek urgent care."
        ]
    }
    st.json(rep)

    if st.button("Download JSON report"):
        b = io.BytesIO(json.dumps(rep, indent=2).encode())
        st.download_button("Save report.json", b, file_name=f"daily_report_{rep['date']}.json", mime="application/json")
