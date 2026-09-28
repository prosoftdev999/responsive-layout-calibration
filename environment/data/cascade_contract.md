# Cascade evidence contract

The CSS extraction is synthetic, but its semantics follow the author-origin parts of the CSS cascade used by this incident. `cascade_rules.ndjson` contains rules from seven named cascade layers. `layer_manifest.json` preserves the layer names but not their declaration order. Values written as `lost:<id>` were redacted in the extraction; `lost_values.json` gives the admissible integer domain for each redaction.

Each cascade sample and render request has a `context` and a layout `case`. The target node is `cards`. Start from the fixed tree in `style_nodes.json`; apply the context by setting `data-density` and `data-tenant` on `app`, `data-mode` on `shell`, `data-exp` on `cards`, and adding class `rtl` to `root` when `direction` is `rtl`.

The selector grammar in this capture is deliberately small: `:root`, class selectors, equality attribute selectors such as `[data-exp="beta"]`, compounds of those forms, and descendant combinators separated by spaces. Standard specificity applies within that grammar: each class, attribute, or `:root` contributes one class-level specificity component.

All declarations are author origin. Normal declarations in later cascade layers outrank normal declarations in earlier layers. For `!important` declarations that layer order is reversed: important declarations in earlier layers outrank important declarations in later layers. Importance is considered before layer order; specificity is considered after layer order; `source_order` breaks any remaining tie. Custom properties inherit normally. A declaration value may be an integer, `lost:<id>`, or a JSON object of the form `{"var":"--name","fallback":17}`. Resolve `var()` from the cascaded custom-property value, using the fallback only when the referenced property is absent.

A rule's `when` object may contain `build_in`, `min_viewport`, `max_viewport`, `min_container`, or `max_container`. Bounds are inclusive. Viewport bounds use `context.viewport_width`; container bounds use `context.container_width`. Missing conditions impose no restriction.

The eleven layout properties are the custom properties named by the token fields in `layout_model.md`, with a `--` prefix. Resolve them on the `cards` node, convert the resulting values to integers, and feed those values into the layout model. Painted milli-values use the half-up device-pixel rule in `layout_model.md`; do not truncate them.

`calibration_samples.ndjson` is the original partial telemetry from the base context. `identification_samples.ndjson` is a later capture around branch boundaries and sensitive wrapping widths. `cascade_samples.ndjson` contains partial measurements from the layered build. Every supplied measurement is authoritative. The same lost values and one layer order apply to the whole capture.
