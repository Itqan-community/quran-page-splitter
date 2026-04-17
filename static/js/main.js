import { state } from "./state.js";
import { mainCanvas } from "./canvas.js";
import { startCropping, onManualInputChange } from "./crop.js";
import { onSelBoxMousemove, onSelBoxMouseDown } from "./drag.js";
import {
  selBox,
  inputX,
  inputY,
  inputW,
  inputH,
  previewCanvas,
  updateLivePreview,
  updateHeaderCoords,
  onCanvasMouseLeave,
} from "./ui.js";
import { handleFileSelection, fullReset, submitCrop } from "./upload.js";

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const browseBtn = document.getElementById("browse-btn");
const startCropBtn = document.getElementById("start-crop-btn");
const resetBtn = document.getElementById("reset-btn");
const cropBtn = document.getElementById("crop-btn");
const saveBtn = document.getElementById("save-btn");
const newCropBtn = document.getElementById("new-crop-btn");
const submitBtn = document.getElementById("submit-btn");
const filenameInput = document.getElementById("filename-input");

// ---- file selection ----
document.addEventListener("dragover", (e) => e.preventDefault());
document.addEventListener("drop", (e) => e.preventDefault());
browseBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () =>
  dropZone.classList.remove("drag-over"),
);
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  handleFileSelection(e.dataTransfer.files);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) handleFileSelection(fileInput.files);
});

// ---- crop controls ----
startCropBtn.addEventListener("click", startCropping);
resetBtn.addEventListener("click", fullReset);
cropBtn.addEventListener("click", () => {
  if (state.selectionActive && state.cropW > 0) updateLivePreview();
});
newCropBtn.addEventListener("click", () => {
  if (state.img) startCropping();
});

// ---- upload / save ----
submitBtn.addEventListener("click", submitCrop);
saveBtn.addEventListener("click", () => {
  const filename = (filenameInput.value.trim() || "cropped") + ".png";
  previewCanvas.toBlob((blob) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  }, "image/png");
});

// ---- manual coordinate inputs ----
[inputX, inputY, inputW, inputH].forEach((el) =>
  el.addEventListener("input", onManualInputChange),
);

// ---- canvas / selbox mouse events ----
selBox.addEventListener("mousemove", onSelBoxMousemove);
selBox.addEventListener("mousedown", onSelBoxMouseDown);
mainCanvas.addEventListener("mousemove", updateHeaderCoords);
mainCanvas.addEventListener("mouseleave", onCanvasMouseLeave);
window.addEventListener("dragstart", (e) => e.preventDefault());
