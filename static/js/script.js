// DOM elements
const workspaceDiv = document.getElementById("workspace");
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const browseBtn = document.getElementById("browse-btn");
const wrapper = document.getElementById("canvas-wrapper");
const mainCanvas = document.getElementById("main-canvas");
const selBox = document.getElementById("selection-box");
const toolbar = document.getElementById("toolbar");
const sizeInfo = document.getElementById("size-info");
const cropBtn = document.getElementById("crop-btn");
const resetBtn = document.getElementById("reset-btn");
const previewSec = document.getElementById("preview-section");
const previewCanvas = document.getElementById("preview-canvas");
const saveBtn = document.getElementById("save-btn");
const newCropBtn = document.getElementById("new-crop-btn");
const coordsEl = document.getElementById("coords");
const filenameInput = document.getElementById("filename-input");
const startCropBtn = document.getElementById("start-crop-btn");

// manual inputs
const inputX = document.getElementById("crop-x");
const inputY = document.getElementById("crop-y");
const inputW = document.getElementById("crop-w");
const inputH = document.getElementById("crop-h");

// image state
let img = null; // HTMLImageElement
let scale = 1; // canvas scaling factor (image original -> canvas)
let imgNaturalWidth = 0,
  imgNaturalHeight = 0;

// crop region in ORIGINAL image coordinates (px)
let cropX = 0,
  cropY = 0,
  cropW = 0,
  cropH = 0;
let selectionActive = false; // whether selection box is shown & interactive

// resize / drag interaction
let dragActive = false;
let dragType = null; // 'move', 'top', 'bottom', 'left', 'right', 'topLeft', 'topRight', 'bottomLeft', 'bottomRight'
let dragStartMouse = { x: 0, y: 0 }; // canvas-relative pixels
let dragStartCrop = { x: 0, y: 0, w: 0, h: 0 };

const ctx = mainCanvas.getContext("2d");

// ---- LIVE PREVIEW: generate preview from current crop ----
function updateLivePreview() {
  if (!img || !selectionActive || cropW <= 0 || cropH <= 0) {
    previewSec.style.display = "none";
    return;
  }
  const rw = cropW;
  const rh = cropH;
  previewCanvas.width = rw;
  previewCanvas.height = rh;
  const pCtx = previewCanvas.getContext("2d");
  pCtx.drawImage(img, cropX, cropY, rw, rh, 0, 0, rw, rh);
  previewSec.style.display = "flex";
}

// ---- coordinate helpers ----
function canvasToOriginalCoord(canvasX, canvasY) {
  return { x: Math.round(canvasX / scale), y: Math.round(canvasY / scale) };
}
function originalToCanvasCoord(origX, origY) {
  return { x: origX * scale, y: origY * scale };
}
function originalToCanvasSize(wOrig, hOrig) {
  return { w: wOrig * scale, h: hOrig * scale };
}

// ---- update selection box UI ----
function updateSelectionDiv() {
  if (!selectionActive || cropW <= 0 || cropH <= 0) {
    selBox.style.display = "none";
    return;
  }
  const canvasPos = originalToCanvasCoord(cropX, cropY);
  const canvasSize = originalToCanvasSize(cropW, cropH);
  selBox.style.left = canvasPos.x + "px";
  selBox.style.top = canvasPos.y + "px";
  selBox.style.width = canvasSize.w + "px";
  selBox.style.height = canvasSize.h + "px";
  selBox.style.display = "block";
}

// update manual inputs & sizeInfo & trigger live preview
function updateUIFromCrop() {
  if (!selectionActive || cropW <= 0 || cropH <= 0) {
    inputX.disabled = true;
    inputY.disabled = true;
    inputW.disabled = true;
    inputH.disabled = true;
    sizeInfo.innerHTML = `⚡ select or start cropping`;
    if (cropW <= 0) selBox.style.display = "none";
    updateLivePreview();
    return;
  }
  inputX.disabled = false;
  inputY.disabled = false;
  inputW.disabled = false;
  inputH.disabled = false;
  inputX.value = cropX;
  inputY.value = cropY;
  inputW.value = cropW;
  inputH.value = cropH;
  sizeInfo.innerHTML = `<span>${cropW}</span> × <span>${cropH}</span> px  (x:${cropX}, y:${cropY})`;
  updateSelectionDiv();
  updateLivePreview(); // real‑time refresh
}

// clamp crop region to image bounds
function clampCropBounds() {
  if (!img) return;
  const maxX = imgNaturalWidth - cropW;
  const maxY = imgNaturalHeight - cropH;
  cropX = Math.min(Math.max(0, cropX), Math.max(0, maxX));
  cropY = Math.min(Math.max(0, cropY), Math.max(0, maxY));
  cropW = Math.min(cropW, imgNaturalWidth - cropX);
  cropH = Math.min(cropH, imgNaturalHeight - cropY);
  if (cropW < 1) cropW = 1;
  if (cropH < 1) cropH = 1;
  if (cropX + cropW > imgNaturalWidth) cropX = imgNaturalWidth - cropW;
  if (cropY + cropH > imgNaturalHeight) cropY = imgNaturalHeight - cropH;
}

function setCrop(newX, newY, newW, newH, updateInputs = true) {
  if (!img) return;
  cropX = Math.round(newX);
  cropY = Math.round(newY);
  cropW = Math.round(newW);
  cropH = Math.round(newH);
  if (cropW < 1) cropW = 1;
  if (cropH < 1) cropH = 1;
  clampCropBounds();
  updateSelectionDiv();
  if (updateInputs) updateUIFromCrop();
  else {
    updateSelectionDiv();
    updateLivePreview();
  }
}

function initDefaultCenteredCrop() {
  if (!img) return;
  let defaultSize = Math.min(150, imgNaturalWidth, imgNaturalHeight);
  defaultSize = Math.max(40, defaultSize);
  const newW = defaultSize;
  const newH = defaultSize;
  const newX = Math.floor((imgNaturalWidth - newW) / 2);
  const newY = Math.floor((imgNaturalHeight - newH) / 2);
  setCrop(newX, newY, newW, newH, true);
  selectionActive = true;
  updateUIFromCrop();
}

function deactivateCrop() {
  selectionActive = false;
  cropW = 0;
  cropH = 0;
  cropX = 0;
  cropY = 0;
  selBox.style.display = "none";
  inputX.disabled = true;
  inputY.disabled = true;
  inputW.disabled = true;
  inputH.disabled = true;
  inputX.value = 0;
  inputY.value = 0;
  inputW.value = 0;
  inputH.value = 0;
  sizeInfo.innerHTML = `⚡ no active crop — press "Start cropping"`;
  updateLivePreview();
}

// ---- resize & drag handlers ----
function getResizeHandleType(mouseCanvasX, mouseCanvasY) {
  if (!selectionActive || cropW <= 0) return null;
  const leftEdge = cropX * scale;
  const rightEdge = (cropX + cropW) * scale;
  const topEdge = cropY * scale;
  const bottomEdge = (cropY + cropH) * scale;
  const threshold = 12;
  const nearLeft = Math.abs(mouseCanvasX - leftEdge) <= threshold;
  const nearRight = Math.abs(mouseCanvasX - rightEdge) <= threshold;
  const nearTop = Math.abs(mouseCanvasY - topEdge) <= threshold;
  const nearBottom = Math.abs(mouseCanvasY - bottomEdge) <= threshold;

  if (nearLeft && nearTop) return "topLeft";
  if (nearRight && nearTop) return "topRight";
  if (nearLeft && nearBottom) return "bottomLeft";
  if (nearRight && nearBottom) return "bottomRight";
  if (nearLeft) return "left";
  if (nearRight) return "right";
  if (nearTop) return "top";
  if (nearBottom) return "bottom";
  if (
    mouseCanvasX > leftEdge &&
    mouseCanvasX < rightEdge &&
    mouseCanvasY > topEdge &&
    mouseCanvasY < bottomEdge
  )
    return "move";
  return null;
}

function setCursorFromHandle(handle) {
  if (!handle) {
    selBox.style.cursor = "grab";
    return;
  }
  const cursors = {
    move: "grab",
    top: "ns-resize",
    bottom: "ns-resize",
    left: "ew-resize",
    right: "ew-resize",
    topLeft: "nw-resize",
    topRight: "ne-resize",
    bottomLeft: "sw-resize",
    bottomRight: "se-resize",
  };
  selBox.style.cursor = cursors[handle] || "default";
}

function onSelBoxMousemove(e) {
  if (!selectionActive || dragActive) return;
  const canvasRect = mainCanvas.getBoundingClientRect();
  const mouseCanvasX = e.clientX - canvasRect.left;
  const mouseCanvasY = e.clientY - canvasRect.top;
  const handle = getResizeHandleType(mouseCanvasX, mouseCanvasY);
  setCursorFromHandle(handle);
}

function onSelBoxMouseDown(e) {
  if (!selectionActive || cropW <= 0 || cropH <= 0) return;
  e.preventDefault();
  e.stopPropagation();
  const canvasRect = mainCanvas.getBoundingClientRect();
  const mouseCanvasX = e.clientX - canvasRect.left;
  const mouseCanvasY = e.clientY - canvasRect.top;
  const handle = getResizeHandleType(mouseCanvasX, mouseCanvasY);
  if (!handle) return;

  dragActive = true;
  dragType = handle;
  dragStartMouse.x = mouseCanvasX;
  dragStartMouse.y = mouseCanvasY;
  dragStartCrop = { x: cropX, y: cropY, w: cropW, h: cropH };
  document.body.style.userSelect = "none";

  window.addEventListener("mousemove", onGlobalMouseMove);
  window.addEventListener("mouseup", onGlobalMouseUp);
}

function onGlobalMouseMove(e) {
  if (!dragActive || !img) return;
  const canvasRect = mainCanvas.getBoundingClientRect();
  let mouseCanvasX = e.clientX - canvasRect.left;
  let mouseCanvasY = e.clientY - canvasRect.top;
  mouseCanvasX = Math.min(Math.max(0, mouseCanvasX), mainCanvas.width);
  mouseCanvasY = Math.min(Math.max(0, mouseCanvasY), mainCanvas.height);

  const deltaX = (mouseCanvasX - dragStartMouse.x) / scale;
  const deltaY = (mouseCanvasY - dragStartMouse.y) / scale;
  let newX = dragStartCrop.x,
    newY = dragStartCrop.y,
    newW = dragStartCrop.w,
    newH = dragStartCrop.h;

  switch (dragType) {
    case "move":
      newX = dragStartCrop.x + deltaX;
      newY = dragStartCrop.y + deltaY;
      break;
    case "right":
      newW = dragStartCrop.w + deltaX;
      break;
    case "left":
      newX = dragStartCrop.x + deltaX;
      newW = dragStartCrop.w - deltaX;
      break;
    case "bottom":
      newH = dragStartCrop.h + deltaY;
      break;
    case "top":
      newY = dragStartCrop.y + deltaY;
      newH = dragStartCrop.h - deltaY;
      break;
    case "topRight":
      newY = dragStartCrop.y + deltaY;
      newH = dragStartCrop.h - deltaY;
      newW = dragStartCrop.w + deltaX;
      break;
    case "topLeft":
      newX = dragStartCrop.x + deltaX;
      newW = dragStartCrop.w - deltaX;
      newY = dragStartCrop.y + deltaY;
      newH = dragStartCrop.h - deltaY;
      break;
    case "bottomRight":
      newW = dragStartCrop.w + deltaX;
      newH = dragStartCrop.h + deltaY;
      break;
    case "bottomLeft":
      newX = dragStartCrop.x + deltaX;
      newW = dragStartCrop.w - deltaX;
      newH = dragStartCrop.h + deltaY;
      break;
  }
  if (newW < 2) newW = 2;
  if (newH < 2) newH = 2;
  setCrop(newX, newY, newW, newH, true);
  clampCropBounds();
  updateUIFromCrop();
}

function onGlobalMouseUp() {
  dragActive = false;
  dragType = null;
  document.body.style.userSelect = "";
  window.removeEventListener("mousemove", onGlobalMouseMove);
  window.removeEventListener("mouseup", onGlobalMouseUp);
  if (selectionActive && cropW > 0) updateUIFromCrop();
}

// ---- header mouse tracking ----
function updateHeaderCoords(e) {
  if (!img) return;
  const rect = mainCanvas.getBoundingClientRect();
  let canvasX = e.clientX - rect.left;
  let canvasY = e.clientY - rect.top;
  if (
    canvasX >= 0 &&
    canvasY >= 0 &&
    canvasX <= mainCanvas.width &&
    canvasY <= mainCanvas.height
  ) {
    const orig = canvasToOriginalCoord(canvasX, canvasY);
    coordsEl.textContent = `x: ${orig.x}  y: ${orig.y}  |  w: —  h: —`;
  } else {
    if (selectionActive && cropW > 0)
      coordsEl.textContent = `crop: ${cropW}×${cropH}`;
    else coordsEl.textContent = `x: —  y: —  |  w: —  h: —`;
  }
}

function onCanvasMouseLeave() {
  if (selectionActive && cropW > 0)
    coordsEl.textContent = `crop active: ${cropW}×${cropH}`;
  else coordsEl.textContent = `x: —  y: —  |  w: —  h: —`;
}

// ---- load image and switch to cropping layout ----
function loadImage(file) {
  const url = URL.createObjectURL(file);
  img = new Image();
  img.onload = () => {
    imgNaturalWidth = img.width;
    imgNaturalHeight = img.height;
    const maxW = Math.min(window.innerWidth - 80, 900);
    const maxH = window.innerHeight * 0.6;
    scale = Math.min(1, maxW / imgNaturalWidth, maxH / imgNaturalHeight);
    mainCanvas.width = Math.round(imgNaturalWidth * scale);
    mainCanvas.height = Math.round(imgNaturalHeight * scale);
    ctx.drawImage(img, 0, 0, mainCanvas.width, mainCanvas.height);

    // UI transition
    dropZone.style.display = "none";
    wrapper.style.display = "block";
    toolbar.style.display = "flex";
    previewSec.style.display = "none";
    workspaceDiv.classList.add("cropper-active"); // enable responsive two‑column layout
    deactivateCrop();
    selectionActive = false;
    startCropBtn.disabled = false;
    URL.revokeObjectURL(url);
  };
  img.src = url;
}

function startCropping() {
  if (!img) return;
  deactivateCrop();
  selectionActive = true;
  initDefaultCenteredCrop();
}

function fullReset() {
  dropZone.style.display = "";
  wrapper.style.display = "none";
  toolbar.style.display = "none";
  previewSec.style.display = "none";
  workspaceDiv.classList.remove("cropper-active");
  if (img) {
    img = null;
  }
  fileInput.value = "";
  deactivateCrop();
  selectionActive = false;
  startCropBtn.disabled = true;
  coordsEl.textContent = `x: —  y: —  |  w: —  h: —`;
  if (ctx) ctx.clearRect(0, 0, mainCanvas.width, mainCanvas.height);
}

function onInputChange() {
  if (!selectionActive || !img) return;
  let newX = parseInt(inputX.value, 10);
  let newY = parseInt(inputY.value, 10);
  let newW = parseInt(inputW.value, 10);
  let newH = parseInt(inputH.value, 10);
  if (isNaN(newX)) newX = cropX;
  if (isNaN(newY)) newY = cropY;
  if (isNaN(newW)) newW = cropW;
  if (isNaN(newH)) newH = cropH;
  if (newW < 1) newW = 1;
  if (newH < 1) newH = 1;
  setCrop(newX, newY, newW, newH, false);
  clampCropBounds();
  updateUIFromCrop();
}

// ---- event binding ----
browseBtn.addEventListener("click", () => fileInput.click());
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
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) loadImage(file);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) loadImage(fileInput.files[0]);
});

startCropBtn.addEventListener("click", startCropping);
resetBtn.addEventListener("click", fullReset);
cropBtn.addEventListener("click", () => {
  if (selectionActive && cropW > 0) updateLivePreview();
});
saveBtn.addEventListener("click", () => {
  const filename = (filenameInput.value.trim() || "cropped") + ".png";
  previewCanvas.toBlob((blob) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  }, "image/png");
});
newCropBtn.addEventListener("click", () => {
  if (img) startCropping();
});

inputX.addEventListener("input", onInputChange);
inputY.addEventListener("input", onInputChange);
inputW.addEventListener("input", onInputChange);
inputH.addEventListener("input", onInputChange);

selBox.addEventListener("mousemove", onSelBoxMousemove);
selBox.addEventListener("mousedown", onSelBoxMouseDown);
mainCanvas.addEventListener("mousemove", updateHeaderCoords);
mainCanvas.addEventListener("mouseleave", onCanvasMouseLeave);
window.addEventListener("dragstart", (e) => e.preventDefault());
