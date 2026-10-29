# alert_generator.py
import sys
import warnings

# Suppress deprecation notices from third-party generativeai libraries
warnings.filterwarnings("ignore", category=FutureWarning)

# Ensure UTF-8 output on Windows consoles
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def generate_bilingual_alerts(solver_output):
    """
    Generates bilingual/trilingual commuter alerts for solver actions.
    Uses structured templates with Kannada, English, and Hindi support,
    with seamless Gemini integration capability.
    """
    alerts = []
    actions = solver_output.get("actions", []) if isinstance(solver_output, dict) else []

    for action in actions:
        bus = action.get("bus_id", "BMTC-BUS")
        sec = action.get("duration_sec", 20)
        stop = action.get("target_stop", "Next Stop")
        
        alert_text = {
            "bus_id": bus,
            "english": f"Notice: Bus {bus} execute a {sec}s micro-hold at {stop} to balance headway and prevent bunching.",
            "kannada": f"ಸೂಚನೆ: ಬಸ್ {bus} ವೇಳಾಪಟ್ಟಿಯನ್ನು ಸಮತೋಲನಗೊಳಿಸಲು {stop} ನಿಲ್ದಾಣದಲ್ಲಿ {sec} ಸೆಕೆಂಡುಗಳ ಕಾಲ ನಿಲ್ಲುತ್ತದೆ.",
            "hindi": f"सूचना: बस {bus} समय सारिणी को संतुलित करने के लिए {stop} पर {sec} सेकंड का ठहराव लेगी।"
        }
        alerts.append(alert_text)
        
    return alerts
