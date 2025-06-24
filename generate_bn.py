import json
import pysmile
import pysmile_license
import re
import itertools

# === CONFIG ===
INPUT_FILE = "CISAIranianAPT.json"
OUTPUT_FILE = "attackflow_bn.xdsl"
DEFAULT_PRIOR = [0.9, 0.1]  # [False, True]

# === Helpers ===
def sanitize_name(name):
    name = name.replace(" ", "_").replace("-", "_")
    name = re.sub(r"[^A-Za-z0-9_]", "", name)
    if not name[0].isalpha():
        name = "N_" + name
    return name

# === Load STIX ===
with open(INPUT_FILE, "r") as f:
    data = json.load(f)

actions = {}
edges = []

for obj in data["objects"]:
    if obj["type"] == "attack-action":
        actions[obj["id"]] = obj["name"]
        for effect in obj.get("effect_refs", []):
            if effect.startswith("attack-action--"):
                edges.append((obj["id"], effect))

id_to_name = {id_: sanitize_name(name) for id_, name in actions.items()}

# === Build BN ===
net = pysmile.Network()
created_nodes = set()

# Add nodes
for stix_id, node_name in id_to_name.items():
    if node_name not in created_nodes:
        net.add_node(pysmile.NodeType.CPT, node_name)
        net.set_node_name(node_name, node_name)
        net.set_outcome_id(node_name, 0, "False")
        net.set_outcome_id(node_name, 1, "True")
        net.set_node_definition(node_name, DEFAULT_PRIOR)
        created_nodes.add(node_name)

# Add arcs
for parent_id, child_id in edges:
    parent = id_to_name.get(parent_id)
    child = id_to_name.get(child_id)
    if parent and child and parent != child:
        try:
            net.add_arc(parent, child)
        except pysmile.SMILEException as e:
            print(f"⚠️ Could not add arc from {parent} to {child}: {e}")

# Manually define CPTs
for node in created_nodes:
    parents = net.get_parents(node)
    if not parents:
        continue

    num_parents = len(parents)
    combinations = list(itertools.product(["False", "True"], repeat=num_parents))
    definition = []

    for combo in combinations:
        if "True" in combo:
            definition.extend([0.3, 0.7])  # 70% chance of True
        else:
            definition.extend([0.99, 0.01])  # Leak

    net.set_node_definition(node, definition)

# === Save File ===
net.write_file(OUTPUT_FILE)
print(f"✅ Saved Bayesian Network to {OUTPUT_FILE}")
