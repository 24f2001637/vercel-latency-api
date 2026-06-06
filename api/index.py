# api/index.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

# ─── CORS ────────────────────────────────────────────────────────────────────
# This allows any website (dashboards, etc.) to call your endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # any origin
    allow_methods=["*"],      # GET, POST, etc.
    allow_headers=["*"],
)

# ─── Load telemetry data once at startup ─────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "latency_data.json")
with open(DATA_PATH) as f:
    TELEMETRY = json.load(f)

# ─── What the incoming request looks like ────────────────────────────────────
class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# ─── Helper: 95th percentile (no numpy needed) ───────────────────────────────
def percentile_95(data: list) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    # Linear interpolation method (same as numpy's default)
    index = 0.95 * (n - 1)
    lower = int(index)
    upper = lower + 1
    if upper >= n:
        return float(sorted_data[-1])
    frac = index - lower
    return sorted_data[lower] + frac * (sorted_data[upper] - sorted_data[lower])

# ─── The actual endpoint ──────────────────────────────────────────────────────
@app.post("/")
def analytics(req: AnalyticsRequest):
    result = {}

    for region in req.regions:
        # Filter records for this region
        records = [r for r in TELEMETRY if r["region"] == region]

        if not records:
            result[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0,
            }
            continue

        latencies = [r["latency_ms"] for r in records]
        uptimes   = [r["uptime"]     for r in records]

        result[region] = {
            "avg_latency": round(sum(latencies) / len(latencies), 4),
            "p95_latency": round(percentile_95(latencies), 4),
            "avg_uptime":  round(sum(uptimes) / len(uptimes), 4),
            "breaches":    sum(1 for l in latencies if l > req.threshold_ms),
        }

    return result