from typing import List, Dict
from datetime import datetime, timedelta
import pytz

FREQ_MAP = {
    "qd (daily)": [9],
    "bid (2x/day)": [9, 21],
    "tid (3x/day)": [9, 15, 21],
    "qid (4x/day)": [8, 12, 16, 20],
}

def build_med_schedule(meds: List[Dict], tz: str = "America/Chicago"):
    """Return today's schedule of reminders as list of dicts"""
    now = datetime.now(pytz.timezone(tz))
    today = now.date()
    out = []
    for m in meds:
        hours = FREQ_MAP.get(m.get("freq","qd (daily)"), [9])
        for h in hours:
            dt = datetime(now.year, now.month, now.day, h, 0, 0, tzinfo=now.tzinfo)
            out.append({
                "when": dt.isoformat(),
                "med": m["name"],
                "dose": m.get("dose",""),
                "status": "due" if dt >= now else "past"
            })
    return out

def adherence_summary(events: List[Dict]):
    """Placeholder: compute adherence percentage from events"""
    if not events:
        return {"scheduled": 0, "taken": 0, "adherence_pct": None}
    scheduled = len(events)
    taken = sum(1 for e in events if e.get("status") == "taken")
    pct = round(100.0 * taken / scheduled, 1) if scheduled else None
    return {"scheduled": scheduled, "taken": taken, "adherence_pct": pct}
