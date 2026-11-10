from __future__ import annotations

import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


root = Path(__file__).resolve().parent
tree_path = root / (sys.argv[1] if len(sys.argv) > 1 else "window-after-update.xml")
tree = ET.parse(tree_path).getroot()
clickable = [node for node in tree.iter("node") if node.attrib.get("clickable") == "true"]
update = next(
    (node for node in clickable if "Перезапустить" in node.attrib.get("text", "")),
    None,
)
bounds = update.attrib.get("bounds", "") if update is not None else ""
coordinates = None
if bounds:
    numbers = [int(value) for value in __import__("re").findall(r"\d+", bounds)]
    if len(numbers) == 4:
        coordinates = [(numbers[0] + numbers[2]) // 2, (numbers[1] + numbers[3]) // 2]

result = {
    "tree_file": tree_path.name,
    "tree_node_count": sum(1 for _ in tree.iter("node")),
    "clickable_nodes": len(clickable),
    "unnamed_clickable_nodes": sum(
        not (node.attrib.get("text", "").strip() or node.attrib.get("content-desc", "").strip())
        for node in clickable
    ),
    "update_action_present": update is not None,
    "update_action_bounds": bounds or None,
    "update_action_center": coordinates,
}
(root / "ui-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=True, indent=2))
