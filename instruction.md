# Recover the responsive layout calibration

A design-system rollout left us with an awkward production artifact: the archived CSS bundle still has its rules, but the root token values, the `@layer` declaration order, and a handful of override constants were stripped from the capture. The browser telemetry survived. We need the missing calibration back so the same layout can be reproduced for a set of unmeasured renders.

The evidence is under `/app/data`. `layout_model.md` describes how resolved layout tokens turn into painted geometry. `cascade_contract.md` describes the CSS subset represented by the extracted rules and how the capture records media/container conditions, custom properties, inheritance, `var()` fallback, specificity, cascade layers, and `!important`. The original partial measurements are in `calibration_samples.ndjson`; `identification_samples.ndjson` is a later boundary capture; `cascade_samples.ndjson` contains partial measurements from the layered build. `render_requests.ndjson` contains the cases that need final predictions. The script in `/workspace/calibrate_layout.py` is the old defaults stub from before the incident, not an answer key.

Write `/app/output/layout_calibration.json` with exactly six top-level keys: `base_tokens`, `layer_order`, `recovered_values`, `predictions`, `history_predictions`, and `flow_predictions`.

`base_tokens` must contain exactly these integer fields:

- `standard_breakpoint`
- `wide_breakpoint`
- `compact_pad`
- `standard_pad`
- `wide_pad`
- `content_cap`
- `sidebar_width`
- `card_min`
- `grid_gap`
- `card_inner_pad`
- `char_factor_milli`

`layer_order` must be an array containing every layer named in `/app/data/layer_manifest.json` exactly once, in the recovered declaration order.

`recovered_values` must contain exactly the lost-value IDs in `/app/data/lost_values.json` that do **not** begin with `base_`. Each value is an integer from that ID's documented domain. The `base_...` lost values belong in `base_tokens`, not here.



There is one more capture from the same rollout. `history_contract.md` documents the event records left by the incremental stylesheet loader; `history_sessions.json`, `history_events.ndjson`, and `history_sheets.json` hold the state history, and `history_queries.ndjson` lists historical renders that must be reconstructed. This is not a second calibration: use the same recovered base tokens, layer order, and redacted values. The work is to recover the visible stylesheet/context state for each historical query and render it with the same cascade and layout semantics.

`predictions` must contain one object for every row in `/app/data/render_requests.ndjson`. Each object must contain exactly these fields:

- `request_id`
- `content_left_milli`
- `content_width_milli`
- `main_width_milli`
- `sidebar_present`
- `columns`
- `column_width_milli`
- `header_rows`
- `header_height_milli`
- `first_card_height_milli`
- `tallest_card_height_milli`

Use the request ID from the render request. Array order is not significant.

`history_predictions` must contain one object for every row in `/app/data/history_queries.ndjson`. Each object uses `query_id` instead of `request_id` and otherwise contains the same ten rendered fields listed above. Array order is not significant.

The final trace is in `flow_cases.ndjson`. It came from a nested flex layout that consumes the same recovered style state; `flex_contract.md` defines the supported behavior. Each flow row points back to either an ordinary render request or one of the historical queries. Recover that source first, then reproduce the flex layout from the row's tree. This part intentionally uses the source's unrounded main width, not the already-painted `main_width_milli`.

`flow_predictions` must contain one object for every flow row. Each object has exactly `flow_id`, `root_line_count`, and `probes`. `probes` contains one object for every node ID listed by that row, with exactly `node_id`, `left_milli`, and `width_milli`. Probe order is not significant, and flow-row order is not significant.

The milli-valued fields use the half-up device-pixel rule described in the shipped model; they are not truncated. Do not add candidate sets, confidence values, or notes to the artifact.

You have 7200 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
