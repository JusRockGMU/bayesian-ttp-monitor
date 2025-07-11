#!/usr/bin/env python3

import os
import json
import requests
import xml.etree.ElementTree as ET

# -------------------------------
# CONFIGURATION
# -------------------------------

BN_FOLDER = "xdsl_files"
DASHBOARD_FOLDER = "dashboards"
APT_NODE_SUFFIX = "Occurred"

# Grafana connection
GRAFANA_URL = "http://localhost:3000"
USERNAME = "admin"
PASSWORD = "admin"

# Dashboard output file
OVERVIEW_DASHBOARD_FILE = os.path.join(DASHBOARD_FOLDER, "overview_dashboard.json")

AUTO_UPLOAD = True

# -------------------------------
# UTILITIES
# -------------------------------

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# -------------------------------
# STEP 1 - Get Prometheus UID
# -------------------------------

def get_prometheus_uid():
    url = f"{GRAFANA_URL}/api/datasources"
    response = requests.get(url, auth=(USERNAME, PASSWORD))
    response.raise_for_status()

    datasources = response.json()
    for ds in datasources:
        if ds.get("type") == "prometheus":
            print(f"[INFO] Found Prometheus UID: {ds['uid']}")
            return ds["uid"]

    raise RuntimeError("No Prometheus datasource found in Grafana.")

# -------------------------------
# STEP 2 - Parse Nodes from XDSL
# -------------------------------

def extract_nodes_from_xdsl(xdsl_path):
    nodes = []
    tree = ET.parse(xdsl_path)
    root = tree.getroot()

    for node in root.findall(".//cpt"):
        node_id = node.attrib.get("id")
        if node_id:
            nodes.append(node_id)

    return nodes

def get_apt_nodes():
    apt_nodes = {}
    for file in os.listdir(BN_FOLDER):
        if file.endswith(".xdsl"):
            apt_name = file.replace(".xdsl", "")
            xdsl_path = os.path.join(BN_FOLDER, file)
            nodes = extract_nodes_from_xdsl(xdsl_path)
            apt_nodes[apt_name] = nodes
    return apt_nodes

# -------------------------------
# STEP 3 - Build Overview Dashboard
# -------------------------------

def build_overview_dashboard(apt_names, prometheus_uid):
    panels = []
    y_pos = 0

    for i, apt in enumerate(sorted(apt_names)):
        metric = f"bn_{apt}{APT_NODE_SUFFIX}"

        panel = {
            "type": "stat",
            "title": f"{apt} Occurred Probability",
            "datasource": {
                "type": "prometheus",
                "uid": prometheus_uid
            },
            "gridPos": {
                "h": 8,
                "w": 6,
                "x": (i % 4) * 6,
                "y": y_pos
            },
            "id": i + 1,
            "pluginVersion": "12.0.2",
            "targets": [
                {
                    "datasource": {
                        "type": "prometheus",
                        "uid": prometheus_uid
                    },
                    "expr": metric,
                    "refId": "A",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "color": {
                        "mode": "thresholds"
                    },
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green"},
                            {"color": "yellow", "value": 0.51},
                            {"color": "red", "value": 0.8}
                        ]
                    },
                    "unit": "percentunit"
                }
            },
            "options": {
                "colorMode": "background",
                "graphMode": "area",
                "justifyMode": "auto",
            }
        }

        panels.append(panel)

        if (i + 1) % 4 == 0:
            y_pos += 8

    dashboard = {
        "dashboard": {
            "id": None,
            "uid": None,
            "title": "APT Bayesian Network Overview",
            "timezone": "browser",
            "editable": True,
            "schemaVersion": 41,
            "version": 0,
            "refresh": "10s",
            "time": {
                "from": "now-6h",
                "to": "now"
            },
            "panels": panels,
        },
        "folderId": 0,
        "overwrite": True
    }

    return dashboard

# -------------------------------
# STEP 4 - Build Per-APT Dashboard
# -------------------------------

def build_per_apt_dashboard(apt_name, node_list, prometheus_uid):
    panels = []
    y_pos = 0

    for i, node in enumerate(sorted(node_list)):
        metric = f"bn_{node}"

        panel = {
            "type": "stat",
            "title": node,
            "datasource": {
                "type": "prometheus",
                "uid": prometheus_uid
            },
            "gridPos": {
                "h": 6,
                "w": 6,
                "x": (i % 4) * 6,
                "y": y_pos
            },
            "id": i + 1,
            "pluginVersion": "12.0.2",
            "targets": [
                {
                    "datasource": {
                        "type": "prometheus",
                        "uid": prometheus_uid
                    },
                    "expr": metric,
                    "refId": "A",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "color": {
                        "mode": "thresholds"
                    },
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green"},
                            {"color": "yellow", "value": 0.51},
                            {"color": "red", "value": 0.8}
                        ]
                    },
                    "unit": "percentunit"
                }
            },
            "options": {
                "colorMode": "background",
                "graphMode": "area",
                "justifyMode": "auto",
            }
        }

        panels.append(panel)

        if (i + 1) % 4 == 0:
            y_pos += 6

    dashboard = {
        "dashboard": {
            "id": None,
            "uid": None,
            "title": f"APT: {apt_name}",
            "timezone": "browser",
            "editable": True,
            "schemaVersion": 41,
            "version": 0,
            "refresh": "10s",
            "time": {
                "from": "now-6h",
                "to": "now"
            },
            "panels": panels,
        },
        "folderId": 0,
        "overwrite": True
    }

    return dashboard

# -------------------------------
# STEP 5 - Save Dashboards
# -------------------------------

def save_dashboard_to_file(dashboard_json, filename):
    with open(filename, "w") as f:
        json.dump(dashboard_json, f, indent=2)
    print(f"[INFO] Saved dashboard → {filename}")

# -------------------------------
# STEP 6 - Upload to Grafana
# -------------------------------

def upload_dashboard(dashboard_json, apt_name):
    url = f"{GRAFANA_URL}/api/dashboards/db"
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        url,
        auth=(USERNAME, PASSWORD),
        headers=headers,
        data=json.dumps(dashboard_json)
    )
    if response.status_code not in (200, 202):
        print(f"[ERROR] Upload failed for {apt_name}:")
        print(response.text)
    else:
        print(f"[SUCCESS] Dashboard uploaded for {apt_name}.")
        try:
            print(response.json())
        except:
            pass

# -------------------------------
# MAIN
# -------------------------------

if __name__ == "__main__":
    ensure_dir(DASHBOARD_FOLDER)

    prometheus_uid = get_prometheus_uid()
    apt_nodes = get_apt_nodes()

    # Build overview dashboard
    apt_names = list(apt_nodes.keys())
    overview_dashboard = build_overview_dashboard(apt_names, prometheus_uid)
    save_dashboard_to_file(overview_dashboard, OVERVIEW_DASHBOARD_FILE)
    if AUTO_UPLOAD:
        upload_dashboard(overview_dashboard, "Overview")

    # Build one dashboard per APT
    for apt, nodes in apt_nodes.items():
        dashboard_json = build_per_apt_dashboard(apt, nodes, prometheus_uid)
        filename = os.path.join(DASHBOARD_FOLDER, f"dashboard_{apt}.json")
        save_dashboard_to_file(dashboard_json, filename)
        if AUTO_UPLOAD:
            upload_dashboard(dashboard_json, apt)
