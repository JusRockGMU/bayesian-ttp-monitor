#!/bin/bash

echo "=== Shutting down services ==="

# Stop Flask (port 8000)
PID_8000=$(lsof -ti :8000)
if [ -n "$PID_8000" ]; then
    echo "Stopping Flask (PID $PID_8000)"
    kill -9 $PID_8000
else
    echo "No Flask server found on port 8000"
fi

# Stop Prometheus (port 9090)
PID_9090=$(lsof -ti :9090)
if [ -n "$PID_9090" ]; then
    echo "Stopping Prometheus (PID $PID_9090)"
    kill -9 $PID_9090
else
    echo "No Prometheus server found on port 9090"
fi

# Stop Grafana
if brew services list | grep -q "^grafana.*started"; then
    echo "Stopping Grafana via Homebrew..."
    brew services stop grafana
else
    PID_3000=$(lsof -ti :3000)
    if [ -n "$PID_3000" ]; then
        echo "Stopping Grafana (PID $PID_3000)"
        kill -9 $PID_3000
    else
        echo "No Grafana process found on port 3000"
    fi
fi

echo "✅ All services stopped (or were not running)"
