# Trace Route UX Improvement TODO

## Pass 1
- [x] Update `templates/index.html` trace-node card markup for landmark + placeholder support.
- [x] Refactor trace-route script:
  - [x] 4-second auto pause per node
  - [x] manual Next as skip
  - [x] adaptive zoom/speed by segment distance
  - [x] reverse-geocode nearest place with caching
  - [x] landmark distance text formatting
- [x] Update `static/styles.css` for new card elements and placeholder styling.

## Pass 2 (current)
- [x] Anchor photo card above active node.
- [x] Replace buggy zoom with stable per-segment distance-based zoom.
- [x] Follow trail head smoothly during movement.
- [x] Keep 4-second node pause with anchored card updates.
- [x] Restart local server for user validation.

## Pass 3 (current)
- [x] Make camera continuously follow trace head (no jump to next node).
- [x] Keep variable speed and variable zoom by segment distance.
- [x] Remove Next/skip behavior and enforce autoplay with 4-second stop at each node.
- [x] Keep node card anchored above active node with photo/placeholder and nearest landmark.
- [x] Performance pass: reduce trace camera/zoom jank and FPS drops.
- [x] Replace default Folium popup/tooltip behavior with trace photo cards on marker click.
- [x] Restart local server.
- [x] Run quick API sanity checks.
- [x] Finalize and summarize changes.

## Pass 4 (current)
- [x] Add real photo timeline panel with trip stats.
- [x] Add export/share mode for HTML, GeoJSON, GPX, and copy link.
- [x] Improve trace storytelling with progress HUD and speed controls.
- [x] Upgrade photo popups with prev/next controls and lightbox view.
- [x] Fix visible text encoding issues in runtime UI.
- [x] Replace default Folium marker visuals with numbered photo pins.
- [x] Improve mobile map, popup, controls, and timeline layout.
