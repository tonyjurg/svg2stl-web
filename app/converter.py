"""Geometry conversion and print-oriented STL validation.

Closed SVG paths can either become holes in a surrounding stencil plate or be
extruded as the artwork itself. OpenCASCADE volumes give Gmsh a known inside
and outside before the STL is written.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import gmsh
import numpy as np
import trimesh
from defusedxml import minidom
from svg.path import Close, Line, Move, parse_path


@dataclass(frozen=True)
class MeshReport:
    """Mesh properties needed to decide whether a slicer can identify a solid."""

    vertices: int
    faces: int
    boundary_edges: int
    non_manifold_edges: int
    degenerate_faces: int
    duplicate_faces: int
    watertight: bool
    winding_consistent: bool
    is_volume: bool
    signed_volume: float
    extents: tuple[float, float, float]

    @property
    def printable(self) -> bool:
        """Return whether the mesh passes every printing check used here."""
        return (
            self.watertight
            and self.winding_consistent
            and self.is_volume
            and self.boundary_edges == 0
            and self.non_manifold_edges == 0
            and self.degenerate_faces == 0
            and self.duplicate_faces == 0
            and self.signed_volume > 0
        )


def _same_point(a, b, atol=1e-9):
    return bool(np.allclose(a, b, atol=atol, rtol=0))


def _finish_contour(points):
    cleaned = []
    for point in points:
        if not cleaned or not _same_point(cleaned[-1], point):
            cleaned.append(point)

    # Gmsh closes the wire itself. Retaining the repeated SVG start point would
    # add a zero-length final edge and can make a curve loop invalid.
    while len(cleaned) > 1 and _same_point(cleaned[0], cleaned[-1]):
        cleaned.pop()

    return np.asarray(cleaned, dtype=float) if len(cleaned) >= 3 else None


def parse_svg_contours(svg_path, definition=12):
    """Read all usable explicitly closed ``path`` contours from an SVG."""
    if definition < 1:
        raise ValueError("Curve detail must be at least 1")

    document = minidom.parse(str(svg_path))
    try:
        root = document.documentElement
        if root.localName != "svg":
            raise ValueError("The uploaded document is not an SVG")
        path_data = [
            node.getAttribute("d")
            for node in document.getElementsByTagName("path")
            if node.getAttribute("d").strip()
        ]
    finally:
        document.unlink()

    if not path_data:
        raise ValueError("No SVG path with drawing data was found")

    contours = []
    for data in path_data:
        points = []
        for segment in parse_path(data):
            if isinstance(segment, Move):
                points = [[segment.end.real, segment.end.imag]]
                continue

            # Lines already have an exact endpoint. Curves and arcs must be
            # sampled because STL contains triangles rather than vector curves.
            samples = 1 if isinstance(segment, (Line, Close)) else definition
            for t in np.linspace(0.0, 1.0, samples + 1)[1:]:
                point = segment.point(float(t))
                points.append([point.real, point.imag])

            if isinstance(segment, Close):
                contour = _finish_contour(points)
                if contour is not None:
                    contours.append(contour)
                points = []

    if not contours:
        raise ValueError("No usable closed SVG contours were found")
    return contours


def analyze_stl(stl_path, degenerate_threshold=1e-8):
    """Inspect an STL for topology and orientation defects that affect slicing."""
    # Processing merges STL's repeated triangle coordinates into shared vertex
    # IDs, which makes edge ownership and adjacency checks meaningful.
    mesh = trimesh.load_mesh(stl_path, process=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError("The conversion did not produce one triangulated mesh")

    edge_counts = np.bincount(mesh.edges_unique_inverse)
    sorted_faces = np.sort(mesh.faces, axis=1)
    _, face_counts = np.unique(sorted_faces, axis=0, return_counts=True)

    return MeshReport(
        vertices=len(mesh.vertices),
        faces=len(mesh.faces),
        boundary_edges=int(np.count_nonzero(edge_counts == 1)),
        non_manifold_edges=int(np.count_nonzero(edge_counts > 2)),
        degenerate_faces=int(
            np.count_nonzero(mesh.area_faces < float(degenerate_threshold))
        ),
        duplicate_faces=int(np.sum(np.maximum(face_counts - 1, 0))),
        watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),
        is_volume=bool(mesh.is_volume),
        signed_volume=float(mesh.volume),
        extents=tuple(float(value) for value in mesh.extents),
    )


def validate_stl(stl_path):
    """Return the mesh report or explain why the generated STL is unsafe."""
    report = analyze_stl(stl_path)
    if report.printable:
        return report

    failures = [
        f"{name}={getattr(report, name)}"
        for name in ("watertight", "winding_consistent", "is_volume")
        if not getattr(report, name)
    ]
    failures.extend(
        f"{name}={getattr(report, name)}"
        for name in (
            "boundary_edges",
            "non_manifold_edges",
            "degenerate_faces",
            "duplicate_faces",
        )
        if getattr(report, name) != 0
    )
    if report.signed_volume <= 0:
        failures.append(f"signed_volume={report.signed_volume}")
    raise ValueError("STL validation failed: " + ", ".join(failures))


def convert_svg_to_stl(
    svg_path,
    output_path,
    *,
    thickness_mm=3.0,
    height_mm=80.0,
    border_mm=10.0,
    definition=12,
    output_mode="stencil",
):
    """Convert closed SVG contours into a validated stencil or shape in mm."""
    svg_path = Path(svg_path)
    output_path = Path(output_path)
    if not svg_path.is_file():
        raise FileNotFoundError(svg_path)
    if thickness_mm <= 0 or height_mm <= 0:
        raise ValueError("Height and thickness must be greater than zero")
    if border_mm < 0:
        raise ValueError("Border cannot be negative")
    if output_mode not in {"stencil", "shape"}:
        raise ValueError("Output mode must be 'stencil' or 'shape'")

    contours = parse_svg_contours(svg_path, definition=definition)
    all_points = np.vstack(contours)
    source_height = float(np.ptp(all_points[:, 1]))
    if source_height == 0:
        raise ValueError("The SVG contours have no height")

    # A single scale factor preserves the artwork's original aspect ratio.
    scale = float(height_mm) / source_height
    contours = [contour * scale for contour in contours]
    all_points = np.vstack(contours)
    artwork_low = all_points.min(axis=0)
    artwork_high = all_points.max(axis=0)
    if output_mode == "stencil":
        low = artwork_low - float(border_mm)
        high = artwork_high + float(border_mm)
    else:
        low = artwork_low
        high = artwork_high
    width, height = high - low
    mesh_size = max(min(width, height) / 18.0, float(thickness_mm) / 3.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.Binary", 1)
        gmsh.model.add(output_mode)
        factory = gmsh.model.occ

        def add_loop(points):
            point_tags = [
                factory.addPoint(float(x), float(y), 0.0, mesh_size) for x, y in points
            ]
            line_tags = [
                factory.addLine(point_tags[i], point_tags[(i + 1) % len(point_tags)])
                for i in range(len(point_tags))
            ]
            return factory.addCurveLoop(line_tags)

        if output_mode == "stencil":
            outer = np.array(
                [
                    [low[0], low[1]],
                    [high[0], low[1]],
                    [high[0], high[1]],
                    [low[0], high[1]],
                ]
            )
            outer_loop = add_loop(outer)
            hole_loops = [add_loop(contour) for contour in contours]
            surfaces = [factory.addPlaneSurface([outer_loop, *hole_loops])]
        else:
            # Each path is its own filled island. This also preserves separate
            # pieces, such as the circle and triangle in the bundled example.
            surfaces = [
                factory.addPlaneSurface([add_loop(contour)]) for contour in contours
            ]

        extruded = factory.extrude(
            [(2, surface) for surface in surfaces],
            0.0,
            0.0,
            float(thickness_mm),
        )
        volume_tags = [tag for dimension, tag in extruded if dimension == 3]
        if not volume_tags:
            raise RuntimeError("Gmsh did not create a closed volume")

        factory.synchronize()
        gmsh.model.mesh.generate(3)

        # Without volume-based orientation, the bottom can point in the same
        # direction as the top even though every edge is used twice.
        for volume_tag in volume_tags:
            gmsh.model.mesh.setOutwardOrientation(volume_tag)

        gmsh.write(str(output_path.resolve()))
    finally:
        gmsh.finalize()

    return validate_stl(output_path.resolve())
