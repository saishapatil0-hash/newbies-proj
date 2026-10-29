# data.py
import pandas as pd
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, "bmtc_dump.xlsx")

# Global DataFrame cache to avoid re-reading the 1MB Excel file on every API call
_CACHED_DF = None

def get_bmtc_dataframe():
    global _CACHED_DF
    if _CACHED_DF is None:
        if os.path.exists(EXCEL_PATH):
            try:
                _CACHED_DF = pd.read_excel(EXCEL_PATH)
            except Exception as e:
                print(f"[Data warning] Could not parse Excel: {e}")
                _CACHED_DF = pd.DataFrame()
        else:
            _CACHED_DF = pd.DataFrame()
    return _CACHED_DF

class FleetDataset:
    def __init__(self, scenario="Normal Flow", sample_size=30):
        self.scenario = scenario
        self.sample_size = sample_size
        self.load_dispatcher_dataset()

    def load_dispatcher_dataset(self):
        df = get_bmtc_dataframe()
        self.buses = []

        # Scenario parameters for realistic headway variance & delays
        if self.scenario == "Heavy Rush Hour":
            delay_range = (5.0, 12.0)
            var_range = (180, 420)
            self.passenger_arrival_rate = 55
            status_pool = ["Bunching Risk", "Headway Delayed", "Bunching Critical"]
        elif self.scenario == "Accident Delay":
            delay_range = (8.0, 20.0)
            var_range = (300, 600)
            self.passenger_arrival_rate = 70
            status_pool = ["Accident Blocked", "Rerouted", "Severe Congestion"]
        else:  # Normal Flow
            delay_range = (0.5, 4.0)
            var_range = (20, 90)
            self.passenger_arrival_rate = 20
            status_pool = ["Normal", "Optimal", "On Schedule"]

        bus_types = ["AC Vajra", "Ordinary", "Vayu Vajra", "EV Midi"]

        if not df.empty:
            # Take a diverse slice of active routes for dispatcher tracking
            sample_df = df.head(self.sample_size)
            for index, row in sample_df.iterrows():
                route_val = str(row.get('route_no') or row.get('Route') or f"R-{index+1}")
                origin_val = str(row.get('origin') or row.get('Current_Stop') or "Majestic")
                dest_val = str(row.get('destination') or "Kempegowda Bus Station")

                b_type = bus_types[index % len(bus_types)]
                bus_id = f"BMTC-{route_val}-{str(index+1).zfill(2)}"
                d_min = round(random.uniform(*delay_range), 1)

                self.buses.append({
                    "bus_id": bus_id,
                    "route": route_val,
                    "type": b_type,
                    "current_stop": origin_val,
                    "destination": dest_val,
                    "delay_min": d_min,
                    "headway_variance_sec": random.randint(*var_range),
                    "driver_hours": round(random.uniform(3.0, 7.5), 1),
                    "spare_available": bool(random.choice([True, False])),
                    "tickets_sold": random.randint(35, 95),
                    "eta_error_pct": round(random.uniform(1.5, 8.0), 1),
                    "status": random.choice(status_pool)
                })
        else:
            # High-fidelity fallback dataset if excel is missing
            fallback_routes = [
                ("BMTC-500D-01", "500D", "AC Vajra", "Silk Board"),
                ("BMTC-500D-02", "500D", "AC Vajra", "Marathahalli"),
                ("BMTC-258A-01", "258A", "Ordinary", "Hebbal"),
                ("BMTC-258A-02", "258A", "Ordinary", "Yelahanka"),
                ("BMTC-335E-01", "335E", "Vayu Vajra", "Majestic"),
                ("BMTC-335E-02", "335E", "Vayu Vajra", "Whitefield"),
                ("BMTC-G4-01", "G-4", "EV Midi", "MG Road"),
                ("BMTC-G4-02", "G-4", "EV Midi", "Brigade Road"),
            ]
            for b_id, rt, tp, stp in fallback_routes:
                self.buses.append({
                    "bus_id": b_id,
                    "route": rt,
                    "type": tp,
                    "current_stop": stp,
                    "delay_min": round(random.uniform(*delay_range), 1),
                    "headway_variance_sec": random.randint(*var_range),
                    "driver_hours": round(random.uniform(3.0, 7.0), 1),
                    "spare_available": True,
                    "tickets_sold": random.randint(40, 85),
                    "eta_error_pct": round(random.uniform(2.0, 6.0), 1),
                    "status": random.choice(status_pool)
                })

    def get_fleet_payload(self):
        return {
            "scenario": self.scenario,
            "arrival_rate": self.passenger_arrival_rate,
            "fleet": self.buses
        }

def get_vehicle_fleet_inventory():
    """
    Returns fleet inventory list for the BMTC dispatch system.
    """
    df = get_bmtc_dataframe()
    if not df.empty:
        inventory = []
        models = [
            ("Tata Starbus AC Vajra", "AC Fleet", "Hebbal Depot", "50 Seats"),
            ("Ashok Leyland Non-AC", "Ordinary", "Majestic Depot", "65 Seats"),
            ("Volvo 8400 BMTC", "Vayu Vajra Airport", "KBS Depot", "45 Seats"),
            ("Electric Midi Bus (Olectra)", "Electric EV", "Shanthinagar Depot", "35 Seats")
        ]
        sample_df = df.head(40)
        for i, r in sample_df.iterrows():
            m_tuple = models[i % len(models)]
            route_val = str(r.get('route_no') or f"R{i+1}")
            origin_val = str(r.get('origin') or "Majestic")
            inventory.append({
                "id": f"BMTC-{route_val}-{str(i+1).zfill(2)}",
                "model": m_tuple[0],
                "category": m_tuple[1],
                "depot": m_tuple[2],
                "capacity": m_tuple[3],
                "assigned_route": route_val,
                "current_terminal": origin_val,
                "status": "In Service"
            })
        return inventory

    return [
        {"id": "F-01", "model": "Tata Starbus AC Vajra", "category": "AC Fleet", "depot": "Hebbal Depot", "capacity": "50 Seats", "status": "In Service"},
        {"id": "F-02", "model": "Ashok Leyland Non-AC", "category": "Ordinary", "depot": "Majestic Depot", "capacity": "65 Seats", "status": "In Service"},
        {"id": "F-03", "model": "Volvo 8400 BMTC Volvo", "category": "Vayu Vajra Airport", "depot": "KBS Depot", "capacity": "45 Seats", "status": "In Service"},
        {"id": "F-04", "model": "Electric Midi Bus (Olectra)", "category": "Electric EV", "depot": "Shanthinagar Depot", "capacity": "35 Seats", "status": "Charging / Standby"}
    ]
