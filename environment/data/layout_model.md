# Layout model used by the telemetry collector

The measurements came from one responsive card page. The collector rounded painted geometry to device pixels, but the layout decisions were made in CSS pixels before that rounding. Eleven integer design tokens feed this model. In the base capture their root values are missing; in layered cases the effective values are custom properties resolved under `cascade_contract.md`. The equations below are fixed once those effective token values are known.

The missing tokens are named `standard_breakpoint`, `wide_breakpoint`, `compact_pad`, `standard_pad`, `wide_pad`, `content_cap`, `sidebar_width`, `card_min`, `grid_gap`, `card_inner_pad`, and `char_factor_milli`.

For a case, first compute `usable = viewport_width - safe_left - safe_right - scrollbar_width`. The page is compact when `usable < standard_breakpoint`, standard when it is at least that value but below `wide_breakpoint`, and wide otherwise. The horizontal pad is the matching pad token. Let `raw = usable - 2*pad`; the content width is `min(content_cap, raw)`, and any width left over because of the cap is split evenly outside the content. The content's left edge therefore begins at `safe_left + pad + max(0, (raw-content_cap)/2)`.

Wide mode has a sidebar. Its width is `sidebar_width`, followed by a fixed 23px gap. Compact and standard modes have no sidebar. The remaining width is the main column. Cards use at most four equal columns. The number of columns is the largest integer from 1 through 4 for which each column can be at least `card_min` with `grid_gap` between neighboring columns. All card widths are computed from the unrounded main width.

Navigation uses the same glyph calibration as card text. Set `scale = text_scale_percent/100` and `char_width = 15*scale*char_factor_milli/1000`. A nav item whose label has `c` characters consumes `c*char_width + 20` CSS pixels. Items are placed left to right into `content_width - 248` pixels, with a 12px gap before every item except the first in a row. If the next item does not fit, start another row. The header height is `40 + max(32, rows*(22*scale) + (rows-1)*6)`.

Card text uses `14*scale` px body text and `18*scale` px title text. The available text width is `column_width - 2*card_inner_pad`. Body characters use `font_size*char_factor_milli/1000` pixels each. Title characters use `font_size*(char_factor_milli-17)/1000`. Characters-per-line is the floor of available width divided by that character width, with a minimum of one. Lines are the ceiling of character count divided by characters-per-line. A card's CSS height is `2*card_inner_pad + title_lines*(23*scale) + 8 + body_lines*(20*scale) + meta_rows*18 + 10`.

Finally, painted scalar geometry is rounded half-up to the nearest device pixel: multiply CSS pixels by `dpr_num/dpr_den`, round `.5` upward, then convert back to CSS pixels. The telemetry stores those painted values multiplied by 1000 as integers. Boolean and count fields are not rounded.

The base calibration file contains cases plus only some measurements from each case. The later identification capture adds boundary cases. Layered samples and render requests resolve their effective token values through the cascade evidence before applying this model.
