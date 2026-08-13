"""FastAPI entry point for the self-hosted SVG-to-STL service."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from defusedxml import minidom
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

BASE_DIR = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
CONVERSION_TIMEOUT_SECONDS = int(os.getenv("CONVERSION_TIMEOUT_SECONDS", 180))
MAX_CONCURRENT_CONVERSIONS = int(os.getenv("MAX_CONCURRENT_CONVERSIONS", 1))
DIAGNOSTIC_ERRORS = os.getenv("DIAGNOSTIC_ERRORS", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MAX_DIAGNOSTIC_CHARS = 1600
LOGGER = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="SVG to STL",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
conversion_slots = asyncio.Semaphore(max(1, MAX_CONCURRENT_CONVERSIONS))


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Apply browser protections without interfering with SVG blob previews."""
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' blob: data:; "
        "script-src 'self'; "
        "style-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "frame-ancestors 'none'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def _download_stem(filename: str | None) -> str:
    """Create a short filesystem-safe base name without trusting user paths."""
    stem = Path(filename or "stencil").stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return (cleaned or "stencil")[:60]


async def _save_upload(upload: UploadFile, destination: Path) -> int:
    """Stream an upload to disk while enforcing the configured byte limit."""
    if Path(upload.filename or "").suffix.lower() != ".svg":
        raise HTTPException(status_code=415, detail="Choose a file ending in .svg")

    total = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(64 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"SVG exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
                    ),
                )
            output.write(chunk)

    if total == 0:
        raise HTTPException(status_code=400, detail="The uploaded SVG is empty")
    return total


def _preflight_svg(path: Path) -> None:
    """Reject non-SVG XML and documents without path drawing data."""
    try:
        document = minidom.parse(str(path))
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="The SVG XML is not valid",
        ) from error

    try:
        if document.documentElement.localName != "svg":
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not an SVG",
            )
        has_path = any(
            node.getAttribute("d").strip()
            for node in document.getElementsByTagName("path")
        )
        if not has_path:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No path drawing data was found; convert shapes and text "
                    "to paths first"
                ),
            )
    finally:
        document.unlink()


def _structured_worker_error(stderr: str) -> str | None:
    """Extract the worker's final JSON error without exposing command details."""
    for line in reversed(stderr.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("error"):
            return str(payload["error"])
    return None


def _diagnostic_excerpt(output: str) -> str:
    """Return a bounded diagnostic tail without container filesystem paths."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    excerpt = " | ".join(lines[-12:])
    excerpt = re.sub(r'File "[^"]+"', 'File "<internal>"', excerpt)
    excerpt = re.sub(r"/(?:app|tmp)/[^\s\"']+", "<internal-path>", excerpt)
    return excerpt[-MAX_DIAGNOSTIC_CHARS:]


def _worker_error(stderr: str, returncode: int, stdout: str = "") -> str:
    """Return a safe worker error, with opt-in abnormal-exit diagnostics."""
    if structured_error := _structured_worker_error(stderr):
        return structured_error

    if not DIAGNOSTIC_ERRORS:
        return "Conversion failed before a valid STL could be produced"

    if returncode < 0:
        signal_number = -returncode
        known_signal_names = {4: "SIGILL", 9: "SIGKILL", 11: "SIGSEGV"}
        signal_name = known_signal_names.get(signal_number)
        if signal_name is None:
            try:
                signal_name = signal.Signals(signal_number).name
            except ValueError:
                signal_name = "UNKNOWN_SIGNAL"
        summary = (
            f"Conversion worker terminated by {signal_name} (signal {signal_number})."
        )
        hints = {
            4: "The converter may have used an instruction unsupported by this CPU.",
            9: (
                "The process was forcibly killed; on a constrained NAS this often "
                "indicates an out-of-memory kill."
            ),
            11: "The native converter crashed with a segmentation fault.",
        }
        if hint := hints.get(signal_number):
            summary = f"{summary} {hint}"
    else:
        summary = f"Conversion worker exited with status {returncode}."

    excerpt = _diagnostic_excerpt(stderr) or _diagnostic_excerpt(stdout)
    if excerpt:
        return f"{summary} Diagnostic output: {excerpt}"
    return f"{summary} No diagnostic output was captured."


def _run_worker(
    input_path: Path,
    output_path: Path,
    *,
    thickness_mm: float,
    height_mm: float,
    border_mm: float,
    definition: int,
    output_mode: str,
) -> dict:
    """Run one isolated conversion and return the worker's mesh report."""
    command = [
        sys.executable,
        "-m",
        "app.worker",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--thickness",
        str(thickness_mm),
        "--height",
        str(height_mm),
        "--border",
        str(border_mm),
        "--definition",
        str(definition),
        "--mode",
        output_mode,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=BASE_DIR.parent,
            capture_output=True,
            text=True,
            timeout=CONVERSION_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            status_code=504,
            detail=f"Conversion exceeded the {CONVERSION_TIMEOUT_SECONDS}-second limit",
        ) from error

    if completed.returncode != 0:
        LOGGER.error(
            "Conversion worker failed with return code %s; stderr=%s; stdout=%s",
            completed.returncode,
            _diagnostic_excerpt(completed.stderr) or "<empty>",
            _diagnostic_excerpt(completed.stdout) or "<empty>",
        )
        raise HTTPException(
            status_code=422,
            detail=_worker_error(
                completed.stderr,
                completed.returncode,
                completed.stdout,
            ),
        )

    try:
        report = json.loads(completed.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail="The converter returned an unreadable validation report",
        ) from error
    return report


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024)},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/convert")
async def convert(
    svg: Annotated[UploadFile, File()],
    thickness_mm: Annotated[float, Form(ge=0.4, le=50.0)] = 3.0,
    height_mm: Annotated[float, Form(ge=5.0, le=1000.0)] = 80.0,
    border_mm: Annotated[float, Form(ge=0.0, le=200.0)] = 10.0,
    definition: Annotated[int, Form(ge=3, le=48)] = 12,
    output_mode: Annotated[Literal["stencil", "shape"], Form()] = "stencil",
):
    """Convert one upload and stream the validated STL back to the browser."""
    work_dir = Path(tempfile.mkdtemp(prefix="svg2stl-"))
    input_path = work_dir / "input.svg"
    output_name = f"{_download_stem(svg.filename)}_{output_mode}.stl"
    output_path = work_dir / output_name

    try:
        await _save_upload(svg, input_path)
        _preflight_svg(input_path)
        async with conversion_slots:
            report = await asyncio.to_thread(
                _run_worker,
                input_path,
                output_path,
                thickness_mm=thickness_mm,
                height_mm=height_mm,
                border_mm=border_mm,
                definition=definition,
                output_mode=output_mode,
            )

        extents = report["extents"]
        headers = {
            "Cache-Control": "no-store",
            "X-Mesh-Vertices": str(report["vertices"]),
            "X-Mesh-Faces": str(report["faces"]),
            "X-Mesh-Width": f"{extents[0]:.3f}",
            "X-Mesh-Height": f"{extents[1]:.3f}",
            "X-Mesh-Thickness": f"{extents[2]:.3f}",
            "X-Mesh-Watertight": str(report["watertight"]).lower(),
            "X-Mesh-Winding": str(report["winding_consistent"]).lower(),
            "X-Output-Mode": output_mode,
        }
        return FileResponse(
            output_path,
            media_type="model/stl",
            filename=output_name,
            headers=headers,
            background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
        )
    except HTTPException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail="Unexpected conversion error",
        ) from error
    finally:
        await svg.close()
