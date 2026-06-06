from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from pydantic import BaseModel
from typing import List
import json, os, traceback

app = FastAPI()

# ── CORS: raw middleware — fires on EVERY request, including OPTIONS ───────────
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age":       "86400",
        })
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# ── Load data ─────────────────────────────────────────────────────────────────
TELEMETRY, LOAD_ERROR = [], None

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
        LOAD_ERROR = str(e); break

if not TELEMETRY and LOAD_ERROR is None:
    LOAD_ERROR = "JSON file not found"

# ── Schema ────────────────────────────────────────────────────────────────────
class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# ── P95 ───────────────────────────────────────────────────────────────────────
def p95(data):
    if not data: return 0.0
    s = sorted(data); n = len(s)
    i = 0.95 * (n - 1); lo = int(i); hi = lo + 1
    if hi >= n: return float(s[-1])
    return s[lo] + (i - lo) * (s[hi] - s[lo])

# ── POST ──────────────────────────────────────────────────────────────────────
@app.post("/")
def analytics(req: AnalyticsRequest):
    if LOAD_ERROR:
        return JSONResponse({"DEBUG_ERROR": LOAD_ERROR})
    try:
        result = {}
        for region in req.regions:
            rows = [r for r in TELEMETRY if r["region"] == region]
            if not rows:
                result[region] = {"avg_latency": None, "p95_latency": None,
                                  "avg_uptime": None, "breaches": 0}
                continue
            lat = [r["latency_ms"] for r in rows]
            upt = [r["uptime"]     for r in rows]
            result[region] = {
                "avg_latency": round(sum(lat)/len(lat), 4),
                "p95_latency": round(p95(lat), 4),
                "avg_uptime":  round(sum(upt)/len(upt), 4),
                "breaches":    sum(1 for l in lat if l > req.threshold_ms),
            }
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"DEBUG_ERROR": str(e), "trace": traceback.format_exc()})

# ── GET health ────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return JSONResponse({
        "status":         "ok" if not LOAD_ERROR else "error",
        "records_loaded": len(TELEMETRY),
        "load_error":     LOAD_ERROR,
        "sample_record":  TELEMETRY[0] if TELEMETRY else None,
    })