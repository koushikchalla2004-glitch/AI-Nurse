from typing import Dict, List, Any
import json
from PyPDF2 import PdfReader

def parse_discharge_summary(uploaded_file) -> Dict[str, Any]:
    """
    Very lightweight parser for demo purposes.
    - Supports TXT or text-based PDF
    - Extracts mentions of diagnoses and medications via simple heuristics
    """
    text = ""
    if uploaded_file.type.endswith("pdf"):
        try:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                txt = page.extract_text() or ""
                text += "\n" + txt
        except Exception:
            text = ""
    else:
        text = uploaded_file.read().decode("utf-8", errors="ignore")

    text_l = text.lower()

    diagnoses = []
    for key in ["heart failure", "copd", "pneumonia", "diabetes", "ckd", "hypertension", "asthma"]:
        if key in text_l:
            diagnoses.append(key)

    meds = []
    # naive medication line capture
    for line in text.splitlines():
        if any(tok in line.lower() for tok in ["mg", "mcg"]) and any(tok in line.lower() for tok in ["qd", "bid", "tid", "qid", "daily"]):
            meds.append({
                "name": line.strip().split()[0],
                "dose": " ".join([w for w in line.split() if any(x in w.lower() for x in ["mg","mcg"])]),
                "freq": "qd (daily)" if "daily" in line.lower() or "qd" in line.lower() else \
                        "bid (2x/day)" if "bid" in line.lower() else \
                        "tid (3x/day)" if "tid" in line.lower() else \
                        "qid (4x/day)" if "qid" in line.lower() else "qd (daily)",
                "start": None, "stop": None
            })

    parsed = {
        "raw_text_present": len(text) > 0,
        "diagnoses": diagnoses,
        "medications": meds,
        "length_of_stay_days": 4,  # placeholder
        "prior_admissions_1y": 1   # placeholder
    }
    return parsed
