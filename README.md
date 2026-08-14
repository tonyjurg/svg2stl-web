# SVG to STL Web

[![Verify](https://github.com/tonyjurg/svg2stl-web/actions/workflows/verify.yml/badge.svg)](https://github.com/tonyjurg/svg2stl-web/actions/workflows/verify.yml)
[![Website](https://img.shields.io/badge/website-GitHub%20Pages-08766d.svg)](https://tonyjurg.github.io/svg2stl-web/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/tonyjurg/svg2stl-web)

A self-hosted web application that converts closed SVG paths into a validated
STL. It can create either a stencil plate with the artwork cut out or the solid
SVG artwork itself.

The central benefit of self-hosting is artwork privacy: the SVG is processed on
your own machine instead of being uploaded to an online conversion provider.
The application has no cloud conversion, analytics, telemetry, or CDN runtime
dependency, and temporary SVG and STL files are deleted after the response.

The service is intended for a home or workshop network and can run on an
x86-64 Synology NAS with Container Manager.

Visit the [project website](https://tonyjurg.github.io/svg2stl-web/) for a
high-level visual overview, animated output examples, and routes into the
detailed documentation.

## Features

- Local conversion keeps artwork away from third-party online converters
- Browser-based SVG preview with zoom, pan, and fit controls
- Interactive STL preview with rotate, pan, zoom, and SVG/STL switching
- Stencil plate and solid shape output modes
- Configurable artwork height, thickness, border, and curve detail
- Explicit outward face orientation before STL export
- Validation for watertightness, winding, positive volume, manifold edges,
  degenerate faces, and duplicate faces
- Automatic cleanup of uploaded and generated files
- Responsive interface for desktop and mobile browsers
- Read-only, non-root Docker container with bounded temporary storage

## Output modes

| Mode | Result | Border setting |
| --- | --- | --- |
| **Stencil plate** | A rectangular plate with each closed SVG path removed | Adds material around the artwork |
| **Solid shape** | Each closed SVG path is extruded into a solid piece | Ignored |

Solid shape mode may create several disconnected pieces in one STL when the SVG
contains several paths. Confirm in your slicer that every intended piece is on
the build plate.

## Quick start with Docker

Requirements: Docker Engine with Compose and an x86-64 host.

```bash
git clone https://github.com/tonyjurg/svg2stl-web.git
cd svg2stl-web
docker compose up --build -d
```

Open <http://localhost:8080>. Check the service with:

```bash
curl http://localhost:8080/api/health
```

The expected response is `{"status":"ok"}`.

## Quick start with Python

Python 3.11 or newer is required. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8080
```

On Linux or macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8080
```

Open <http://localhost:8080> and try
[`examples/simple_shapes.svg`](examples/simple_shapes.svg).

## Using the application

1. Choose or drop an SVG file.
2. Select **Stencil plate** or **Solid shape**.
3. Set the required dimensions in millimetres.
4. Adjust curve detail if the artwork contains arcs or curves.
5. Select **Create stencil plate** or **Create solid shape**.
6. Review the reported dimensions and validation results.
7. Select **STL** in the preview to inspect the generated mesh in 3D.
8. Download the STL and inspect it in your slicer before printing.

Only explicitly closed SVG `<path>` elements are converted. Convert text and
SVG primitives such as circles and rectangles to paths before uploading.

## Documentation

- [Preparing SVG files and choosing settings](docs/USAGE.md)
- [Synology and Docker deployment](docs/DEPLOYMENT.md)
- [DSM user authentication](docs/AUTHENTICATION.md)
- [HTTP API reference](docs/API.md)
- [Architecture and development](docs/DEVELOPMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Contributing](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)

## Important limitations

- SVG transforms are not applied.
- Text and primitives such as `<rect>`, `<circle>`, and `<polygon>` are not
  interpreted directly.
- Open paths are ignored.
- Nested islands, fill rules, strokes, and self-intersections are not resolved.
- Every closed path is treated independently; visual appearance in an SVG
  editor is not enough to guarantee equivalent solid geometry.
- The supplied container targets x86-64 because the Gmsh Python package used by
  the project is not distributed as a standard Linux ARM wheel.

See [the usage guide](docs/USAGE.md) for preparation advice and examples.

## Security model

The application has no login system. Keep it on a trusted LAN or place it
behind an authenticated HTTPS reverse proxy. Uploads are size-limited, parsed
with external XML entities disabled, handled in isolated conversion processes,
and removed after the response is sent.

See [the deployment guide](docs/DEPLOYMENT.md#network-and-access) before making
the service reachable outside your home network.

## Verification

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m pytest
```

GitHub Actions runs the same lint and test checks on Linux and builds the
production Docker image for every push and pull request.

## Origins and license

This project builds on the SVG-to-STL approach from
[MaxHalford/svg2stl](https://github.com/MaxHalford/svg2stl) and its
[avipars/svg2stl](https://github.com/avipars/svg2stl) fork. The web service,
isolated worker, OpenCASCADE volume construction, face-orientation repair,
mesh validation, shape mode, and deployment tooling are a substantial rewrite.

The source code is available under the [MIT License](LICENSE). Third-party
packages and bundled binaries retain their own licenses; see
[third-party notices](THIRD_PARTY_NOTICES.md).

## AI-assisted development

OpenAI Codex assisted with implementation, analysis, documentation, and test
execution under human direction. Its output was reviewed through source
inspection, automated tests, real STL validation, browser checks, and Linux
container builds.
