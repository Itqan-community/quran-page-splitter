"""FastAPI server — builds the pipeline from HTTP form data and runs it."""

import logging
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import io

from core.config import CropConfig, DetectionConfig, ClassifierConfig
from core.line_detector import LineDetector
from core.classifier import SuraClassifier
from core.page_processor import PageProcessor
from core.pipeline import Pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Line Cutter Server")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = Path("index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return index_path.read_text(encoding="utf-8")


@app.post("/upload/")
async def upload_images(
    images: List[UploadFile] = File(...),
    sura_name: UploadFile = File(...),
    aya_separator: UploadFile = File(...),
    crop_x: int = Form(...),
    crop_y: int = Form(...),
    crop_w: int = Form(...),
    crop_h: int = Form(...),
    gap_threshold: float = Form(0.03),
    min_line_height: int = Form(20),
    padding: int = Form(4),
):
    if crop_w <= 0 or crop_h <= 0:
        raise HTTPException(status_code=400, detail="Invalid crop dimensions")

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    # Build configs
    crop_cfg = CropConfig(x=crop_x, y=crop_y, w=crop_w, h=crop_h)
    det_cfg = DetectionConfig(gap_threshold=gap_threshold, min_line_height=min_line_height, padding=padding)

    # Load sura template and build classifier
    sura_data = await sura_name.read()
    try:
        sura_template = Image.open(io.BytesIO(sura_data))
        sura_template.load()  # Force validation
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid sura template image: {e}")
    classifier = SuraClassifier(template=sura_template, detection=det_cfg)

    # Save aya separator (kept for output directory completeness)
    aya_data = await aya_separator.read()
    aya_path = results_dir / (aya_separator.filename or "aya_separator.png")
    aya_path.write_bytes(aya_data)

    # Build pipeline
    detector = LineDetector(crop=crop_cfg, detection=det_cfg)
    processor = PageProcessor(detector=detector, results_dir=results_dir, classifier=classifier)
    pipeline = Pipeline(processor=processor)

    images_data = [(await f.read(), f.filename or "unknown") for f in images]
    return {"status": "completed", "results": pipeline.run(images_data)}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
