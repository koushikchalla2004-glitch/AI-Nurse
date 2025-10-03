# AI Nurse Demo (Student Prototype)

A Streamlit-based prototype that:
- Uploads a discharge summary (PDF/TXT) and extracts basic fields (diagnoses, meds).
- Trains a simple 30-day readmission risk model on synthetic data.
- Simulates wearable vitals (HR, SpO2, steps) and updates risk in real time.
- Sends mock reminders/alerts (in-app) and generates a daily report summary.

## Quickstart

```bash
# 1) Create & activate a virtual environment (Linux/Mac)
python3 -m venv .venv
source .venv/bin/activate
# (Windows)
# py -m venv .venv
# .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run app
streamlit run app.py
```

## Notes
- This is a **prototype** for thesis/demo — not for clinical use.
- If your PDFs are images, OCR is not included by default; provide a TXT discharge summary or a text-based PDF for the demo.
- Extend `utils/parsers.py` to add robust extraction rules.
