@echo off
:: Navigate to your project folder
cd /d "C:\Users\Hamza 3\Generative AI"

:: Run the script using the Python executable
python agenticworkflow.py

:: Pause the window ONLY if the script crashes so you can read the error
if %errorlevel% neq 0 pause