from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

# ── Load data ─────────────────────────────────────────────────────────────────
TELEMETRY = []
LOAD_ERROR = None

for candidate in [
    os.path.join(os.path.dirname(__file__), "latency_data.json"),
    os.path.join(os.path.dirname(__file__), "q-vercel-latency.json"),
    os.path.join(os.path.dirname(__file__), "..", "latency_data.json"),
    os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json"),
]:
    try:
        with open(candidate) as f:
            TELEMETRY = json.load(f)
        break
    except FileNotFoundError:
        continue
    except Exception as e:
        LOAD_ERROR = str(e)
        break

if not TELEMETRY and LOAD_ERROR is None:
    LOAD_ERROR = "JSON file not found in api/ or root folder"

# ── Schema ────────────────────────────────────────────────────────────────────
class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# ── P95 helper ────────────────────────────────────────────────────────────────
def percentile_95(data: list) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    n = len(s)
    index = 0.95 * (n - 1)
    lo = int(index)
    hi = lo + 1
    if hi >= n:
        return float(s[-1])
    return s[lo] + (index - lo) * (s[hi] - s[lo])

# ── Preflight handler ─────────────────────────────────────────────────────────
@app.options("/")
def preflight():
    return JSONResponse(content={}, headers=CORS_HEADERS)

# ── POST endpoint ─────────────────────────────────────────────────────────────
@app.post("/")
def analytics(req: AnalyticsRequest):
    if LOAD_ERROR:
        return JSONResponse(content={"DEBUG_ERROR": LOAD_ERROR}, headers=CORS_HEADERS)
    try:
        result = {}
        for region in req.regions:
            records = [r for r in TELEMETRY if r["region"] == region]
            if not records:
                result[region] = {
                    "avg_latency": None, "p95_latency": None,
                    "avg_uptime":  None, "breaches":    0,
                }
                continue
            latencies = [r["latency_ms"] for r in records]
            uptimes   = [r["uptime"]     for r in records]
            result[region] = {
                "avg_latency": round(sum(latencies) / len(latencies), 4),
                "p95_latency": round(percentile_95(latencies), 4),
                "avg_uptime":  round(sum(uptimes)   / len(uptimes),   4),
                "breaches":    sum(1 for l in latencies if l > req.threshold_ms),
            }
        return JSONResponse(content=result, headers=CORS_HEADERS)
    except Exception as e:
        return JSONResponse(
            content={"DEBUG_ERROR": str(e), "trace": traceback.format_exc()},
            headers=CORS_HEADERS
        )

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return JSONResponse(content={
        "status":         "ok" if not LOAD_ERROR else "error",
        "records_loaded": len(TELEMETRY),
        "load_error":     LOAD_ERROR,
        "sample_record":  TELEMETRY[0] if TELEMETRY else None,
    }, headers=CORS_HEADERS)