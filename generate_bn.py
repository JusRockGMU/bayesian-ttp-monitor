#!/usr/bin/env python3

import os
import json
import pysmile
import pysmile_license
import re
import itertools
import yaml

# -----------------------------
# CONFIG LOAD
# -----------------------------

CONFIG_FILE = "config.yaml"

with open(CONFIG_FILE, "r") as f:
    config = yaml.safe_load(f)

INPUT_DIR = "inputs"
OUTPUT_DIR = "xdsl_files"
DEFAULT_PRIOR = config["default_prior"]
TRUE_PROB = config["influence_true_prob"]
FALSE_PROB = config["influence_false_prob"]
MODEL = config["model"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# HELPERS
# -----------------------------

def sanitize_name(name):
    name = name.replace(" ", "_")
    name = name.replace("-", "_")
    name = name.replace("(", "_").replace(")", "_")
    name = re.sub(r"[^A-Za-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    if not name or not name[0].isalpha():
        name = "N_" + name
    return name

def build_noisy_or_cpt(num_parents, true_prob, false_prob):
    combinations = list(itertools.product(["False", "True"], repeat=num_parents))
    definition = []
    for combo in combinations:
        if "True" in combo:
            definition.extend([1 - true_prob, true_prob])
        else:
            definition.extend([1 - false_prob, false_prob])
    return definition

def build_naive_bayes_cpt(num_parents, true_prob, false_prob):
    combinations = list(itertools.product(["False", "True"], repeat=num_parents))
    definition = []
    for combo in combinations:
        true_count = combo.count("True")
        prob = false_prob + (true_prob - false_prob) * (true_count / num_parents if num_parents > 0 else 0)
        definition.extend([1 - prob, prob])
    return definition

def traverse_attack_flow(start_id, objects_dict, visited, nodes, edges, allowed_types):
    if start_id in visited:
        return

    visited.add(start_id)
    obj = objects_dict.get(start_id)
    if obj is None:
        return

    if obj["type"] in allowed_types:
        obj_name = obj.get("name", obj["id"])
        clean_name = sanitize_name(obj_name)[:30]
        type_name = sanitize_name(obj["type"])
        stix_id = obj["id"].split("--")[-1][:8] if "--" in obj["id"] else obj["id"][:8]
        node_name = f"{clean_name}_{type_name}_{stix_id}"

        nodes[start_id] = node_name

        if obj["type"] == "attack-action":
            for child_id in obj.get("effect_refs", []):
                edges.append((start_id, child_id))
                traverse_attack_flow(child_id, objects_dict, visited, nodes, edges, allowed_types)

def process_json_file(filepath, output_path, apt_name):
    apt_root_node = f"{apt_name}Occurred"

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    objects_dict = {}
    for obj in data.get("objects", []):
        if "id" in obj:
            objects_dict[obj["id"]] = obj

    allowed_types = [
        "attack-action",
        "attack-condition",
        "attack-operator",
        "attack-object"
    ]

    attack_flows = [
        obj for obj in data.get("objects", [])
        if obj.get("type") == "attack-flow"
    ]

    if not attack_flows:
        print(f"[WARN] No attack-flow found in {os.path.basename(filepath)}")
        return

    nodes = {}
    edges = []
    visited = set()
    start_nodes = set()

    for flow in attack_flows:
        for start_id in flow.get("start_refs", []):
            traverse_attack_flow(start_id, objects_dict, visited, nodes, edges, allowed_types)
            start_nodes.add(start_id)

    if not nodes:
        print(f"[WARN] No relevant nodes found in {os.path.basename(filepath)}")
        return

    net = pysmile.Network()

    # Create APT-level root node
    apt_handle = net.add_node(pysmile.NodeType.CPT, apt_root_node)
    net.set_node_name(apt_handle, apt_root_node)
    net.set_outcome_id(apt_root_node, 0, "False")
    net.set_outcome_id(apt_root_node, 1, "True")
    net.set_node_definition(apt_root_node, DEFAULT_PRIOR)

    node_handles = {}

    for stix_id, node_name in nodes.items():
        if node_name not in node_handles:
            handle = net.add_node(pysmile.NodeType.CPT, node_name)
            net.set_node_name(handle, node_name)
            net.set_outcome_id(node_name, 0, "False")
            net.set_outcome_id(node_name, 1, "True")
            net.set_node_definition(node_name, DEFAULT_PRIOR)
            node_handles[node_name] = handle

    for start_id in start_nodes:
        child_name = nodes.get(start_id)
        if not child_name:
            continue
        try:
            net.add_arc(apt_root_node, child_name)
        except pysmile.SMILEException as e:
            print(f"[WARN] Could not add arc from APT root to {child_name}: {e}")

    for parent_id, child_id in edges:
        parent_name = nodes.get(parent_id)
        child_name = nodes.get(child_id)

        if not parent_name or not child_name:
            print(f"[SKIP] Arc skipped because node missing: {parent_id} → {child_id}")
            continue

        if parent_name == child_name:
            print(f"[SKIP] Skipped self-loop arc for {parent_name}")
            continue

        try:
            net.add_arc(parent_name, child_name)
        except pysmile.SMILEException as e:
            print(f"[WARN] Could not add arc from {parent_name} to {child_name}: {e}")

    # ✅ Update the Occurred node CPT
    parents_of_occurred = net.get_parents(apt_root_node)
    num_parents = len(parents_of_occurred)
    if num_parents > 0:
        if MODEL == "noisy_or":
            definition = build_noisy_or_cpt(num_parents, TRUE_PROB, FALSE_PROB)
        elif MODEL == "naive_bayes":
            definition = build_naive_bayes_cpt(num_parents, TRUE_PROB, FALSE_PROB)
        else:
            definition = build_noisy_or_cpt(num_parents, TRUE_PROB, FALSE_PROB)
        net.set_node_definition(apt_root_node, definition)
        print(f"[INFO] Updated CPT for {apt_root_node} with {num_parents} parent(s).")
    else:
        print(f"[INFO] No parents found for {apt_root_node}, keeping default prior.")

    # ✅ Update all other nodes only if they have parents
    all_nodes = list(node_handles.keys())
    for node_name in all_nodes:
        parents = net.get_parents(node_name)
        if not parents:
            continue
        num_parents = len(parents)
        if MODEL == "noisy_or":
            definition = build_noisy_or_cpt(num_parents, TRUE_PROB, FALSE_PROB)
        elif MODEL == "naive_bayes":
            definition = build_naive_bayes_cpt(num_parents, TRUE_PROB, FALSE_PROB)
        else:
            definition = build_noisy_or_cpt(num_parents, TRUE_PROB, FALSE_PROB)
        net.set_node_definition(node_name, definition)

    net.write_file(output_path)
    print(f"[SUCCESS] Saved BN to {output_path}")

def main():
    json_files = [
        f for f in os.listdir(INPUT_DIR)
        if f.endswith(".json")
    ]

    if not json_files:
        print("[WARN] No JSON files found.")
        return

    for json_file in json_files:
        apt_name = json_file.replace(".json", "")
        clean_apt_name = sanitize_name(apt_name)
        json_path = os.path.join(INPUT_DIR, json_file)
        xdsl_path = os.path.join(OUTPUT_DIR, f"{clean_apt_name}.xdsl")

        if os.path.exists(xdsl_path):
            print(f"[INFO] Overwriting existing {xdsl_path}")

        try:
            process_json_file(json_path, xdsl_path, clean_apt_name)
        except Exception as e:
            print(f"[ERROR] Failed for {json_file}: {e}")

if __name__ == "__main__":
    main()
