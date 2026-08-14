import { createStlViewer } from "./stl-viewer.js";

const fileInput = document.querySelector("#svg-file");
const dropZone = document.querySelector("#drop-zone");
const dropTitle = document.querySelector("#drop-title");
const dropDetail = document.querySelector("#drop-detail");
const previewStage = document.querySelector("#preview-stage");
const previewTools = document.querySelector("#preview-tools");
const preview = document.querySelector("#svg-preview");
const stlPreview = document.querySelector("#stl-preview");
const emptyPreview = document.querySelector("#empty-preview");
const previewStatus = document.querySelector("#preview-status");
const previewHelp = document.querySelector("#preview-help");
const showSvgButton = document.querySelector("#show-svg");
const showStlButton = document.querySelector("#show-stl");
const zoomOutButton = document.querySelector("#zoom-out");
const zoomInButton = document.querySelector("#zoom-in");
const resetViewButton = document.querySelector("#reset-view");
const clearButton = document.querySelector("#clear-file");
const form = document.querySelector("#conversion-form");
const convertButton = document.querySelector("#convert-button");
const buttonLabel = convertButton.querySelector(".button-label");
const detailInput = document.querySelector("#definition");
const detailOutput = document.querySelector("#detail-output");
const modeInputs = document.querySelectorAll('input[name="output_mode"]');
const borderField = document.querySelector("#border-field");
const borderInput = document.querySelector("#border-mm");
const errorMessage = document.querySelector("#error-message");
const resultPanel = document.querySelector("#result-panel");
const resultLabel = document.querySelector("#result-label");
const resultName = document.querySelector("#result-name");
const downloadLink = document.querySelector("#download-link");
const downloadText = document.querySelector("#download-text");

const SVG_MIN_SCALE = 0.25;
const SVG_MAX_SCALE = 12;

let selectedFile = null;
let previewUrl = null;
let downloadUrl = null;
let stlBlob = null;
let stlViewer = null;
let stlGeneration = 0;
let resultMode = null;
let activePreview = "svg";
let svgView = { scale: 1, x: 0, y: 0 };
let panState = null;

function selectedMode() {
  return document.querySelector('input[name="output_mode"]:checked').value;
}

function modeName(mode) {
  return mode === "stencil" ? "Stencil plate" : "Solid shape";
}

function sourceStatus() {
  return selectedFile
    ? `Source SVG · ${modeName(selectedMode())} selected`
    : "Awaiting artwork";
}

function updateMode() {
  const isStencil = selectedMode() === "stencil";
  borderInput.disabled = !isStencil;
  borderField.classList.toggle("is-disabled", !isStencil);
  borderField.setAttribute("aria-disabled", String(!isStencil));
  buttonLabel.textContent = isStencil ? "Create stencil plate" : "Create solid shape";
  clearResult();
  previewStatus.textContent = sourceStatus();
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function revokeUrl(url) {
  if (url) URL.revokeObjectURL(url);
}

function setPreviewButtons(mode) {
  const showingSvg = mode === "svg";
  showSvgButton.classList.toggle("is-active", showingSvg);
  showSvgButton.setAttribute("aria-pressed", String(showingSvg));
  showStlButton.classList.toggle("is-active", !showingSvg);
  showStlButton.setAttribute("aria-pressed", String(!showingSvg));
}

function activatePreview(mode) {
  activePreview = mode;
  const showingSvg = mode === "svg";
  preview.hidden = !showingSvg || !selectedFile;
  stlPreview.hidden = showingSvg;
  emptyPreview.hidden = Boolean(selectedFile);
  previewStage.classList.toggle("is-svg-view", showingSvg && Boolean(selectedFile));
  previewStage.classList.toggle("is-stl-view", !showingSvg);
  previewHelp.textContent = showingSvg
    ? "Scroll to zoom · drag to pan"
    : "Drag to rotate · right-drag to pan · scroll to zoom";
  setPreviewButtons(mode);
}

function applySvgView() {
  preview.style.transform = `translate3d(${svgView.x}px, ${svgView.y}px, 0) scale(${svgView.scale})`;
}

function resetSvgView() {
  svgView = { scale: 1, x: 0, y: 0 };
  applySvgView();
}

function zoomSvg(factor, clientX = null, clientY = null) {
  const nextScale = Math.min(
    SVG_MAX_SCALE,
    Math.max(SVG_MIN_SCALE, svgView.scale * factor),
  );
  if (nextScale === svgView.scale) return;

  const bounds = previewStage.getBoundingClientRect();
  const anchorX = (clientX ?? bounds.left + bounds.width / 2) - bounds.left - bounds.width / 2;
  const anchorY = (clientY ?? bounds.top + bounds.height / 2) - bounds.top - bounds.height / 2;
  const ratio = nextScale / svgView.scale;
  svgView.x = anchorX - (anchorX - svgView.x) * ratio;
  svgView.y = anchorY - (anchorY - svgView.y) * ratio;
  svgView.scale = nextScale;
  applySvgView();
}

function disposeStlViewer() {
  stlGeneration += 1;
  const viewer = stlViewer;
  stlViewer = null;
  try {
    viewer?.dispose();
  } catch (error) {
    // A graphics-driver cleanup error must never block changing output mode.
    console.warn("Could not fully dispose the STL preview", error);
  } finally {
    stlPreview.replaceChildren();
  }
}

function clearResult() {
  revokeUrl(downloadUrl);
  downloadUrl = null;
  stlBlob = null;
  resultMode = null;
  downloadLink.removeAttribute("href");
  resultPanel.hidden = true;
  showStlButton.disabled = true;
  activatePreview("svg");
  disposeStlViewer();
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
}

async function showPreviewMode(mode) {
  if (mode === "svg") {
    activatePreview("svg");
    previewStatus.textContent = sourceStatus();
    return;
  }
  if (!stlBlob) return;

  activatePreview("stl");
  if (stlViewer) {
    stlViewer.resize();
    previewStatus.textContent = `${modeName(resultMode)} STL preview`;
    return;
  }

  const generation = stlGeneration;
  const blob = stlBlob;
  showStlButton.disabled = true;
  previewStatus.textContent = "Loading 3D preview";
  try {
    const viewer = createStlViewer(stlPreview);
    await viewer.load(blob);
    if (generation !== stlGeneration || blob !== stlBlob) {
      viewer.dispose();
      return;
    }
    stlViewer = viewer;
    previewStatus.textContent = `${modeName(resultMode)} STL preview`;
  } catch (error) {
    if (generation !== stlGeneration) return;
    stlPreview.replaceChildren();
    activatePreview("svg");
    showError(error.message || "The STL was created, but its 3D preview could not be shown.");
    previewStatus.textContent = `${modeName(resultMode)} STL ready · 3D preview unavailable`;
  } finally {
    if (generation === stlGeneration) showStlButton.disabled = false;
  }
}

function selectFile(file) {
  if (!file || !file.name.toLowerCase().endsWith(".svg")) {
    showError("Choose an SVG file.");
    return;
  }

  clearError();
  clearResult();
  selectedFile = file;
  revokeUrl(previewUrl);
  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  previewTools.hidden = false;
  clearButton.hidden = false;
  dropZone.classList.add("has-file");
  dropTitle.textContent = file.name;
  dropDetail.textContent = formatBytes(file.size);
  previewStatus.textContent = sourceStatus();
  convertButton.disabled = false;
  resetSvgView();
  activatePreview("svg");
}

function resetFile() {
  selectedFile = null;
  fileInput.value = "";
  revokeUrl(previewUrl);
  previewUrl = null;
  preview.removeAttribute("src");
  previewTools.hidden = true;
  clearButton.hidden = true;
  dropZone.classList.remove("has-file");
  dropTitle.textContent = "Choose an SVG";
  dropDetail.textContent = "or drop it here";
  previewStatus.textContent = "Awaiting artwork";
  convertButton.disabled = true;
  clearError();
  clearResult();
  resetSvgView();
  emptyPreview.hidden = false;
}

function responseFilename(response) {
  const disposition = response.headers.get("content-disposition") || "";
  const utfMatch = disposition.match(/filename\*=utf-8''([^;]+)/i);
  if (utfMatch) return decodeURIComponent(utfMatch[1]);
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  const fallback = selectedMode() === "stencil" ? "stencil" : "solid_shape";
  return plainMatch ? plainMatch[1] : `${fallback}.stl`;
}

function detailFromResponse(payload) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg || "Invalid setting").join("; ");
  }
  return "The conversion could not be completed.";
}

function metric(response, name, fallback = "—") {
  return response.headers.get(name) || fallback;
}

function showResult(response, blob) {
  clearResult();
  stlBlob = blob;
  resultMode = response.headers.get("x-output-mode") === "shape" ? "shape" : "stencil";
  downloadUrl = URL.createObjectURL(blob);
  const filename = responseFilename(response);
  downloadLink.href = downloadUrl;
  downloadLink.download = filename;
  resultName.textContent = filename;
  resultLabel.textContent = `VALIDATED ${modeName(resultMode).toUpperCase()} STL`;
  downloadText.textContent = `Download ${modeName(resultMode).toLowerCase()} STL`;

  const width = metric(response, "x-mesh-width");
  const height = metric(response, "x-mesh-height");
  const thickness = metric(response, "x-mesh-thickness");
  document.querySelector("#metric-size").textContent = `${width} × ${height} × ${thickness} mm`;
  document.querySelector("#metric-faces").textContent = Number(
    metric(response, "x-mesh-faces", "0"),
  ).toLocaleString();
  document.querySelector("#metric-watertight").textContent =
    metric(response, "x-mesh-watertight") === "true" ? "Passed" : "Failed";
  document.querySelector("#metric-winding").textContent =
    metric(response, "x-mesh-winding") === "true" ? "Passed" : "Failed";
  resultPanel.hidden = false;
  showStlButton.disabled = false;
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));
clearButton.addEventListener("click", resetFile);
detailInput.addEventListener("input", () => { detailOutput.value = detailInput.value; });
showSvgButton.addEventListener("click", () => showPreviewMode("svg"));
showStlButton.addEventListener("click", () => showPreviewMode("stl"));

zoomOutButton.addEventListener("click", () => {
  if (activePreview === "svg") zoomSvg(0.8);
  else stlViewer?.zoom(0.8);
});
zoomInButton.addEventListener("click", () => {
  if (activePreview === "svg") zoomSvg(1.25);
  else stlViewer?.zoom(1.25);
});
resetViewButton.addEventListener("click", () => {
  if (activePreview === "svg") resetSvgView();
  else stlViewer?.reset();
});

previewStage.addEventListener("wheel", (event) => {
  if (activePreview !== "svg" || !selectedFile) return;
  event.preventDefault();
  zoomSvg(Math.exp(-event.deltaY * 0.0015), event.clientX, event.clientY);
}, { passive: false });

previewStage.addEventListener("pointerdown", (event) => {
  if (activePreview !== "svg" || !selectedFile || event.button !== 0) return;
  panState = { pointerId: event.pointerId, x: event.clientX, y: event.clientY };
  previewStage.setPointerCapture(event.pointerId);
  previewStage.classList.add("is-panning");
});

previewStage.addEventListener("pointermove", (event) => {
  if (!panState || event.pointerId !== panState.pointerId) return;
  svgView.x += event.clientX - panState.x;
  svgView.y += event.clientY - panState.y;
  panState.x = event.clientX;
  panState.y = event.clientY;
  applySvgView();
});

function finishPan(event) {
  if (!panState || event.pointerId !== panState.pointerId) return;
  if (previewStage.hasPointerCapture(event.pointerId)) {
    previewStage.releasePointerCapture(event.pointerId);
  }
  panState = null;
  previewStage.classList.remove("is-panning");
}

previewStage.addEventListener("pointerup", finishPan);
previewStage.addEventListener("pointercancel", finishPan);

for (const modeInput of modeInputs) {
  modeInput.addEventListener("change", updateMode);
}

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}

dropZone.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedFile) return;

  clearError();
  clearResult();
  const mode = selectedMode();
  const body = new FormData(form);
  body.set("output_mode", mode);
  body.append("svg", selectedFile, selectedFile.name);

  convertButton.disabled = true;
  for (const modeInput of modeInputs) modeInput.disabled = true;
  convertButton.classList.add("is-busy");
  buttonLabel.textContent = mode === "stencil" ? "Building stencil plate" : "Building solid shape";
  previewStatus.textContent = "Converting and validating";

  try {
    const response = await fetch("/api/convert", { method: "POST", body });
    if (!response.ok) {
      let payload = null;
      try {
        payload = await response.json();
      } catch {
        // A generic message below is safer than exposing an unexpected body.
      }
      throw new Error(detailFromResponse(payload));
    }

    const blob = await response.blob();
    showResult(response, blob);
    previewStatus.textContent = `${modeName(mode)} STL ready`;
  } catch (error) {
    showError(error.message || "The conversion could not be completed.");
    previewStatus.textContent = sourceStatus();
  } finally {
    convertButton.disabled = false;
    for (const modeInput of modeInputs) modeInput.disabled = false;
    convertButton.classList.remove("is-busy");
    buttonLabel.textContent = mode === "stencil" ? "Create stencil plate" : "Create solid shape";
  }
});

updateMode();

window.addEventListener("beforeunload", () => {
  revokeUrl(previewUrl);
  revokeUrl(downloadUrl);
  disposeStlViewer();
});
