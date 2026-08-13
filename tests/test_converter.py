"""Geometry-level regression tests for the printable STL contract."""

from pathlib import Path

import numpy as np
import pytest
import trimesh
from defusedxml.common import EntitiesForbidden

from app.converter import (
    analyze_stl,
    convert_svg_to_stl,
    parse_svg_contours,
    validate_stl,
)

ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples" / "simple_shapes.svg"


def test_example_converts_to_a_printable_volume(tmp_path):
    output = tmp_path / "simple_shapes.stl"
    report = convert_svg_to_stl(
        EXAMPLE,
        output,
        thickness_mm=2.0,
        height_mm=30.0,
        border_mm=5.0,
        definition=8,
    )

    assert report.printable
    assert report.watertight
    assert report.winding_consistent
    assert report.boundary_edges == 0
    assert report.non_manifold_edges == 0
    assert report.degenerate_faces == 0
    assert report.duplicate_faces == 0
    assert np.isclose(report.extents[1], 40.0)
    assert np.isclose(report.extents[2], 2.0)
    assert output.is_file()


def test_example_converts_to_the_svg_shape_without_a_border(tmp_path):
    output = tmp_path / "simple_shapes_shape.stl"
    report = convert_svg_to_stl(
        EXAMPLE,
        output,
        thickness_mm=2.0,
        height_mm=30.0,
        border_mm=50.0,
        definition=8,
        output_mode="shape",
    )

    assert report.printable
    assert np.isclose(report.extents[1], 30.0)
    assert np.isclose(report.extents[2], 2.0)
    assert output.is_file()


def test_unknown_output_mode_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Output mode"):
        convert_svg_to_stl(
            EXAMPLE,
            tmp_path / "unknown.stl",
            output_mode="relief",
        )


def test_parser_reads_both_closed_paths():
    contours = parse_svg_contours(EXAMPLE, definition=8)
    assert len(contours) == 2


def test_validator_rejects_one_reversed_face(tmp_path):
    mesh = trimesh.creation.box(extents=(2.0, 2.0, 2.0))
    mesh.faces[0] = mesh.faces[0][::-1]
    output = tmp_path / "flipped.stl"
    mesh.export(output)

    report = analyze_stl(output)
    assert report.watertight
    assert not report.winding_consistent
    with pytest.raises(ValueError, match="winding_consistent=False"):
        validate_stl(output)


def test_parser_rejects_xml_without_svg_root(tmp_path):
    path = tmp_path / "not-svg.svg"
    path.write_text(
        "<document><path d='M0,0 L1,0 L0,1 Z'/></document>",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not an SVG"):
        parse_svg_contours(path)


def test_parser_rejects_external_entities(tmp_path):
    path = tmp_path / "unsafe.svg"
    path.write_text(
        '<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        '<svg xmlns="http://www.w3.org/2000/svg"><path d="&xxe;"/></svg>',
        encoding="utf-8",
    )

    with pytest.raises(EntitiesForbidden):
        parse_svg_contours(path)
