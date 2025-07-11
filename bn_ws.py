#!/usr/bin/env python3

import os
import pysmile
import pysmile_license
from flask import Flask, request, jsonify
from prometheus_client import generate_latest, Gauge, Counter, Histogram, CONTENT_TYPE_LATEST

app = Flask(__name__)

# -----------------------------
# LOAD ALL BNs
# -----------------------------

BN_FOLDER = "xdsl_files"
APT_NODE_SUFFIX = "Occurred"

nets = {}
apt_nodes = {}

print("[INFO] Loading all .xdsl files...")

for file in os.listdir(BN_FOLDER):
    if file.endswith(".xdsl"):
        apt_name = file.replace(".xdsl", "")
        path = os.path.join(BN_FOLDER, file)

        net = pysmile.Network()
        net.read_file(path)

        nets[apt_name] = net

        root_node = f"{apt_name}{APT_NODE_SUFFIX}"
        found = False

        handle = net.get_first_node()
        while handle >= 0:
            name = net.get_node_name(handle)
            if name == root_node:
                found = True
                break
            handle = net.get_next_node(handle)

        if found:
            apt_nodes[apt_name] = root_node
        else:
            print(f"[WARN] APT root node {root_node} not found in {file}")

        print(f"[INFO] Loaded {file}")

print(f"[INFO] Total BNs loaded: {len(nets)}")

# -----------------------------
# PROMETHEUS METRICS
# -----------------------------

apt_gauges = {}
for apt_name in nets.keys():
    gauge_name = f"bn_{apt_name}{APT_NODE_SUFFIX}"
    apt_gauges[apt_name] = Gauge(
        gauge_name,
        f"Belief that {apt_name} occurred (TRUE probability)"
    )

node_gauges = {}

def get_node_gauge(node_name):
    if node_name not in node_gauges:
        metric_name = f"bn_{node_name}".replace(".", "_").replace("-", "_")
        node_gauges[node_name] = Gauge(
            metric_name,
            f"Belief (TRUE probability) for evidence node {node_name} across all BNs"
        )
    return node_gauges[node_name]

EVIDENCE_REQUESTS_TOTAL = Counter(
    "evidence_requests_total",
    "Total number of POST requests to /evidence"
)

EVIDENCE_REQUEST_DURATION = Histogram(
    "evidence_request_duration_seconds",
    "Time spent processing /evidence requests"
)

# -----------------------------
# INITIALIZE METRICS
# -----------------------------

print("[INFO] Performing initial belief update to populate Prometheus metrics...")

for apt, net in nets.items():
    net.clear_all_evidence()
    net.update_beliefs()

    handle = net.get_first_node()
    while handle >= 0:
        name = net.get_node_name(handle)
        values = net.get_node_value(handle)
        true_prob = values[1] if values and len(values) > 1 else 0.0

        try:
            gauge = get_node_gauge(name)
            gauge.set(true_prob)
        except Exception as e:
            print(f"[WARN] Could not initialize gauge for node {name} in {apt}: {e}")

        handle = net.get_next_node(handle)

    root_node = apt_nodes.get(apt)
    if root_node:
        try:
            belief = net.get_node_value(root_node)[1]
            apt_gauges[apt].set(belief)
        except pysmile.SMILEException as e:
            print(f"[WARN] Could not initialize root node gauge for {apt}: {e}")
            apt_gauges[apt].set(0.0)

print("[INFO] Initial metrics populated.")

# -----------------------------
# API ROUTES
# -----------------------------

@app.route("/nodes", methods=["GET"])
def list_nodes():
    all_nodes = {}
    for apt, net in nets.items():
        node_names = []
        handle = net.get_first_node()
        while handle >= 0:
            name = net.get_node_name(handle)
            node_names.append(name)
            handle = net.get_next_node(handle)
        all_nodes[apt] = node_names
    return jsonify(all_nodes)


@app.route("/evidence", methods=["POST"])
@EVIDENCE_REQUEST_DURATION.time()
def update_evidence():
    EVIDENCE_REQUESTS_TOTAL.inc()

    data = request.get_json()
    evidence_list = data.get("evidence", [])

    results = {}

    for apt, net in nets.items():
        net.clear_all_evidence()

        nodes_in_bn = set()
        handle = net.get_first_node()
        while handle >= 0:
            name = net.get_node_name(handle)
            nodes_in_bn.add(name)
            handle = net.get_next_node(handle)

        for ev in evidence_list:
            if ev in nodes_in_bn:
                try:
                    net.set_evidence(ev, "True")
                except pysmile.SMILEException as e:
                    print(f"[WARN] Could not set evidence {ev} in {apt}: {e}")

        net.update_beliefs()

        node_beliefs = {}
        handle = net.get_first_node()
        while handle >= 0:
            name = net.get_node_name(handle)
            values = net.get_node_value(handle)
            node_beliefs[name] = values

            try:
                true_prob = values[1] if values and len(values) > 1 else 0.0
                gauge = get_node_gauge(name)
                gauge.set(true_prob)
            except Exception as e:
                print(f"[WARN] Could not set gauge for node {name} in {apt}: {e}")

            handle = net.get_next_node(handle)

        results[apt] = node_beliefs

        root_node = apt_nodes.get(apt)
        if root_node:
            try:
                belief = net.get_node_value(root_node)[1]
                apt_gauges[apt].set(belief)
            except pysmile.SMILEException as e:
                print(f"[WARN] Could not read belief for {apt}: {e}")
                apt_gauges[apt].set(0.0)

    return jsonify(results)


@app.route("/inference", methods=["GET"])
def inference():
    results = {}
    for apt, net in nets.items():
        node_beliefs = {}
        handle = net.get_first_node()
        while handle >= 0:
            name = net.get_node_name(handle)
            values = net.get_node_value(handle)
            node_beliefs[name] = values
            handle = net.get_next_node(handle)
        results[apt] = node_beliefs
    return jsonify(results)


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
