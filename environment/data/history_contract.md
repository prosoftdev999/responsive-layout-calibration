# Incremental stylesheet history capture

The final part of the incident came from an incremental stylesheet loader. The files `history_sessions.json`, `history_events.ndjson`, `history_sheets.json`, and `history_queries.ndjson` are the surviving capture.

A session is an event stream. `session-01` starts from its `base_context` and no adopted hotfix sheets. Every other session names a `parent_session` and `fork_seq`; it starts from the parent's **visible** state immediately after that sequence. Session ancestry is acyclic. A child does not inherit an unfinished batch from its parent. The child's own `base_context` is retained as capture metadata but does not replace inherited categorical state.

Events are ordered by integer `seq`. A query at sequence `q` sees committed effects from events with `seq <= q` in that session. `set_context` changes one categorical context field. `adopt` appends a sheet if it is not already adopted. `remove` removes it if present. `move` removes an adopted sheet and reinserts it at the requested zero-based index after clamping that index to the current list length; moving a sheet that is not adopted is a no-op.

`begin` opens one atomic batch. Until the matching `commit`, the enclosed mutations are buffered and invisible to queries and descendants. `commit` applies them in recorded order. `abort` discards them. Batches do not nest and IDs match within a session.

Each hotfix sheet contributes declarations directly to the `cards` node. Its `layer` and declaration `important` flag participate in the same cascade described by `cascade_contract.md`. Hotfix declarations have the same selector specificity as `.cards`. Within a layer and importance class, hotfix source order follows the current adopted-sheet order and comes after the archived static rules. The usual reversed layer priority for `!important` still applies. The hotfix declarations contain literal integer values only.

For a history query, reconstruct the visible session state at the query sequence (including ancestry), begin with the query's `seed_context` for its numeric viewport/container fields, replace its categorical context fields with the reconstructed values, append the currently adopted hotfix declarations to the archived cascade, resolve the eleven effective tokens, and then evaluate the query's `case` with `layout_model.md`. Viewport/container conditions continue to use the context values carried by the query; history events do not change numeric viewport/container fields.
