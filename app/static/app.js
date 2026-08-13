const fileInput = document.querySelector("#svg-file");
const dropZone = document.querySelector("#drop-zone");
const dropTitle = document.querySelector("#drop-title");
const dropDetail = document.querySelector("#drop-detail");
const preview = document.querySelector("#svg-preview");
const emptyPreview = document.querySelector("#empty-preview");
const previewStatus = document.querySelector("#preview-status");
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
const resultName = document.querySelector("#result-name");
const downloadLink = document.querySelector("#download-link");

let selectedFile = null;
let previewUrl = null;
let downloadUrl = null;

function selectedMode() {
  return document.querySelector('input[name="output_mode"]:checked').value;
}

function updateMode() {
  const isStencil = selectedMode() === "stencil";
  borderInput.disabled = !isStencil;
  borderField.classList.toggle("is-disabled", !isStencil);
  borderField.setAttribute("aria-disabled", String(!isStencil));
  buttonLabel.textContent = isStencil ? "Create stencil" : "Create SVG shape";
  previewStatus.textContent = selectedFile ? selectedFile.name : "Awaiting artwork";
  clearResult();
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function revokeUrl(url) {
  if (url) URL.revokeObjectURL(url);
}

function clearResult() {
  revokeUrl(downloadUrl);
  downloadUrl = null;
  downloadLink.removeAttribute("href");
  resultPanel.hidden = true;
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
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
  preview.hidden = false;
  emptyPreview.hidden = true;
  clearButton.hidden = false;
  dropZone.classList.add("has-file");
  dropTitle.textContent = file.name;
  dropDetail.textContent = formatBytes(file.size);
  previewStatus.textContent = file.name;
  convertButton.disabled = false;
}

function resetFile() {
  selectedFile = null;
  fileInput.value = "";
  revokeUrl(previewUrl);
  previewUrl = null;
  preview.removeAttribute("src");
  preview.hidden = true;
  emptyPreview.hidden = false;
  clearButton.hidden = true;
  dropZone.classList.remove("has-file");
  dropTitle.textContent = "Choose an SVG";
  dropDetail.textContent = "or drop it here";
  previewStatus.textContent = "Awaiting artwork";
  convertButton.disabled = true;
  clearError();
  clearResult();
}

function responseFilename(response) {
  const disposition = response.headers.get("content-disposition") || "";
  const utfMatch = disposition.match(/filename\*=utf-8''([^;]+)/i);
  if (utfMatch) return decodeURIComponent(utfMatch[1]);
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch ? plainMatch[1] : `${selectedMode()}.stl`;
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
  downloadUrl = URL.createObjectURL(blob);
  const filename = responseFilename(response);
  downloadLink.href = downloadUrl;
  downloadLink.download = filename;
  resultName.textContent = filename;

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
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));
clearButton.addEventListener("click", resetFile);
detailInput.addEventListener("input", () => { detailOutput.value = detailInput.value; });
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
  convertButton.disabled = true;
  for (const modeInput of modeInputs) modeInput.disabled = true;
  convertButton.classList.add("is-busy");
  const mode = selectedMode();
  buttonLabel.textContent = mode === "stencil" ? "Building stencil" : "Building shape";
  previewStatus.textContent = "Converting and validating";

  const body = new FormData(form);
  body.append("svg", selectedFile, selectedFile.name);

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
    previewStatus.textContent = "Validated STL ready";
  } catch (error) {
    showError(error.message || "The conversion could not be completed.");
    previewStatus.textContent = selectedFile.name;
  } finally {
    convertButton.disabled = false;
    for (const modeInput of modeInputs) modeInput.disabled = false;
    convertButton.classList.remove("is-busy");
    buttonLabel.textContent = mode === "stencil" ? "Create stencil" : "Create SVG shape";
  }
});

updateMode();

window.addEventListener("beforeunload", () => {
  revokeUrl(previewUrl);
  revokeUrl(downloadUrl);
});
