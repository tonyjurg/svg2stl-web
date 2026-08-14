"""HTTP tests for uploads, validation, and STL downloads."""

from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

import app.main as web
from app.converter import analyze_stl

ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples" / "simple_shapes.svg"
client = TestClient(web.app)


def test_home_page_and_health_endpoint():
    page = client.get("/")
    health = client.get("/api/health")

    assert page.status_code == 200
    assert "SVG to STL" in page.text
    assert "Create stencil plate" in page.text
    assert "Solid shape" in page.text
    assert "Source SVG" in page.text
    assert "Generated STL" in page.text
    assert 'id="show-svg"' in page.text
    assert 'id="show-stl"' in page.text
    assert 'type="module"' in page.text
    assert 'class="brand-mark"' in page.text
    assert "https://github.com/tonyjurg/svg2stl-web" in page.text
    assert "/static/favicon.svg" in page.text
    assert health.json() == {"status": "ok"}
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"


def test_local_preview_modules_are_served_without_cdn_dependencies():
    viewer = client.get("/static/stl-viewer.js")
    three = client.get("/static/three.module.min.js")
    three_core = client.get("/static/three.core.min.js")
    loader = client.get("/static/STLLoader.js")

    assert viewer.status_code == 200
    assert three.status_code == 200
    assert three_core.status_code == 200
    assert loader.status_code == 200
    assert 'from"./three.core.min.js"' in three.text
    assert 'from "./three.module.min.js"' in viewer.text
    assert "from './three.module.min.js'" in loader.text
    assert "https://" not in viewer.text


def test_browser_submission_captures_output_mode_before_disabling_controls():
    script = client.get("/static/app.js")

    assert script.status_code == 200
    assert 'body.set("output_mode", mode);' in script.text
    assert script.text.index("const body = new FormData(form);") < script.text.index(
        "for (const modeInput of modeInputs) modeInput.disabled = true;"
    )


def test_conversion_endpoint_returns_a_valid_stl(tmp_path):
    with EXAMPLE.open("rb") as source:
        response = client.post(
            "/api/convert",
            files={"svg": ("simple shapes.svg", source, "image/svg+xml")},
            data={
                "thickness_mm": "2",
                "height_mm": "30",
                "border_mm": "5",
                "definition": "8",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("model/stl")
    assert "simple_shapes_stencil.stl" in response.headers["content-disposition"]
    assert response.headers["x-mesh-watertight"] == "true"
    assert response.headers["x-mesh-winding"] == "true"

    output = tmp_path / "download.stl"
    output.write_bytes(response.content)
    assert analyze_stl(output).printable


def test_shape_mode_returns_the_svg_form_without_a_border(tmp_path):
    with EXAMPLE.open("rb") as source:
        response = client.post(
            "/api/convert",
            files={"svg": ("simple shapes.svg", source, "image/svg+xml")},
            data={
                "thickness_mm": "2",
                "height_mm": "30",
                "border_mm": "50",
                "definition": "8",
                "output_mode": "shape",
            },
        )

    assert response.status_code == 200
    assert "simple_shapes_solid_shape.stl" in response.headers["content-disposition"]
    assert response.headers["x-output-mode"] == "shape"
    assert np.isclose(float(response.headers["x-mesh-height"]), 30.0)

    output = tmp_path / "shape.stl"
    output.write_bytes(response.content)
    assert analyze_stl(output).printable


def test_non_svg_extension_is_rejected():
    response = client.post(
        "/api/convert",
        files={"svg": ("drawing.txt", b"not an svg", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Choose a file ending in .svg"


def test_svg_without_path_data_is_rejected():
    response = client.post(
        "/api/convert",
        files={
            "svg": (
                "empty.svg",
                b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="5"/></svg>',
                "image/svg+xml",
            )
        },
    )

    assert response.status_code == 400
    assert "convert shapes and text to paths" in response.json()["detail"]


def test_upload_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 20)
    response = client.post(
        "/api/convert",
        files={"svg": ("large.svg", b"<svg>" + b"x" * 30 + b"</svg>", "image/svg+xml")},
    )

    assert response.status_code == 413


def test_worker_failure_is_returned_as_a_safe_client_error(monkeypatch):
    def fail_worker(*args, **kwargs):
        raise web.HTTPException(
            status_code=422,
            detail="No usable closed SVG contours were found",
        )

    monkeypatch.setattr(web, "_run_worker", fail_worker)
    with EXAMPLE.open("rb") as source:
        response = client.post(
            "/api/convert",
            files={"svg": ("example.svg", source, "image/svg+xml")},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "No usable closed SVG contours were found"


def test_structured_worker_error_is_returned_without_diagnostic_mode(monkeypatch):
    monkeypatch.setattr(web, "DIAGNOSTIC_ERRORS", False)

    detail = web._worker_error('{"error":"Invalid closed contour"}', 1)

    assert detail == "Invalid closed contour"


def test_unstructured_worker_error_is_hidden_by_default(monkeypatch):
    monkeypatch.setattr(web, "DIAGNOSTIC_ERRORS", False)

    detail = web._worker_error("native converter output", -11)

    assert detail == "Conversion failed before a valid STL could be produced"


def test_diagnostic_worker_error_decodes_kill_signal(monkeypatch):
    monkeypatch.setattr(web, "DIAGNOSTIC_ERRORS", True)

    detail = web._worker_error("", -9)

    assert "SIGKILL (signal 9)" in detail
    assert "out-of-memory kill" in detail
    assert "No diagnostic output was captured" in detail


def test_diagnostic_worker_error_bounds_and_sanitizes_output(monkeypatch):
    monkeypatch.setattr(web, "DIAGNOSTIC_ERRORS", True)
    stderr = (
        'File "/app/app/worker.py", line 10\nRuntimeError: failed in /tmp/input.svg'
    )

    detail = web._worker_error(stderr, 1)

    assert "exited with status 1" in detail
    assert "RuntimeError" in detail
    assert "/app/app/worker.py" not in detail
    assert "/tmp/input.svg" not in detail
    assert len(detail) < web.MAX_DIAGNOSTIC_CHARS + 200


def test_diagnostic_mode_returns_worker_signal_to_web_client(monkeypatch):
    monkeypatch.setattr(web, "DIAGNOSTIC_ERRORS", True)
    completed = web.subprocess.CompletedProcess([], -9, stdout="", stderr="")
    monkeypatch.setattr(web.subprocess, "run", lambda *args, **kwargs: completed)

    with EXAMPLE.open("rb") as source:
        response = client.post(
            "/api/convert",
            files={"svg": ("example.svg", source, "image/svg+xml")},
        )

    assert response.status_code == 422
    assert "SIGKILL (signal 9)" in response.json()["detail"]
