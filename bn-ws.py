from flask import Flask, request, jsonify
from prometheus_client import Gauge, generate_latest
from pysmile import Network
import pysmile_license  # 💡 Activate license BEFORE using Network()

import threading

app = Flask(__name__)
prob_gauges = {}
lock = threading.Lock()

# === Load BN ===
net = Network()
net.read_file("attackflow_bn.xdsl")

# === Gauge Update Helper ===
def update_gauges():
    with lock:
        for node_id in net.get_all_nodes():
            tid = net.get_node_name(node_id)
            try:
                p_true = net.get_node_value(node_id)[1]  # [False, True]
                if tid not in prob_gauges:
                    metric_name = f"bn_{tid}"
                    prob_gauges[tid] = Gauge(metric_name, f"Probability of technique {tid}")
                prob_gauges[tid].set(p_true)
            except Exception as e:
                print(f"⚠️ Failed to update gauge for {tid}: {e}")

# === Routes ===

@app.route("/evidence", methods=["POST"])
def set_evidence():
    data = request.json
    evidence = data.get("evidence", [])

    net.clear_all_evidence()
    for tid in evidence:
        try:
            net.set_evidence(tid, "True")
        except Exception as e:
            print(f"⚠️ Failed to set evidence for {tid}: {e}")
    net.update_beliefs()
    update_gauges()
    return jsonify({"message": "✅ Evidence updated", "evidence": evidence})

@app.route("/nodes", methods=["GET"])
def get_nodes():
    beliefs = {}
    for node_id in net.get_all_nodes():
        tid = net.get_node_name(node_id)
        try:
            prob = net.get_node_value(node_id)[1]
            beliefs[tid] = round(prob, 4)
        except Exception:
            beliefs[tid] = None
    return jsonify(beliefs)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain'}

# === Start Server ===
if __name__ == "__main__":
    net.update_beliefs()
    update_gauges()
    app.run(host="0.0.0.0", port=8000)
