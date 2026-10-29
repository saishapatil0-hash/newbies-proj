# predictive_engine.py
import time

from qcloud_circuit import run_traffic_penalty_circuit


def predict_future_bunching_with_telemetry(fleet_data, api_key=None):
    """
    Calculates passenger queue pressure and projected delays over a 20-minute horizon.
    Integrates with QpiAI parameterized quantum circuit for traffic penalty weighting.
    """
    started_at = time.perf_counter()
    rate = fleet_data.get("arrival_rate", 20)
    p_current = 45  # Baseline current waiting passengers at major transfer hub
    
    # Formula: P_waiting = P_current + Rate * 20
    p_waiting = p_current + (rate * 20)
    
    circuit_telemetry = run_traffic_penalty_circuit(
        congestion_factor=rate / 10.0,
        api_key=api_key,
    )
    theta_future = circuit_telemetry["theta_future"]

    predictions = []
    fleet = fleet_data.get("fleet", [])
    for bus in fleet:
        delay = float(bus.get("delay_min", 1.0))
        projected_delay = delay * theta_future
        predictions.append({
            "bus_id": bus.get("bus_id", "BMTC-BUS"),
            "route": bus.get("route", "500D"),
            "vehicle_type": bus.get("type", "Unknown"),
            "current_stop": bus.get("current_stop", "Majestic"),
            "predicted_queue_passengers": p_waiting,
            "projected_delay_min": round(projected_delay, 2),
            "theta_future": theta_future
        })
        
    telemetry = {
        "traffic_model": circuit_telemetry,
        "prediction_calculation_time_ms": round(
            (time.perf_counter() - started_at) * 1000, 3
        ),
    }
    return predictions, telemetry


def predict_future_bunching(fleet_data):
    predictions, _ = predict_future_bunching_with_telemetry(fleet_data)
    return predictions
