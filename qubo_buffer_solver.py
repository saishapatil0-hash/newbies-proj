import time


def solve_micro_buffer_qubo(predictions, api_key=None):
    """
    Apply a local delay-threshold heuristic to fleet headway recovery actions.
    """
    started_at = time.perf_counter()
    print("========================================", flush=True)
    print("[DISPATCH] Received dispatch request from UI...", flush=True)
    print("[DISPATCH] Initializing fleet dispatch model...", flush=True)

    fleet = []
    if isinstance(predictions, list):
        fleet = predictions
    elif isinstance(predictions, dict):
        fleet = predictions.get("fleet", [])
        if not fleet:
            fleet = predictions.get("predictions", {}).get("fleet", [])

    actions = []
    if not fleet and isinstance(predictions, list):
        fleet = predictions

    vehicle_types = sorted({
        str(bus.get("vehicle_type", "Unknown"))
        for bus in fleet
        if isinstance(bus, dict)
    })
    print(
        "[DISPATCH] Vehicle types: "
        + (", ".join(vehicle_types) if vehicle_types else "Unknown"),
        flush=True
    )
    print(
        "[DISPATCH] Model: local delay-threshold heuristic "
        "(QpiAI-Opt cloud solver is not invoked)",
        flush=True
    )

    for bus in fleet:
        bus_id = bus.get("bus_id", "BMTC-BUS")
        delay = bus.get("projected_delay_min", bus.get("delay_min", 1.0))
        stop = bus.get("current_stop", "Hebbal")
        
        if delay > 3.0:
            duration = int(min(45, max(20, delay * 6)))
        else:
            duration = 20

        actions.append({
            "bus_id": bus_id,
            "vehicle_type": bus.get("vehicle_type", "Unknown"),
            "target_stop": stop,
            "duration_sec": duration,
            "qubo_status": "Local heuristic decision"
        })

    response_time_ms = round((time.perf_counter() - started_at) * 1000, 3)
    print(
        f"[DISPATCH] Completed {len(actions)} bus decisions using a local heuristic "
        f"in {response_time_ms} ms.",
        flush=True
    )
    print("========================================", flush=True)

    return {
        "solver": "Local delay-threshold dispatch heuristic",
        "model": "Delay-threshold dispatch heuristic (local)",
        "status": "Success",
        "execution_mode": "local",
        "response_time_ms": response_time_ms,
        "total_optimized_buses": len(actions),
        "actions": actions
    }