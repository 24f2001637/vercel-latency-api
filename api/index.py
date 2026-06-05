from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import numpy as np

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load telemetry data
BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "q-vercel-latency.json", "r") as f:
    telemetry = json.load(f)

# Handle CORS preflight
@app.options("/")
async def options_root():
    response = Response(status_code=200)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Main endpoint
@app.post("/")
def analyze(data: dict):

    regions = data["regions"]
    threshold = data["threshold_ms"]

    result = {}

    for region in regions:

        records = [
            r for r in telemetry
            if r["region"] == region
        ]

        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]

        result[region] = {
            "avg_latency": round(sum(latencies) / len(latencies), 2),
            "p95_latency": round(np.percentile(latencies, 95), 2),
            "avg_uptime": round(sum(uptimes) / len(uptimes), 3),
            "breaches": sum(
                1 for x in latencies
                if x > threshold
            )
        }

    return JSONResponse(
        content=result,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )