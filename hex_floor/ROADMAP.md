# Hex Floor Layout Roadmap

This roadmap collects potential improvements beyond the current polygon, grout,
doorway, orientation, and aesthetic-scoring features.

## Recommended sequence

1. Exact polygon clipping and cut geometry
2. Interactive floor and feature editor
3. Fixture, doorway, and sightline modeling
4. True offcut nesting and purchasing optimization
5. Contractor-oriented exports and installation planning

Exact geometry is the foundation: reliable cut shapes and retained areas improve
sliver detection, material estimates, offcut reuse, reports, and visual scoring.

## 1. Exact edge-piece geometry

- Replace sampled retained-area estimates with true polygon clipping.
- Calculate exact cut polygons, dimensions, and retained percentages.
- Detect edge slivers from actual geometry.
- Produce printable templates for complex cuts.
- Consider using Shapely for robust polygon intersection and offset operations.

## 2. Real offcut nesting

- Match an offcut from one perimeter tile to compatible cuts elsewhere.
- Respect tile color, orientation, shape, and surface direction.
- Include blade kerf, handling clearance, and breakage allowance.
- Distinguish guaranteed reuse from theoretical area savings.
- Produce a numbered cutting and reuse schedule.

## 3. Interactive layout viewer

- Draw, resize, and drag floor polygon vertices in a browser interface.
- Mark doorways, cabinets, drains, fixtures, and other constraints visually.
- Switch between pointy- and flat-top orientations.
- Move the tile grid interactively or lock its offset.
- Compare ranked layouts side by side.
- Inspect tile color, coordinates, retained area, and cuts by selecting a tile.

## 4. Doorways and sightlines

- Model door swing, opening width, threshold depth, and transition material.
- Support multiple doorways with explicit priorities.
- Record the primary viewing direction and long sightlines from adjacent rooms.
- Allow hard constraints for a centered tile or centered grout joint.
- Score symmetry across doorway jambs and other prominent openings.

## 5. Fixtures, drains, and penetrations

- Model toilets, vanities, tubs, cabinets, registers, pipes, and floor drains.
- Distinguish concealed areas from visible obstructions.
- Prefer visually centered drain and penetration placement where appropriate.
- Detect fragile notches and narrow U-shaped cuts.
- Penalize cuts too close to tile corners.

## 6. Installation constraints

- Configure minimum edge-piece width and retained-area thresholds.
- Configure minimum clearance between a cut and a tile corner.
- Model perimeter and field movement joints accurately.
- Select a preferred starting wall and installation direction.
- Generate reference lines and initial layout measurements.
- Support tile rotation or directional-pattern restrictions.

## 7. Purchasing and inventory

- Accept pack sizes and available quantities for each color.
- Track tiles already owned and reusable leftovers.
- Apply configurable waste, breakage, and dye-lot reserve percentages.
- Recommend purchase quantities by product and color.
- Include inventory feasibility in layout scoring.

## 8. Contractor-oriented outputs

- Generate a dimensioned PDF plan.
- Export SVG or DXF geometry.
- Produce a numbered tile map and perimeter cut schedule.
- Produce material orders and an installation sequence.
- Generate full-scale paper templates for complex edge pieces.

## 9. Multiple regions and holes

- Support interior polygon holes, columns, and structural penetrations.
- Model shower curbs, islands, and floor drains.
- Support multiple connected rooms and disconnected tiled regions.
- Accept GeoJSON MultiPolygon input where appropriate.

## 10. Reproducible project files

- Version the project-file schema.
- Store geometry, tile dimensions, grout, fixtures, inventory, and solver settings.
- Record the selected candidate, color seed, and report metadata.
- Preserve enough information to regenerate historical layouts after upgrades.

## Current estimation caveat

The current cut report estimates retained area by sampling points within each tile,
and its offcut-reuse figure is area-based. It is useful for comparing layouts but
is not a guaranteed cutting plan. Exact clipping and nesting should replace these
estimates before they are used for purchasing or fabrication decisions.
