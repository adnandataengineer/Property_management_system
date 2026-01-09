#!/bin/bash
# Script to restart the Django server with correct settings

# Kill any existing Django server on port 8000
echo "Stopping any Django servers on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No process found on port 8000"

# Wait a moment
sleep 2

# Start the server with DEBUG=True
echo "Starting Django server with DEBUG=True on port 8000..."
DEBUG=True USE_SQLITE=1 venv/bin/python manage.py runserver 0.0.0.0:8000
