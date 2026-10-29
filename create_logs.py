# create_logs.py
import sys
import os
import io
import datetime
import time

# Ensure UTF-8 output
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from qpiai_quantum import QpiAIQuantumAuth
from data import FleetDataset, get_vehicle_fleet_inventory
from predictive_engine import predict_future_bunching_with_telemetry
from qubo_buffer_solver import solve_micro_buffer_qubo
from alert_generator import generate_bilingual_alerts
import qcloud_circuit

timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Capture Tool 1: QpiAI Cloud Authentication & Resources
api_key = os.getenv("QPIAI_API_KEY")
resource_status = "not attempted (QPIAI_API_KEY is not configured)"
resource_output = "No authenticated cloud resource lookup was performed."
resource_lookup_time_ms = 0.0
if api_key:
    old_stdout = sys.stdout
    buffer = io.StringIO()
    resource_started_at = time.perf_counter()
    try:
        sys.stdout = buffer
        QpiAIQuantumAuth.login(api_key=api_key)
        QpiAIQuantumAuth.list_compute_resources()
        resource_status = "success"
    except Exception as error:
        resource_status = f"failed ({type(error).__name__})"
    finally:
        sys.stdout = old_stdout
        resource_lookup_time_ms = round(
            (time.perf_counter() - resource_started_at) * 1000, 3
        )
        resource_output = buffer.getvalue().strip() or "SDK returned no resource details."

tool_log_lines = []
tool_log_lines.append("================================================================================")
tool_log_lines.append("             QPIAI QUANTUM & OPTIMIZATION TOOLS - EXECUTION LOG               ")
tool_log_lines.append(f"Generated: {timestamp}")
tool_log_lines.append("================================================================================\n")

tool_log_lines.append("--------------------------------------------------------------------------------")
tool_log_lines.append("TOOL 1: QpiAI Quantum Cloud Authentication & Resource Discovery")
tool_log_lines.append("--------------------------------------------------------------------------------")
tool_log_lines.append("[SDK] qpiai-quantum v0.7.5")
tool_log_lines.append(f"[AUTH] Status: {resource_status}")
tool_log_lines.append(f"[RESOURCES] Lookup response time: {resource_lookup_time_ms} ms")
tool_log_lines.append("[RESOURCES] Resource lookup result:")
tool_log_lines.append(resource_output)
tool_log_lines.append("\n")

tool_log_lines.append("--------------------------------------------------------------------------------")
tool_log_lines.append("TOOL 2: Parameterized Quantum Circuit Execution (QpiAI Circuit Engine)")
tool_log_lines.append("--------------------------------------------------------------------------------")
tool_log_lines.append("[CIRCUIT ARCHITECTURE]")
tool_log_lines.append("  Qubits: 3 | Classical Bits: 3")
tool_log_lines.append("  Gates: H(0), H(1), H(2) -> CX(0,1), CX(1,2) -> Rz(0, theta=congestion*1.57) -> MeasureAll")
tool_log_lines.append("  Target Device: QpiAI-QSV-Simulator when cloud auth succeeds; otherwise QpiAI-QSV-Local")
tool_log_lines.append("  Shots: 1024")
tool_log_lines.append("  Timing values below are client-observed wall-clock milliseconds, not QPU-only execution time.")
tool_log_lines.append("  Circuit Representation (QASM 2.0 / QpiAI IR):")
tool_log_lines.append("    OPENQASM 2.0;")
tool_log_lines.append("    include \"qelib1.inc\";")
tool_log_lines.append("    qreg q[3];")
tool_log_lines.append("    creg c[3];")
tool_log_lines.append("    h q[0]; h q[1]; h q[2];")
tool_log_lines.append("    cx q[0], q[1]; cx q[1], q[2];")
tool_log_lines.append("    rz(congestion_factor * 1.57) q[0];")
tool_log_lines.append("    measure q[0] -> c[0]; measure q[1] -> c[1]; measure q[2] -> c[2];")

# Test traffic congestion circuit runs
for cong in [1.5, 3.5, 7.0]:
    circuit_result = qcloud_circuit.run_traffic_penalty_circuit(
        congestion_factor=cong,
        api_key=api_key,
    )
    tool_log_lines.append(
        f"  Execution Run -> Congestion Factor: {cong:.1f} | "
        f"Status: {circuit_result['status']} | Mode: {circuit_result['execution_mode']} | "
        f"Backend: {circuit_result['backend'] or 'local numeric fallback'} | "
        f"theta_future: {circuit_result['theta_future']}"
    )
    tool_log_lines.append(
        f"    Response: {circuit_result['response_time_ms']} ms | "
        f"Auth: {circuit_result['authentication_time_ms']} ms | "
        f"Execution: {circuit_result['execution_time_ms']} ms | "
        f"Shots: {circuit_result['shots']} | Dominant State: {circuit_result['dominant_state']}"
    )
    if circuit_result["fallback_reason"]:
        tool_log_lines.append(f"    Fallback reason: {circuit_result['fallback_reason']}")

tool_log_lines.append("\n")
tool_log_lines.append("--------------------------------------------------------------------------------")
tool_log_lines.append("TOOL 3: Fleet Dispatch Model")
tool_log_lines.append("--------------------------------------------------------------------------------")
tool_log_lines.append("[MODEL] Local delay-threshold dispatch heuristic (not a QpiAI-Opt cloud solver)")

ds_test = FleetDataset(scenario="Heavy Rush Hour")
payload_test = ds_test.get_fleet_payload()
prediction_started_at = time.perf_counter()
preds_test, prediction_telemetry = predict_future_bunching_with_telemetry(
    payload_test,
    api_key=api_key,
)
solver_res = solve_micro_buffer_qubo(preds_test)
tool_log_lines.append(
    f"  Traffic Model: {prediction_telemetry['traffic_model']['model']} | "
    f"Mode: {prediction_telemetry['traffic_model']['execution_mode']} | "
    f"Backend: {prediction_telemetry['traffic_model']['backend'] or 'local numeric fallback'}"
)
tool_log_lines.append(
    f"  Traffic Model Response Time: "
    f"{prediction_telemetry['traffic_model']['response_time_ms']} ms"
)
tool_log_lines.append(
    f"  Prediction Calculation Time: "
    f"{prediction_telemetry['prediction_calculation_time_ms']} ms"
)

tool_log_lines.append(f"  Solver Engine: {solver_res['solver']}")
tool_log_lines.append(f"  Dispatch Model: {solver_res['model']}")
tool_log_lines.append(f"  Convergence Status: {solver_res['status']}")
tool_log_lines.append(f"  Dispatch Response Time: {solver_res['response_time_ms']} ms")
tool_log_lines.append(
    f"  Prediction + Dispatch Wall Time: "
    f"{round((time.perf_counter() - prediction_started_at) * 1000, 3)} ms"
)
tool_log_lines.append(f"  Total Optimized Vehicles: {solver_res['total_optimized_buses']}")
tool_log_lines.append("  Selected Dispatch Micro-Hold Actions:")
for act in solver_res['actions'][:6]:
    tool_log_lines.append(f"    - Bus ID: {act['bus_id']} | Vehicle Type: {act['vehicle_type']} | Target Stop: {act['target_stop']} | Recommended Micro-Hold: {act['duration_sec']}s | Status: {act['qubo_status']}")

tool_log_lines.append("\n")
tool_log_lines.append("--------------------------------------------------------------------------------")
tool_log_lines.append("TOOL 4: Multilingual Commuter Alert Engine (Kannada, English, Hindi)")
tool_log_lines.append("--------------------------------------------------------------------------------")
alerts = generate_bilingual_alerts(solver_res)
for al in alerts[:3]:
    tool_log_lines.append(f"  Bus {al['bus_id']}:")
    tool_log_lines.append(f"    [EN] {al['english']}")
    tool_log_lines.append(f"    [KN] {al['kannada']}")
    tool_log_lines.append(f"    [HI] {al['hindi']}")

tool_log_text = "\n".join(tool_log_lines)

# Write to qpiai_tools_execution_log.txt
with open(os.path.join(BASE_DIR, "qpiai_tools_execution_log.txt"), "w", encoding="utf-8") as f:
    f.write(tool_log_text)

print("qpiai_tools_execution_log.txt generated successfully.")

# Create website_test_data_log.txt
web_log_lines = []
web_log_lines.append("================================================================================")
web_log_lines.append("                 NAMMA PRAYANA WEBSITE TEST DATA & TELEMETRY LOG                ")
web_log_lines.append(f"Logged At: {timestamp}")
web_log_lines.append("================================================================================\n")

web_log_lines.append("--------------------------------------------------------------------------------")
web_log_lines.append("1. LIVE FLEET INVENTORY TEST DATA (Loaded from bmtc_dump.xlsx)")
web_log_lines.append("--------------------------------------------------------------------------------")
inv = get_vehicle_fleet_inventory()
web_log_lines.append(f"Total Vehicles in Active Inventory: {len(inv)}")
for item in inv[:10]:
    web_log_lines.append(f"  - Vehicle ID: {item['id']} | Model: {item['model']} | Category: {item['category']} | Depot: {item['depot']} | Route: {item.get('assigned_route', 'N/A')} | Status: {item['status']}")

web_log_lines.append("\n--------------------------------------------------------------------------------")
web_log_lines.append("2. SCENARIO DISPATCH RUNS TEST DATA (Normal Flow, Heavy Rush Hour, Accident Delay)")
web_log_lines.append("--------------------------------------------------------------------------------")

for sc in ["Normal Flow", "Heavy Rush Hour", "Accident Delay"]:
    scenario_started_at = time.perf_counter()
    ds = FleetDataset(scenario=sc)
    pl = ds.get_fleet_payload()
    preds, scenario_telemetry = predict_future_bunching_with_telemetry(
        pl,
        api_key=api_key,
    )
    sol = solve_micro_buffer_qubo(preds)
    als = generate_bilingual_alerts(sol)
    
    web_log_lines.append(f"\n>>> SCENARIO: {sc.upper()}")
    web_log_lines.append(f"    Passenger Arrival Rate: {pl['arrival_rate']} passengers/min")
    web_log_lines.append(f"    Active Fleet Sample: {len(pl['fleet'])} buses monitored")
    web_log_lines.append(f"    Calculated Quantum Penalty Weight (theta_future): {preds[0]['theta_future']}")
    web_log_lines.append(f"    Projected 20-min Transfer Hub Queue: {preds[0]['predicted_queue_passengers']} commuters waiting")
    web_log_lines.append(f"    Dispatch Status: {sol['status']} ({sol['total_optimized_buses']} buses processed)")
    web_log_lines.append(f"    Dispatch Model: {sol['model']}")
    web_log_lines.append(
        f"    Traffic Model: {scenario_telemetry['traffic_model']['model']} | "
        f"Mode: {scenario_telemetry['traffic_model']['execution_mode']} | "
        f"Backend: {scenario_telemetry['traffic_model']['backend'] or 'local numeric fallback'}"
    )
    web_log_lines.append(
        f"    Response Times (ms): traffic model="
        f"{scenario_telemetry['traffic_model']['response_time_ms']}, "
        f"prediction={scenario_telemetry['prediction_calculation_time_ms']}, "
        f"dispatch={sol['response_time_ms']}"
    )
    web_log_lines.append(
        f"    Full Scenario Calculation Time: "
        f"{round((time.perf_counter() - scenario_started_at) * 1000, 3)} ms"
    )
    web_log_lines.append("    Sample Headway Hold Orders:")
    for act in sol['actions'][:4]:
        web_log_lines.append(f"      * Bus: {act['bus_id']} | Vehicle Type: {act['vehicle_type']} at {act['target_stop']} -> Hold: {act['duration_sec']}s ({act['qubo_status']})")
    web_log_lines.append("    Sample Commuter Multilingual Alert:")
    web_log_lines.append(f"      * English: {als[0]['english']}")
    web_log_lines.append(f"      * Kannada: {als[0]['kannada']}")
    web_log_lines.append(f"      * Hindi:   {als[0]['hindi']}")

web_log_text = "\n".join(web_log_lines)

# Write to website_test_data_log.txt
with open(os.path.join(BASE_DIR, "website_test_data_log.txt"), "w", encoding="utf-8") as f:
    f.write(web_log_text)

print("website_test_data_log.txt generated successfully.")
