# Using SVG to STL Web

This guide explains how the two output modes interpret SVG paths, how to
prepare artwork, and how each setting affects the resulting STL.

## Choose an output mode

### Stencil

Stencil mode creates a rectangular plate around the artwork. Every closed SVG
path becomes an opening through that plate.

Use this mode for paint masks, craft stencils, templates, and signs where the
artwork should be empty space.

The requested artwork height applies to the SVG contours. The outer border is
added afterward, so the final plate height is:

```text
artwork height + (2 x outer border)
```

For example, an 80 mm artwork height with a 10 mm border creates a plate that
is 100 mm high.

### SVG shape

SVG shape mode extrudes each closed path as solid material. The border control
is disabled because this mode has no surrounding plate.

Use this mode for flat signs, badges, tokens, ornaments, or other objects whose
outline should match the artwork. Several paths produce several disconnected
solids in the same STL. A slicer may present those as one imported object with
multiple parts.

## Settings

| Setting | Range | Effect |
| --- | ---: | --- |
| Artwork height | 5-1000 mm | Scales all contours together while preserving aspect ratio |
| Plate thickness | 0.4-50 mm | Extrusion depth along the STL Z axis |
| Outer border | 0-200 mm | Material added on every side in stencil mode only |
| Curve detail | 3-48 | Samples per SVG curve or arc segment |

Higher curve detail creates smoother arcs but also increases conversion time,
triangle count, memory use, and STL size. Straight line segments are preserved
without extra sampling.

## Preparing an SVG

The converter reads SVG path commands, not the rendered picture. Before
uploading:

1. Convert text to paths.
2. Convert shapes such as rectangles, circles, ellipses, and polygons to paths.
3. Apply or bake transforms into the path coordinates.
4. Close every contour that should become geometry.
5. Remove clipping masks, strokes used as artwork, duplicate paths, and hidden
   construction geometry.
6. Save as a plain SVG when your editor offers that option.

In Inkscape, **Path > Object to Path** converts selected text and primitives.
Use **Path > Stroke to Path** when a visible stroke must become a filled shape.
The exact menu names can vary between editor versions.

## Supported path data

The parser supports the segment types provided by the `svg.path` package,
including lines, Bezier curves, and arcs. A contour is accepted only when its
path data contains an explicit close command (`Z` or `z`).

The following SVG features are not currently interpreted:

- transform attributes on paths or parent groups;
- fill rules such as `evenodd` and `nonzero`;
- nested holes or islands;
- stroke width;
- clipping and masking;
- open paths;
- self-intersecting paths;
- non-path elements such as `<text>`, `<circle>`, and `<rect>`.

### Nested artwork

Do not use one path inside another to describe a letter such as `O` or a ring.
The current converter does not infer containment or fill rules.

In stencil mode, every contour is submitted as a hole in the plate. In SVG
shape mode, every contour is submitted as a filled solid. Prepare the artwork
as independent, non-overlapping closed contours that match the chosen mode.

## Reading the result

### Preview controls

After choosing an SVG, use the buttons above the preview or interact with the
artwork directly:

- scroll over the SVG or use **+** and **−** to zoom;
- drag the SVG to pan, and select **Fit** to restore the initial view;
- after a successful conversion, select **STL** to switch to the generated
  three-dimensional mesh;
- drag the STL to rotate it, right-drag to pan it, and scroll to zoom it;
- use **SVG** and **STL** to move between the source and generated previews.

The STL viewer runs entirely in the browser from files bundled with the
application. It does not upload the STL again or contact an external service.
If WebGL is unavailable, the validated STL can still be downloaded and opened
in a slicer.

### Validation results

The result panel shows:

- **Size:** STL width, height, and thickness in millimetres.
- **Triangles:** number of faces in the exported mesh.
- **Watertight:** every mesh edge belongs to exactly two faces.
- **Winding:** adjacent faces use a consistent orientation.

The server downloads an STL only after all printability checks pass. It also
requires a positive enclosed volume, no boundary or non-manifold edges, and no
degenerate or duplicate triangles.

These checks catch the inconsistent face-orientation problem that caused older
outputs to slice incorrectly. They cannot determine whether the chosen artwork
is practical to print. Always inspect thin bridges, isolated pieces, minimum
feature sizes, and bed placement in the slicer.

## Example

[`examples/simple_shapes.svg`](../examples/simple_shapes.svg) contains a closed
circle path and a closed triangle path. It deliberately avoids personal or
branded artwork.

- Stencil mode creates one rectangular plate with two openings.
- SVG shape mode creates a circular solid and a triangular solid in one STL.

