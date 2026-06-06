from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics

# TELEMETRY DATA — already embedded
TELEMETRY_DATA = [
  {"region": "apac", "service": "checkout", "latency_ms": 131.61, "uptime_pct": 98.261, "timestamp": 20250301},
  {"region": "apac", "service": "analytics", "latency_ms": 211.14, "uptime_pct": 98.825, "timestamp": 20250302},
  {"region": "apac", "service": "payments", "latency_ms": 195.45, "uptime_pct": 97.861, "timestamp": 20250303},
  {"region": "apac", "service": "analytics", "latency_ms": 176.47, "uptime_pct": 97.401, "timestamp": 20250304},
  {"region": "apac", "service": "checkout", "latency_ms": 164.12, "uptime_pct": 97.501, "timestamp": 20250305},
  {"region": "apac", "service": "analytics", "latency_ms": 108.58, "uptime_pct": 98.115, "timestamp": 20250306},
  {"region": "apac", "service": "analytics", "latency_ms": 220.71, "uptime_pct": 97.217, "timestamp": 20250307},
  {"region": "apac", "service": "checkout", "latency_ms": 221.65, "uptime_pct": 99.446, "timestamp": 20250308},
  {"region": "apac", "service": "payments", "latency_ms": 206.93, "uptime_pct": 98.464, "timestamp": 20250309},
  {"region": "apac", "service": "catalog", "latency_ms": 186.32, "uptime_pct": 98.924, "timestamp": 20250310},
  {"region": "apac", "service": "support", "latency_ms": 170.28, "uptime_pct": 97.959, "timestamp": 20250311},
  {"region": "apac", "service": "catalog", "latency_ms": 151.58, "uptime_pct": 99.047, "timestamp": 20250312},
  {"region": "emea", "service": "recommendations", "latency_ms": 186.96, "uptime_pct": 98.945, "timestamp": 20250301},
  {"region": "emea", "service": "catalog", "latency_ms": 189.1, "uptime_pct": 97.692, "timestamp": 20250302},
  {"region": "emea", "service": "checkout", "latency_ms": 136.91, "uptime_pct": 97.813, "timestamp": 20250303},
  {"region": "emea", "service": "support", "latency_ms": 201.11, "uptime_pct": 97.679, "timestamp": 20250304},
  {"region": "emea", "service": "checkout", "latency_ms": 191.28, "uptime_pct": 99.006, "timestamp": 20250305},
  {"region": "emea", "service": "analytics", "latency_ms": 163.8, "uptime_pct": 97.874, "timestamp": 20250306},
  {"region": "emea", "service": "support", "latency_ms": 107.49, "uptime_pct": 99.174, "timestamp": 20250307},
  {"region": "emea", "service": "checkout", "latency_ms": 210.72, "uptime_pct": 99.383, "timestamp": 20250308},
  {"region": "emea", "service": "checkout", "latency_ms": 130.07, "uptime_pct": 98.454, "timestamp": 20250309},
  {"region": "emea", "service": "analytics", "latency_ms": 223.13, "uptime_pct": 97.802, "timestamp": 20250310},
  {"region": "emea", "service": "catalog", "latency_ms": 136.91, "uptime_pct": 97.335, "timestamp": 20250311},
  {"region": "emea", "service": "support", "latency_ms": 214.73, "uptime_pct": 97.666, "timestamp": 20250312},
  {"region": "amer", "service": "analytics", "latency_ms": 158.7, "uptime_pct": 97.369, "timestamp": 20250301},
  {"region": "amer", "service": "catalog", "latency_ms": 138.41, "uptime_pct": 98.021, "timestamp": 20250302},
  {"region": "amer", "service": "recommendations", "latency_ms": 108.94, "uptime_pct": 99.474, "timestamp": 20250303},
  {"region": "amer", "service": "recommendations", "latency_ms": 208.09, "uptime_pct": 97.867, "timestamp": 20250304},
  {"region": "amer", "service": "analytics", "latency_ms": 104.98, "uptime_pct": 97.253, "timestamp": 20250305},
  {"region": "amer", "service": "payments", "latency_ms": 180.65, "uptime_pct": 97.911, "timestamp": 20250306},
  {"region": "amer", "service": "payments", "latency_ms": 144.66, "uptime_pct": 99.481, "timestamp": 20250307},
  {"region": "amer", "service": "analytics", "latency_ms": 126.8, "uptime_pct": 98.515, "timestamp": 20250308},
  {"region": "amer", "service": "payments", "latency_ms": 171.07, "uptime_pct": 99.058, "timestamp": 20250309},
  {"region": "amer", "service": "recommendations", "latency_ms": 155.84, "uptime_pct": 98.606, "timestamp": 20250310},
  {"region": "amer", "service": "checkout", "latency_ms": 216.6, "uptime_pct": 97.297, "timestamp": 20250311},
  {"region": "amer", "service": "analytics", "latency_ms": 183.43, "uptime_pct": 97.125, "timestamp": 20250312}
]

FIELD_REGION = "region"
FIELD_LATENCY = "latency_ms"
FIELD_UPTIME = "uptime_pct"

app = FastAPI()

# CORS: allow any origin for POST requests
# REMOVED allow_credentials=True — it conflicts with allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestBody(BaseModel):
    regions: list
    threshold_ms: int

def calculate_p95(values):
    if not values:
        return 0
    sorted_values = sorted(values)
    n = len(sorted_values)
    index = int(n * 0.95)
    if index >= n:
        index = n - 1
    return sorted_values[index]

@app.post("/")
async def analyze(request: RequestBody):
    results = {}
    for region in request.regions:
        region_records = [r for r in TELEMETRY_DATA if r.get(FIELD_REGION) == region]
        if not region_records:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
            continue
        latencies = [r.get(FIELD_LATENCY, 0) for r in region_records]
        uptimes = [r.get(FIELD_UPTIME, 0) for r in region_records]
        avg_latency = statistics.mean(latencies)
        p95_latency = calculate_p95(latencies)
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for lat in latencies if lat > request.threshold_ms)
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }
    return results