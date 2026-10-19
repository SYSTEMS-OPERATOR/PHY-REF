#!/usr/bin/env python3
"""Validate the pending packet and optional Studio preview draft, offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phy_ref.glb import strict_json
from phy_ref.landmarks import load_packet, validate_draft

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path)
    args = parser.parse_args()
    packet = load_packet(ROOT)
    result = validate_draft(ROOT, strict_json(args.draft.read_text())) if args.draft else {
        "packet_id": packet["packet_id"], "status": packet["status"],
        "accepted_landmarks": None, "fabrication_released": False}
    print(json.dumps(result, indent=2, allow_nan=False))
