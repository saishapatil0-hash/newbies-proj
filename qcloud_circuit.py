import os
import time

from qpiai_quantum import Circuit, QpiAIQuantumAuth
from qpiai_quantum.authentication.exceptions import APIKeyInvalidError, AuthError


def run_traffic_penalty_circuit(congestion_factor, api_key=None):
    started_at = time.perf_counter()
    active_key = api_key or os.getenv("QPIAI_API_KEY")
    authentication_time_ms = 0.0
    execution_time_ms = 0.0
    fallback_reason = None
    execution_mode = "local_simulator"
    backend = "QpiAI-QSV-Local"
    status = "success"
    counts = {}

    if active_key:
        auth_started_at = time.perf_counter()
        try:
            QpiAIQuantumAuth.login(api_key=active_key)
            execution_mode = "qpi_cloud"
            backend = "QpiAI-QSV-Simulator"
        except (APIKeyInvalidError, AuthError) as error:
            fallback_reason = type(error).__name__
        except Exception as error:
            fallback_reason = type(error).__name__
        finally:
            authentication_time_ms = round(
                (time.perf_counter() - auth_started_at) * 1000, 3
            )

    try:
        circuit = Circuit(3, 3)
        circuit.h(0)
        circuit.h(1)
        circuit.h(2)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.rz(0, float(congestion_factor) * 1.57)
        circuit.measure([0, 1, 2], [0, 1, 2])

        run_started_at = time.perf_counter()
        try:
            job_result = circuit.run(
                shots=1024,
                experiment_name="BMTC_Headway_Recovery",
                device_name=backend,
            )
        except Exception as error:
            if execution_mode != "qpi_cloud":
                raise
            fallback_reason = type(error).__name__
            execution_mode = "local_simulator"
            backend = "QpiAI-QSV-Local"
            job_result = circuit.run(
                shots=1024,
                experiment_name="BMTC_Headway_Recovery",
                device_name=backend,
            )

        counts = job_result.get_counts()
        execution_time_ms = round((time.perf_counter() - run_started_at) * 1000, 3)
        dominant_state = max(counts, key=counts.get)
        theta_future = int(dominant_state, 2) * 0.25 + 1.0
    except Exception as error:
        fallback_reason = fallback_reason or type(error).__name__
        execution_mode = "local_fallback"
        backend = None
        status = "fallback"
        theta_future = 1.85

    telemetry = {
        "model": "QpiAI 3-qubit traffic-penalty circuit (not a trained ML model)",
        "status": status,
        "execution_mode": execution_mode,
        "backend": backend,
        "shots": 1024,
        "congestion_factor": float(congestion_factor),
        "theta_future": theta_future,
        "counts": counts,
        "dominant_state": max(counts, key=counts.get) if counts else None,
        "authentication_time_ms": authentication_time_ms,
        "execution_time_ms": execution_time_ms,
        "response_time_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "fallback_reason": fallback_reason,
    }
    print(
        f"[TRAFFIC MODEL] {telemetry['model']} | Status: {status} | "
        f"Mode: {execution_mode} | Backend: {backend or 'numeric fallback'} | "
        f"Response: {telemetry['response_time_ms']} ms "
        f"(auth {authentication_time_ms} ms, execution {execution_time_ms} ms)",
        flush=True,
    )
    if fallback_reason:
        print(f"[TRAFFIC MODEL] Fallback reason: {fallback_reason}", flush=True)
    return telemetry
