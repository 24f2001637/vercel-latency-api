from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

# 1. Setup the app
app = FastAPI()

# 2. Add CORS (The "Bouncer")
# This allows dashboards from any website to ask your API for data safely.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_methods=["POST"], # Only allows POST requests
    allow_headers=["*"],
)

# 3. Define what the incoming request looks like
class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# 4. Load the JSON data
# We do this carefully so Vercel can find the file in the cloud
current_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(current_dir)
file_path = os.path.join(root_dir, 'q-vercel-latency.json')

with open(file_path, 'r') as f:
    telemetry_data = json.load(f)

# 5. Create the POST Endpoint
@app.post("/")
def get_metrics(request: AnalyticsRequest):
    results = {}
    
    # Loop through each region they asked for
    for target_region in request.regions:
        # Filter the data for just this region
        region_records = [d for d in telemetry_data if d.get("region") == target_region]
        
        if not region_records:
            continue
            
        # Extract lists of just the numbers we need
        latencies = [d["latency"] for d in region_records]
        uptimes = [d["uptime"] for d in region_records]
        
        # Calculate Averages (Mean)
        avg_latency = sum(latencies) / len(latencies)
        avg_uptime = sum(uptimes) / len(uptimes)
        
        # Calculate Breaches (How many times was latency > threshold?)
        breaches = sum(1 for lat in latencies if lat > request.threshold_ms)
        
        # Calculate p95 Latency 
        # (The value where 95% of the data is lower, 5% is higher)
        latencies_sorted = sorted(latencies)
        p95_index = int(0.95 * len(latencies_sorted))
        
        # If the index is out of bounds, grab the last one
        if p95_index >= len(latencies_sorted):
            p95_index = len(latencies_sorted) - 1
            
        p95_latency = latencies_sorted[p95_index]
        
        # Save to our results dictionary
        results[target_region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return results