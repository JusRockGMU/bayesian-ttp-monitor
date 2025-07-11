#!/bin/bash

echo "-------------------------------------"
echo "     Starting BN Monitoring Stack    "
echo "-------------------------------------"

# -------------------------------
# Paths
# -------------------------------

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

GET_APTS_LOG="$LOG_DIR/get_APTs.log"
GEN_BN_LOG="$LOG_DIR/generate_bn.log"
GRAFANA_DASH_LOG="$LOG_DIR/grafana_dashboards.log"
FLASK_LOG="$LOG_DIR/bn_ws.log"
PROM_LOG="$LOG_DIR/prometheus.log"
GRAFANA_LOG="$LOG_DIR/grafana.log"

PROM_CONFIG="prometheus.yml"

# -------------------------------
# Check Python
# -------------------------------

PY_CMD=$(which python)

echo "[INFO] Using Python interpreter: $PY_CMD"

$PY_CMD -c "import pysmile" 2> /dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] pysmile not found in Python interpreter: $PY_CMD"
    echo "Please activate your virtual environment before running this script."
    exit 1
fi

# -------------------------------
# Download APT JSONs
# -------------------------------

echo "[+] Running get_APTs.py ..."
$PY_CMD get_APTs.py > "$GET_APTS_LOG" 2>&1
if [ $? -eq 0 ]; then
    echo "[✓] APT JSONs downloaded (logs → $GET_APTS_LOG)"
else
    echo "[!] get_APTs.py failed. Check logs: $GET_APTS_LOG"
fi

# -------------------------------
# Generate Bayesian Networks
# -------------------------------

echo "[+] Running generate_bn.py ..."
$PY_CMD generate_bn.py > "$GEN_BN_LOG" 2>&1
if [ $? -eq 0 ]; then
    echo "[✓] Bayesian Networks generated (logs → $GEN_BN_LOG)"
else
    echo "[!] generate_bn.py failed. Check logs: $GEN_BN_LOG"
fi

# -------------------------------
# Start Prometheus
# -------------------------------

echo "[+] Starting Prometheus ..."
prometheus --config.file="$PROM_CONFIG" > "$PROM_LOG" 2>&1 &
PROM_PID=$!

sleep 2
curl -s http://localhost:9090 > /dev/null
if [ $? -eq 0 ]; then
    echo "[✓] Prometheus running on port 9090"
else
    echo "[!] Prometheus failed to start. Check logs: $PROM_LOG"
fi

# -------------------------------
# Start Flask BN Webservice
# -------------------------------

echo "[+] Starting BN Webservice ..."
$PY_CMD bn_ws.py > "$FLASK_LOG" 2>&1 &
FLASK_PID=$!

sleep 2
curl -s http://localhost:8000/metrics > /dev/null
if [ $? -eq 0 ]; then
    echo "[✓] BN Webservice running on port 8000"
else
    echo "[!] BN Webservice failed to start. Check logs: $FLASK_LOG"
fi

# -------------------------------
# Generate Grafana Dashboards
# -------------------------------

echo "[+] Generating Grafana dashboards ..."
$PY_CMD generate_grafana_dashboards.py > "$GRAFANA_DASH_LOG" 2>&1
if [ $? -eq 0 ]; then
    echo "[✓] Grafana dashboards generated (logs → $GRAFANA_DASH_LOG)"
else
    echo "[!] Dashboard generation failed. Check logs: $GRAFANA_DASH_LOG"
fi

# -------------------------------
# Start Grafana
# -------------------------------

echo "[+] Starting Grafana ..."
export GF_SECURITY_ADMIN_USER="admin"
export GF_SECURITY_ADMIN_PASSWORD="admin"

grafana-server > "$GRAFANA_LOG" 2>&1 &
GRAFANA_PID=$!

sleep 3
curl -s http://localhost:3000 > /dev/null
if [ $? -eq 0 ]; then
    echo "[✓] Grafana running on port 3000"
else
    echo "[!] Grafana failed to start. Check logs: $GRAFANA_LOG"
fi

echo "-------------------------------------"
echo "[✓] All services launched successfully."
echo "[✓] Logs stored in ./logs/"
echo "-------------------------------------"

# Save PIDs for stop script
echo $PROM_PID > "$LOG_DIR/prometheus.pid"
echo $FLASK_PID > "$LOG_DIR/bn_ws.pid"
echo $GRAFANA_PID > "$LOG_DIR/grafana.pid"
