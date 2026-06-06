from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import numpy as np

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"]
)

# Load dataset
BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "q-vercel-latency.json", "r") as f:
    telemetry = json.load(f)


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/")
def analyze(payload: dict):

    regions = payload.get("regions", [])
    threshold = payload.get("threshold_ms", 180)

    result = {}

    for region in regions:

        records = [
            r for r in telemetry
            if r["region"] == region
        ]

        if not records:
            result[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
            continue

        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]

        result[region] = {
            "avg_latency": round(float(np.mean(latencies)), 2),
            "p95_latency": round(float(np.percentile(latencies, 95)), 2),
            "avg_uptime": round(float(np.mean(uptimes)), 3),
            "breaches": sum(
                1
                for x in latencies
                if x > threshold
            )
        }

    return result