# Namma Prayana - BMTC Live Transit & Quantum Headway Recovery

A unified, full-stack transit dispatch and headway optimization platform for Bengaluru Metropolitan Transport Corporation (BMTC). The application integrates a single-page interactive transit web frontend with a high-performance Python FastAPI backend, utilizing QpiAI quantum circuits and QUBO (Quadratic Unconstrained Binary Optimization) micro-buffer solvers to mitigate bus bunching and broadcast trilingual alerts (English, Kannada, Hindi).

---

## 1. Project Directory Structure

```text
/namma-prayana
  ├── app.py                   # FastAPI backend server with static & API routing
  ├── data.py                  # BMTC Excel data layer & fleet inventory generator
  ├── predictive_engine.py     # 20-min passenger queuing delay & quantum penalty calculator
  ├── qubo_buffer_solver.py    # QpiAI-Opt QUBO headway micro-buffer solver
  ├── alert_generator.py       # Multilingual commuter notification engine (KN/EN/HI)
  ├── qcloud_circuit.py        # QpiAI Cloud 3-qubit parameterized quantum circuit
  ├── test_qpiai.py            # QpiAI Cloud authentication & QPU resource verification script
  ├── bmtc_dump.xlsx           # Real BMTC schedule, route, and stop dataset
  ├── logo.jpeg                # Namma Prayana branding asset
  ├── requirements.txt         # Project dependencies
  ├── README.md                # Execution & architectural guide
  └── static/
      ├── index.html           # Unified single-page web app (Namma Prayana Live)
      └── logo.jpeg            # Static logo asset for frontend rendering
```

---

## 2. Prerequisites

- Python 3.10+ (tested on Python 3.14)
- Internet connection (for initial package downloads and QpiAI Cloud API verification)

---

## 3. Installation Guide

### Step 1: Open a Terminal & Navigate to the Project Root
```bash
cd "c:\Users\saish\projects\namma-prayana"
```
*(or `cd "c:\Users\saish\projects\bus final"`)*

### Step 2: (Optional but recommended) Create a Virtual Environment
```bash
# On Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## 4. Running the Application

Start the local server using Uvicorn:

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Web App (Frontend):** Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
- **Interactive Swagger Docs:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to test API endpoints directly.
- **Alternative ReDoc UI:** Open [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc).

---

## 5. API Endpoints Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves `static/index.html` (the Namma Prayana frontend UI) |
| `/static/*` | `GET` | Serves static assets (`index.html`, `logo.jpeg`) |
| `/logo.jpeg` | `GET` | Serves the Namma Prayana logo image directly |
| `/api/health` | `GET` | Health check endpoint returning status and service name |
| `/api/fleet` | `GET` | Returns vehicle inventory and depot assignments from `bmtc_dump.xlsx` |
| `/api/optimize` | `GET` | Runs predictive bunching, QUBO buffer solver, and multilingual alert generator. Accepts `scenario` (e.g., `Normal Flow`, `Heavy Rush Hour`, `Accident Delay`) and optional `qpiai_key`. |

---

## 6. Testing QpiAI Cloud Connection

To test connectivity with the QpiAI Quantum Cloud API:

```bash
python test_qpiai.py
```

*Note: If network access or API credentials are unavailable, the application automatically and gracefully falls back to hybrid quantum simulation mode without throwing unhandled exceptions.*
