import { state } from './state.js';
import { drawToCanvas, ctx, mainCanvas } from './canvas.js';
import { deactivateCrop } from './crop.js';
import { previewSec, submitBtn, coordsEl, updateQueueInfo } from './ui.js';

const MAX_FILES = 610;
const ENDPOINT  = 'http://localhost:8000/upload/';

// ---- queue setup ----
export function handleFileSelection(files) {
  const images = Array.from(files).filter(f => f.type.startsWith('image/'));
  if (images.length === 0) return;
  if (images.length > MAX_FILES) {
    alert(`Only the first ${MAX_FILES} images will be used.`);
  }
  state.imageFiles = images.slice(0, MAX_FILES);
  loadImageFile(state.imageFiles[0]);
  updateQueueInfo();
}

function loadImageFile(file) {
  const url = URL.createObjectURL(file);
  const imgEl = new Image();
  imgEl.onload = () => {
    state.img = imgEl;
    state.imgNaturalWidth  = imgEl.width;
    state.imgNaturalHeight = imgEl.height;
    drawToCanvas(imgEl);

    document.getElementById('drop-zone').style.display    = 'none';
    document.getElementById('canvas-wrapper').style.display = 'block';
    document.getElementById('toolbar').style.display      = 'flex';
    previewSec.style.display = 'none';
    document.getElementById('workspace').classList.add('cropper-active');
    deactivateCrop();
    state.selectionActive = false;
    document.getElementById('start-crop-btn').disabled = false;
    URL.revokeObjectURL(url);
  };
  imgEl.src = url;
}

// ---- full reset ----
export function fullReset() {
  document.getElementById('drop-zone').style.display      = '';
  document.getElementById('canvas-wrapper').style.display = 'none';
  document.getElementById('toolbar').style.display        = 'none';
  previewSec.style.display = 'none';
  document.getElementById('workspace').classList.remove('cropper-active');
  state.img = null;
  state.imageFiles = [];
  document.getElementById('file-input').value = '';
  deactivateCrop();
  state.selectionActive = false;
  document.getElementById('start-crop-btn').disabled = true;
  coordsEl.textContent = `x: —  y: —  |  w: —  h: —`;
  ctx.clearRect(0, 0, mainCanvas.width, mainCanvas.height);
  updateQueueInfo();
}

// ---- POST submission ----
export async function submitCrop() {
  if (!state.img || !state.selectionActive || state.cropW <= 0) {
    alert('Please define a crop region first.');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = 'Uploading…';

  const fd = new FormData();
  state.imageFiles.forEach(f => fd.append('images', f));
  fd.append('crop_x', state.cropX);
  fd.append('crop_y', state.cropY);
  fd.append('crop_w', state.cropW);
  fd.append('crop_h', state.cropH);

  try {
    const res = await fetch(ENDPOINT, { method: 'POST', body: fd });
    if (res.ok) {
      alert(`✓ ${state.imageFiles.length} image(s) uploaded successfully.`);
      fullReset();
    } else {
      alert(`Server error: ${res.status} ${res.statusText}`);
    }
  } catch (err) {
    alert(`Request failed: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '↑ Upload all';
  }
}
