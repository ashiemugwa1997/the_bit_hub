@echo off
echo BitHub Installation Script
echo ==========================

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is required but not installed.
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist env (
    echo Creating virtual environment...
    python -m venv env
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create virtual environment.
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call env\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Run setup script
echo Running setup script...
python setup.py

echo Installation complete!
echo To start the server, run: env\Scripts\activate.bat ^&^& python manage.py runserver
