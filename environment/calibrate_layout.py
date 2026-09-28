#!/usr/bin/env python3
import json
from pathlib import Path

# This was the temporary defaults file used before telemetry calibration.
TOKENS = {
    "standard_breakpoint": 768,
    "wide_breakpoint": 1200,
    "compact_pad": 16,
    "standard_pad": 24,
    "wide_pad": 32,
    "content_cap": 1200,
    "sidebar_width": 280,
    "card_min": 240,
    "grid_gap": 20,
    "card_inner_pad": 16,
    "char_factor_milli": 550,
}

if __name__ == "__main__":
    out = {"tokens": TOKENS, "predictions": []}
    Path("/app/output/layout_calibration.json").write_text(json.dumps(out, indent=2) + "\n")
