import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import sys
import logging
from typing import Dict, List, Optional
# Import the dotenv loader module
from dotenv import load_dotenv

# Load variables from the .env file dynamically
load_dotenv()

# Force windows console stream to use UTF-8 natively
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============ CONFIGURATION ============
LATITUDE = 24.860735
LONGITUDE = 67.001137

# REAL-WORLD KARACHI FILTER CONTROLS
RAIN_THRESHOLD_MM = 2.0       # Ignore micro-drizzle/humidity traces under 2mm
MIN_PROBABILITY_PERCENT = 40   # Only alert if the forecast has at least 40% confidence

# Securely extract SMTP configuration keys from the environment variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

# Verification safety check to ensure configuration loaded successfully
if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, TO_EMAIL]):
    print("❌ Critical configuration error: Missing credentials in .env file.")
    sys.exit(1)

# Safely handle Windows home directory expansion
LOG_FILE = os.path.join(os.path.expanduser("~"), "rain_alert.log")

# Clear any lingering default logger handlers to avoid double-printing
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Setup clear, production-safe logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ============ WEATHER FUNCTIONS ============

def get_weather_forecast(lat: float, lon: float, days: int = 2) -> Optional[Dict]:
    """Fetch weather forecast from Open-Meteo API."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability,weathercode",
        "timezone": "auto",
        "forecast_days": days
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error fetching weather data: {e}")
        return None

def check_for_rain(weather_data: Dict, threshold: float = RAIN_THRESHOLD_MM) -> List[Dict]:
    """Analyze forecast for valid rain events meeting both volume and probability baselines."""
    if not weather_data or "hourly" not in weather_data:
        return []
    
    hourly = weather_data["hourly"]
    times = hourly.get("time", [])
    precipitations = hourly.get("precipitation", [])
    probabilities = hourly.get("precipitation_probability", [])
    weathercodes = hourly.get("weathercode", [])
    
    rainy_hours = []
    current_time = datetime.now()
    
    for i, (time_str, precip) in enumerate(zip(times, precipitations)):
        forecast_time = datetime.fromisoformat(time_str)
        if forecast_time < current_time:
            continue
        
        prob = probabilities[i] if i < len(probabilities) else 0
        
        if precip is not None and precip >= threshold and prob >= MIN_PROBABILITY_PERCENT:
            code = weathercodes[i] if i < len(weathercodes) else 0
            
            rainy_hours.append({
                "time": forecast_time,
                "precipitation": precip,
                "probability": prob,
                "weathercode": code
            })
    return rainy_hours

def get_weather_description(weathercode: int) -> str:
    """Convert WMO weather code to description."""
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle",
        53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
        63: "Moderate rain", 65: "Heavy rain", 80: "Slight rain showers",
        81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm"
    }
    return weather_codes.get(weathercode, "Rain expected")

def send_rain_alert(rainy_hours: List[Dict], location: str) -> bool:
    """Send email alert using secure port 465 wrapper variables fetched from environment."""
    if not rainy_hours:
        return False
    
    first_rain = rainy_hours[0]
    rain_count = len(rainy_hours)
    total_precip = sum(r['precipitation'] for r in rainy_hours)
    
    body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; }}
            .alert {{ background-color: #f44336; color: white; padding: 15px; border-radius: 10px; }}
            .rain-detail {{ background-color: #e3f2fd; padding: 10px; margin: 8px 0; border-radius: 5px; }}
            .summary {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="alert">
            <h2>⚠️ SIGNIFICANT RAIN ALERT for {location}</h2>
            <p>Actionable rainfall predicted over the next 48 hours.</p>
        </div>
        <div class="summary">
            <h3>Summary Matrix:</h3>
            <ul>
                <li>Total Impact Duration: <strong>{rain_count} hour(s)</strong></li>
                <li>Total Expected Rainfall: <strong>{total_precip:.1f} mm</strong></li>
                <li>Expected Commencement: <strong>{first_rain['time'].strftime('%I:%M %p on %A, %B %d')}</strong></li>
                <li>Confidence Level: <strong>{first_rain['probability']}%</strong></li>
                <li>Type: <strong>{get_weather_description(first_rain['weathercode'])}</strong></li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    msg["Subject"] = f"⚠️ RAIN ALERT - {total_precip:.1f}mm Rain Predicted for {location}"
    msg.attach(MIMEText(body, "html"))
    
    try:
        logging.info("📧 Connecting via direct SSL to Gmail (Port 465)...")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logging.info(f"✅ Rain alert email successfully delivered to {TO_EMAIL}!")
        return True
    except Exception as e:
        logging.error(f"❌ Critical error sending email: {e}")
        return False

# ============ MAIN FUNCTION ============

def main():
    logging.info("============================================================")
    logging.info("🌧️ Secure Weather Protection Agent Initialized")
    logging.info(f"📍 Target Coordinates: {LATITUDE}, {LONGITUDE} (Karachi)")
    logging.info(f"📧 Notification Endpoint: {TO_EMAIL}")
    
    logging.info("🔍 Pulling real-time forecast arrays...")
    weather_data = get_weather_forecast(LATITUDE, LONGITUDE)
    
    if not weather_data:
        logging.error("❌ Failed to secure weather data matrix.")
        return
    
    logging.info("✅ Weather data retrieved successfully")
    
    rainy_hours = check_for_rain(weather_data)
    
    if rainy_hours:
        logging.warning(f"⚠️ GENUINE WEATHER EVENT DETECTED! {len(rainy_hours)} hours meet thresholds.")
        success = send_rain_alert(rainy_hours, "Karachi, Pakistan")
        if not success:
            logging.error("❌ Notification process failed.")
    else:
        logging.info("✅ Weather conditions stable. No rain anomalies detected above thresholds.")
    
    logging.info("🏁 Rain Alert Agent Finished Cleanly")
    logging.info("============================================================")

if __name__ == "__main__":
    main()