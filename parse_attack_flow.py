import json
from pathlib import Path
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt

# Load Attack Flow JSON
with open("CISAIranianAPT.json", "r") as f:
    data = json.load(f)

# Step 1: Extract attack-action nodes and their relationships
actions = {}
edges = []

for obj in data["objects"]:
    if obj["type"] == "attack-action":
        actions[obj["id"]] = {
            "name": obj.get("name", "Unnamed"),
            "description": obj.get("description", ""),
            "effects": obj.get("effect_refs", []),
        }

# Step 2: Build directed graph
G = nx.DiGraph()

for action_id, info in actions.items():
    G.add_node(action_id, label=info["name"])
    for target in info["effects"]:
        if target in actions:
            G.add_edge(action_id, target)

# Step 3: Draw the graph
plt.figure(figsize=(14, 10))
pos = nx.spring_layout(G, k=0.5)
nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'), node_size=2000, node_color="lightblue", font_size=8, font_weight='bold')
plt.title("Attack Flow - Action Dependency Graph")
plt.tight_layout()
plt.show()
