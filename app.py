# app.py
import os
import datetime
import logging
import time
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Header, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from data import FleetDataset, get_vehicle_fleet_inventory
from predictive_engine import predict_future_bunching_with_telemetry
from qubo_buffer_solver import solve_micro_buffer_qubo
from alert_generator import generate_bilingual_alerts

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LOG_FILE = BASE_DIR / "website_test_data_log.txt"
ACTIVITY_LOG_FILE = BASE_DIR / "website_activity.log"

activity_logger = logging.getLogger("website.activity")
activity_logger.setLevel(logging.INFO)
activity_logger.propagate = False
if not activity_logger.handlers:
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(ACTIVITY_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    activity_logger.addHandler(console_handler)
    activity_logger.addHandler(file_handler)

app = FastAPI(
    title="Namma Prayana - BMTC Transit Prediction API",
    version="2.0.0",
    description="BMTC transit predictions with a QpiAI traffic circuit, local dispatch heuristic, and multilingual alerts."
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


class ActivityEvent(BaseModel):
    event: Literal["demo_login", "login_prompt_opened", "ui_click", "ui_change"]
    user_name: str | None = Field(default=None, max_length=80)
    role: str | None = Field(default=None, max_length=40)
    bus_id: str | None = Field(default=None, max_length=40)
    element_id: str | None = Field(default=None, max_length=80)
    element_label: str | None = Field(default=None, max_length=100)


@app.middleware("http")
async def log_http_activity(request, call_next):
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
        activity_logger.exception(
            "HTTP request failed method=%s path=%s duration_ms=%s",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise

    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
    activity_logger.info(
        "HTTP request method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def _activity_script() -> str:
    return r"""
<script>
(() => {
  const sendActivity = (event, control) => {
    let user = {};
    try { user = JSON.parse(localStorage.getItem('np_user') || '{}'); } catch (_) {}
    const body = {
      event,
      user_name: user.n || null,
      role: user.role || null,
      bus_id: user.bus || null,
      element_id: control && control.id ? control.id.slice(0, 80) : null,
      element_label: control
        ? (control.getAttribute('aria-label') || control.title || control.innerText || control.textContent || '')
            .trim().replace(/\\s+/g, ' ').slice(0, 100)
        : null
    };
    fetch('/api/activity', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
      keepalive: true
    }).catch(error => console.error('[Activity log] Could not send event:', error));
  };

  document.addEventListener('click', event => {
    const control = event.target.closest('button, a, [role="button"]');
    if (!control) return;
    sendActivity('ui_click', control);
    if (control.id === 'lgo') {
      window.setTimeout(() => {
        const error = document.getElementById('lerr');
        const login = document.getElementById('login');
        if (error && !error.textContent && login && !login.classList.contains('on')) {
          sendActivity('demo_login', null);
        }
      }, 0);
    } else if (control.id === 'guest') {
      sendActivity('demo_login', null);
    } else if (control.id === 'lo' || control.id === 'mp') {
      sendActivity('login_prompt_opened', control);
    }
  }, true);

  document.addEventListener('change', event => {
    const field = event.target;
    if (field instanceof HTMLElement && field.id) {
      sendActivity('ui_change', field);
    }
  }, true);
})();
</script>
"""


@app.post("/api/activity")
def record_activity(event: ActivityEvent):
    if event.event == "demo_login":
        activity_logger.info(
            "DEMO LOGIN (frontend-only; server did not authenticate) "
            "user=%r role=%r bus_id=%r",
            event.user_name or "Guest",
            event.role or "Passenger",
            event.bus_id or "none",
        )
    elif event.event == "login_prompt_opened":
        activity_logger.info(
            "LOGIN PROMPT OPENED user=%r role=%r",
            event.user_name or "Guest",
            event.role or "unknown",
        )
    else:
        activity_logger.info(
            "UI event=%s user=%r role=%r element_id=%r label=%r",
            event.event,
            event.user_name or "Guest",
            event.role or "unknown",
            event.element_id or "unknown",
            event.element_label or "",
        )
    return {"status": "logged"}


def log_website_test_event(
    scenario: str,
    arrival_rate: int,
    predictions_count: int,
    theta: float,
    solver_decision: dict,
    alerts: list,
    model_telemetry: dict,
    request_time_ms: float,
):
    """
    Appends website test run telemetry to the codebase test data log.
    """
    try:
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{ts}] LIVE API RUN -> Scenario: {scenario} | Arrival Rate: {arrival_rate} pax/min\n")
            f.write(f"  Quantum Traffic Weight (theta_future): {theta}\n")
            traffic_model = model_telemetry["traffic_model"]
            f.write(
                f"  Traffic Model: {traffic_model['model']} | Status: {traffic_model['status']} "
                f"| Mode: {traffic_model['execution_mode']} | Backend: {traffic_model['backend'] or 'local numeric fallback'}\n"
            )
            f.write(
                f"  Traffic Model Times (ms): auth={traffic_model['authentication_time_ms']}, "
                f"execution={traffic_model['execution_time_ms']}, response={traffic_model['response_time_ms']}\n"
            )
            f.write(
                f"  Dispatch Model: {solver_decision.get('model')} | "
                f"Response Time: {solver_decision.get('response_time_ms')} ms\n"
            )
            f.write(f"  Full Optimization Response Time: {request_time_ms} ms\n")
            f.write(f"  Total Buses Evaluated: {predictions_count} | Dispatch Engine: {solver_decision.get('solver')} ({solver_decision.get('status')})\n")
            f.write(f"  Dispatch Model: {solver_decision.get('model', 'Not reported')}\n")
            actions = solver_decision.get("actions", [])
            f.write(f"  Hold Decisions Generated: {len(actions)}\n")
            for a in actions[:3]:
                f.write(f"    * Bus: {a.get('bus_id')} | Type: {a.get('vehicle_type', 'Unknown')} @ {a.get('target_stop')} -> {a.get('duration_sec')}s micro-hold ({a.get('qubo_status')})\n")
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
        html = index_path.read_text(encoding="utf-8")
        if "</body>" in html:
            html = html.replace("</body>", f"{_activity_script()}</body>", 1)
        else:
            html += _activity_script()
        return HTMLResponse(html)
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
def run_optimization(
    scenario: str = "Normal Flow",
    qpiai_key: str = Header(default="", alias="X-QpiAI-Key"),
):
    """
    Runs prediction, traffic-circuit evaluation, local dispatch heuristic, and multilingual alerts.
    """
    request_started_at = time.perf_counter()
    dataset = FleetDataset(scenario=scenario)
    fleet_payload = dataset.get_fleet_payload()
    
    # 1. Predict bunching using passenger queuing and the traffic-penalty circuit.
    predictions, model_telemetry = predict_future_bunching_with_telemetry(
        fleet_payload,
        api_key=qpiai_key or None,
    )
    
    # 2. Calculate dispatch actions using the local delay-threshold heuristic.
    solver_decision = solve_micro_buffer_qubo(predictions, api_key=qpiai_key)
    
    # 3. Generate bilingual & trilingual commuter alerts (Kannada, English, Hindi)
    trilingual_alerts = generate_bilingual_alerts(solver_decision)
    
    theta_val = predictions[0].get("theta_future", 1.85) if predictions else 1.85
    arrival_rate = fleet_payload.get("arrival_rate", 20)
    request_time_ms = round(
        (time.perf_counter() - request_started_at) * 1000, 3
    )
    
    # Automatically log test run to website_test_data_log.txt
    log_website_test_event(
        scenario=scenario,
        arrival_rate=arrival_rate,
        predictions_count=len(predictions),
        theta=theta_val,
        solver_decision=solver_decision,
        alerts=trilingual_alerts,
        model_telemetry=model_telemetry,
        request_time_ms=request_time_ms,
    )
    traffic_model = model_telemetry["traffic_model"]
    activity_logger.info(
        "OPTIMIZATION completed scenario=%r buses=%s traffic_model=%r "
        "mode=%s backend=%s dispatch_model=%r timings_ms=%s",
        scenario,
        len(predictions),
        traffic_model["model"],
        traffic_model["execution_mode"],
        traffic_model["backend"] or "local numeric fallback",
        solver_decision["model"],
        {
            "traffic_model": traffic_model["response_time_ms"],
            "dispatch_model": solver_decision["response_time_ms"],
            "total": request_time_ms,
        },
    )
    
    return {
        "scenario": scenario,
        "predictions": predictions,
        "solver_decision": solver_decision,
        "model_telemetry": model_telemetry,
        "timings_ms": {
            "traffic_model_response": model_telemetry["traffic_model"]["response_time_ms"],
            "prediction_calculation": model_telemetry["prediction_calculation_time_ms"],
            "dispatch_model_response": solver_decision["response_time_ms"],
            "optimization_total": request_time_ms,
        },
        "trilingual_alerts": trilingual_alerts,
        "fleet_status": fleet_payload["fleet"]
    }
