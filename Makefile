# -----------------------------------------------------
# Makefile for BN Monitoring Stack - Midterm Project
# -----------------------------------------------------

# Hard-coded Python interpreter from your virtual environment
PYTHON := /opt/anaconda3/envs/midterm_env/bin/python

# Logs folder
LOG_DIR := logs

# Directories we may want to wipe on a full clean
INPUT_DIR := inputs
XDSL_DIR := xdsl_files
DASHBOARD_DIR := dashboards

# Ensure logs folder exists
$(shell mkdir -p $(LOG_DIR))

.PHONY: all clean clean-full generate get run-prometheus run-flask run-grafana dashboards start

# Check that pysmile can be imported
check-python:
	@echo "[INFO] Using Python interpreter: $(PYTHON)"
	@$(PYTHON) -c "import pysmile" 2>/dev/null || \
		(echo "[ERROR] pysmile not found in Python interpreter: $(PYTHON)"; exit 1)

# Download all APT JSON files
get:
	@echo "[+] Downloading APT JSON files..."
	@$(PYTHON) get_APTs.py > $(LOG_DIR)/get_APTs.log 2>&1 && \
		echo "[✓] APT JSONs downloaded" || \
		(echo "[!] Failed to download APT JSONs"; exit 1)

# Generate .xdsl files from inputs
generate: check-python
	@echo "[+] Generating Bayesian Networks (.xdsl files)..."
	@$(PYTHON) generate_bn.py > $(LOG_DIR)/generate_bn.log 2>&1 && \
		echo "[✓] BN files generated" || \
		(echo "[!] BN generation failed, see logs."; exit 1)

# Run Prometheus
run-prometheus:
	@echo "[+] Starting Prometheus..."
	@prometheus --config.file=prometheus.yml > $(LOG_DIR)/prometheus.log 2>&1 & \
	sleep 3 && \
	curl -s http://localhost:9090 > /dev/null && \
	echo "[✓] Prometheus is running on port 9090" || \
	(echo "[!] Prometheus failed to start."; exit 1)

# Run Flask webservice
run-flask: check-python
	@echo "[+] Starting Flask Web Service..."
	@$(PYTHON) bn_ws.py > $(LOG_DIR)/flask.log 2>&1 & \
	sleep 3 && \
	curl -s http://localhost:8000/metrics > /dev/null && \
	echo "[✓] Flask web service is running on port 8000" || \
	(echo "[!] Flask web service failed to start."; exit 1)

# Run Grafana
run-grafana:
	@echo "[+] Starting Grafana (brew)..."
	@brew services start grafana > $(LOG_DIR)/grafana.log 2>&1
	@sleep 5
	@curl -s http://localhost:3000 > /dev/null && \
		echo "[✓] Grafana is running on port 3000" || \
		(echo "[!] Grafana failed to start."; exit 1)


# Generate dashboards
dashboards: check-python
	@echo "[+] Generating Grafana Dashboards..."
	@$(PYTHON) generate_grafana_dashboard.py > $(LOG_DIR)/dashboards.log 2>&1 && \
		echo "[✓] Dashboards generated and uploaded" || \
		(echo "[!] Dashboard generation failed."; exit 1)

# Start entire stack
start: check-python get generate run-prometheus run-flask run-grafana dashboards
	@echo "[✓] All services are running."

# Clean only logs
clean:
	@echo "[INFO] Cleaning logs..."
	@rm -rf $(LOG_DIR)/*
	@echo "[✓] Logs cleaned."

# Full clean wipes inputs, xdsl_files, dashboards, logs
clean-full:
	@echo "[INFO] Performing FULL CLEAN..."
	@rm -rf $(LOG_DIR)/* $(INPUT_DIR)/* $(XDSL_DIR)/* $(DASHBOARD_DIR)/*
	@echo "[✓] Full clean complete."
