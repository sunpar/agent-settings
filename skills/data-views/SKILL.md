---
name: data-views
description: Use when building, restyling, or reviewing a table, data grid, list view, or data-dense dashboard panel in any stack (HTML/CSS, React, grid libraries such as TanStack Table, AG Grid, or MUI DataGrid). Covers width, borders, row striping, alignment, number formatting, ordering, and emphasis. For charts, use the dataviz skill.
---

# Data Views

These are the table details Claude tends to skip or get wrong. They follow Edward Tufte's principles from *The Visual Display of Quantitative Information* and *Beautiful Evidence*: show the data, make most of the ink carry data, erase ink that carries none, and separate things with the lightest mark that works.

Each item gives the rule, when it applies, and how to check it. Check every item before calling a data view done. To add an item, put it in the section it belongs to and write it the same way.

## Width

- **Fit to content**: use `width: auto` with `max-width: 100%`, and wrap wide tables in a container with `overflow-x: auto`. `width: 100%` spreads the spare width across every column, so a 3-character code column grows to hundreds of pixels and the eye has to cross empty space to read a row.
- **Filling the container**: when the table has to fill its container (to line up with a card or the page grid), give all the spare width to one column. Use the main text column, or an empty last column with `width: 100%`. Without one column taking the spare width, the browser stretches the others past any cap you set inside them.
- **Cap free-text columns**: set the cap on an element inside the cell, such as `<td><div style="max-width: 32ch">`. Let the text wrap, or truncate it with an ellipsis and show the full text in a `title` or tooltip. Don't put `max-width` on the `td`: CSS leaves it undefined for table cells, and Chromium ignores it once the table is `width: 100%` (a cell capped at 100 px rendered 1244 px wide).
- **Grid libraries**: let at most one column flex. Size the others to their content or give them fixed widths.
- **Check**: render at about 1920 px wide and at the narrowest width you support. At 1920 px, no column should have a wide empty gap between its content and the next column. At the narrowest width, the table should scroll inside its container instead of squeezing the columns or widening the page.

## Borders and decoration

- **No vertical rules**: alignment and padding already separate columns.
- **Horizontal rules where structure changes**: draw them above the header, below the header, and below the last row (the "booktabs" style). Separate row groups with extra space or one light rule, not a border on every cell.
- **No decoration without meaning**: no outer box, heavy header fill, shadow, icon, or color that doesn't stand for something.
- **Check**: take away each border, fill, and color one at a time. If the table reads as well without it, leave it out.

## Row striping

- **When to stripe**: stripe rows when the eye has to follow a row across, as in tables with many columns, wide rows, or many rows. Don't stripe tables with a few rows or a few narrow columns; there the stripes add noise without helping anyone read.
- **Stripes replace gridlines**: use stripes instead of row gridlines, never both.
- **Faint stripes**: make the stripe color barely different from the background, and define it for both light and dark themes.
- **Hover and selection**: hovered and selected rows must still look different from striped rows.
- **Stripe by data position**: in virtualized grids and tables with grouped or expandable rows, stripe by the row's position in the data, not with `:nth-child`. Virtualized grids reuse row elements, and expanded child rows shift which rows count as odd or even.
- **Check**: look at the table in both themes with one row hovered and one selected. The stripe should be the faintest of the three.

## Alignment and numbers

- **Alignment**: right-align numbers and left-align text. Align each header the same way as its column, so number headers are right-aligned too.
- **Tabular figures**: use `font-variant-numeric: tabular-nums` so digits line up from row to row.
- **Consistent precision**: use the same number of decimal places down a column. Choose it for the decision the reader is making, not from whatever precision the source data has.
- **Units in the header**: put units and scale in the header, as in "Revenue ($M)", instead of repeating them in every cell.
- **Negative numbers**: show them with a minus sign, or with parentheses in financial tables. Don't rely on red alone.
- **Zero versus missing**: keep them apart. Say why a value is missing (for example "n/a" or "pending" in muted text) instead of leaving the cell blank or showing a lone dash.
- **Check**: scan one numeric column from top to bottom. The decimal points should line up and the precision should never change.

## Order and emphasis

- **Default sort**: sort by what the reader came to find, such as the largest value or the most recent date. Use alphabetical order only when people look rows up by name.
- **Sparing emphasis**: bold or color only the cells that need attention; when everything is highlighted, nothing stands out.
- **Sparklines for trends**: show a per-row trend with a sparkline (Tufte's small, word-sized line chart) instead of a run of number columns. Style it with the dataviz skill.
