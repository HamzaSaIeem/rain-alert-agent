# Agentic Rain Alert System

This project is a Python-based weather alert agent that checks the Open-Meteo forecast for a target location and emails you when significant rain is predicted.

## What it does

- Pulls hourly forecast data for the configured latitude and longitude.
- Filters for meaningful rainfall using a minimum rainfall threshold and probability threshold.
- Sends an HTML email alert through Gmail SMTP when rain conditions are met.
- Supports Windows execution through the included batch file.

## Files

- [agenticworkflow.py](agenticworkflow.py) - Main weather monitoring and alert script.
- [Run Rain Alert.bat](Run%20Rain%20Alert.bat) - Convenience launcher for Windows.
- [.env](.env) - Local secrets file for email credentials.

## Setup

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with these values:

```env
EMAIL_ADDRESS=your_sender_account@gmail.com
EMAIL_PASSWORD=your_google_app_password
TO_EMAIL=your_destination_inbox@gmail.com
```

## Run

Run the script directly:

```bash
python agenticworkflow.py
```

Or use the Windows batch file:

```bat
Run Rain Alert.bat
```

## Configuration

Update the target coordinates near the top of [agenticworkflow.py](agenticworkflow.py) to match your location.
