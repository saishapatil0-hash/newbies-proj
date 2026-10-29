# predictive_engine.py
from qcloud_circuit import run_traffic_penalty_circuit

def predict_future_bunching(fleet_data):
    """
    Calculates passenger queue pressure and projected delays over a 20-minute horizon.
    Integrates with QpiAI parameterized quantum circuit for traffic penalty weighting.
    """
    rate = fleet_data.get("arrival_rate", 20)
    p_current = 45  # Baseline current waiting passengers at major transfer hub
    
    # Formula: P_waiting = P_current + Rate * 20
    p_waiting = p_current + (rate * 20)
    
    # Fetch quantum-optimized traffic penalty weight (theta_future)
    theta_future = run_traffic_penalty_circuit(congestion_factor=rate / 10.0)
    
    predictions = []
    fleet = fleet_data.get("fleet", [])
    for bus in fleet:
        delay = float(bus.get("delay_min", 1.0))
        projected_delay = delay * theta_future
        predictions.append({
            "bus_id": bus.get("bus_id", "BMTC-BUS"),
            "route": bus.get("route", "500D"),
            "current_stop": bus.get("current_stop", "Majestic"),
            "predicted_queue_passengers": p_waiting,
            "projected_delay_min": round(projected_delay, 2),
            "theta_future": theta_future
        })
        
    return predictions
