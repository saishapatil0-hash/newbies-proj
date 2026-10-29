# app.py
import os
import datetime
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from data import FleetDataset, get_vehicle_fleet_inventory
from predictive_engine import predict_future_bunching
from qubo_buffer_solver import solve_micro_buffer_qubo
from alert_generator import generate_bilingual_alerts

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LOG_FILE = BASE_DIR / "website_test_data_log.txt"

app = FastAPI(
    title="Namma Prayana - BMTC Quantum-Optimized Transit API",
    version="2.0.0",
    description="Full-stack BMTC live transit dispatch, QUBO micro-buffer headway recovery & multimodal alert engine."
)

# Enable CORS for all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory for JS, CSS, images, and HTML assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def log_website_test_event(scenario: str, arrival_rate: int, predictions_count: int, theta: float, solver_decision: dict, alerts: list):
    """
    Appends website test run telemetry to the codebase test data log.
    """
    try:
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{ts}] LIVE API RUN -> Scenario: {scenario} | Arrival Rate: {arrival_rate} pax/min\n")
            f.write(f"  Quantum Traffic Weight (theta_future): {theta}\n")
            f.write(f"  Total Buses Evaluated: {predictions_count} | QUBO Solver: {solver_decision.get('solver')} ({solver_decision.get('status')})\n")
            actions = solver_decision.get("actions", [])
            f.write(f"  Hold Decisions Generated: {len(actions)}\n")
            for a in actions[:3]:
                f.write(f"    * Bus: {a.get('bus_id')} @ {a.get('target_stop')} -> {a.get('duration_sec')}s micro-hold ({a.get('qubo_status')})\n")
            if alerts:
                f.write(f"  Commuter Alert Sample:\n")
                f.write(f"    [EN] {alerts[0].get('english')}\n")
                f.write(f"    [KN] {alerts[0].get('kannada')}\n")
                f.write(f"    [HI] {alerts[0].get('hindi')}\n")
    except Exception as e:
        print(f"[Logging notice] {e}")

@app.get("/", response_class=FileResponse)
def serve_index():
    """
    Serves the Namma Prayana single-page web application.
    """
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>Namma Prayana API is running. static/index.html not found.</h1>", status_code=404)

@app.get("/logo.jpeg")
def serve_logo():
    """
    Serves the BMTC logo asset directly.
    """
    for candidate in [STATIC_DIR / "logo.jpeg", BASE_DIR / "logo.jpeg"]:
        if candidate.exists():
            return FileResponse(str(candidate), media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="logo.jpeg not found")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Namma Prayana BMTC API",
        "version": "2.0.0"
    }

@app.get("/api/fleet")
def get_fleet():
    """
    Returns the real-time vehicle fleet inventory from the BMTC database dump.
    """
    return {"fleet": get_vehicle_fleet_inventory()}

@app.get("/api/optimize")
def run_optimization(scenario: str = "Normal Flow", qpiai_key: str = Query(default="")):
    """
    Runs the full end-to-end predictive bunching calculation, QpiAI-Opt QUBO headway recovery solver,
    and multilingual commuter alert generator.
    """
    dataset = FleetDataset(scenario=scenario)
    fleet_payload = dataset.get_fleet_payload()
    
    # 1. Predict future bunching using passenger queuing & quantum traffic penalty
    predictions = predict_future_bunching(fleet_payload)
    
    # 2. Solve micro-buffer headway stabilization QUBO matrix
    solver_decision = solve_micro_buffer_qubo(predictions, api_key=qpiai_key)
    
    # 3. Generate bilingual & trilingual commuter alerts (Kannada, English, Hindi)
    trilingual_alerts = generate_bilingual_alerts(solver_decision)
    
    theta_val = predictions[0].get("theta_future", 1.85) if predictions else 1.85
    arrival_rate = fleet_payload.get("arrival_rate", 20)
    
    # Automatically log test run to website_test_data_log.txt
    log_website_test_event(
        scenario=scenario,
        arrival_rate=arrival_rate,
        predictions_count=len(predictions),
        theta=theta_val,
        solver_decision=solver_decision,
        alerts=trilingual_alerts
    )
    
    return {
        "scenario": scenario,
        "predictions": predictions,
        "solver_decision": solver_decision,
        "trilingual_alerts": trilingual_alerts,
        "fleet_status": fleet_payload["fleet"]
    }
