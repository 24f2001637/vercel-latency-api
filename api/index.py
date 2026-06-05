# api/index.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import numpy as np

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"]
)

with open("q-vercel-latency.json", "r") as f:
    telemetry = json.load(f)

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
        uptimes = [r["uptime"] for r in records]

        result[region] = {
            "avg_latency": round(sum(latencies)/len(latencies), 2),
            "p95_latency": round(
                np.percentile(latencies, 95),
                2
            ),
            "avg_uptime": round(
                sum(uptimes)/len(uptimes),
                4
            ),
            "breaches": sum(
                1
                for x in latencies
                if x > threshold
            )
        }

    return result