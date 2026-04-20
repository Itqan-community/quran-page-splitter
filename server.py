"""FastAPI server — thin HTTP layer that delegates to services."""

import logging
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from services import process_all_pages, save_border_assets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Line Cutter Server")

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the frontend HTML."""
    index_path = Path("index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return index_path.read_text(encoding="utf-8")


@app.post("/upload/")
async def upload_images(
    images: List[UploadFile] = File(..., description="Image files"),
    sura_name: UploadFile = File(..., description="Sura name border"),
    aya_separator: UploadFile = File(..., description="Aya separator asset"),
    crop_x: int = Form(..., description="Left coordinate of crop rectangle"),
    crop_y: int = Form(..., description="Top coordinate of crop rectangle"),
    crop_w: int = Form(..., description="Width of crop rectangle"),
    crop_h: int = Form(..., description="Height of crop rectangle"),
    gap_threshold: float = Form(0.1, description="Gap detection threshold"),
    min_line_height: int = Form(20, description="Minimum line height in pixels"),
    padding: int = Form(4, description="Padding around each line"),
):
    """Accept page images, crop, detect lines, and export results."""
    if crop_w <= 0 or crop_h <= 0:
        raise HTTPException(status_code=400, detail="Invalid crop dimensions")

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    # Save border assets
    try:
        save_border_assets(
            sura_data=await sura_name.read(),
            sura_name=sura_name.filename,
            aya_data=await aya_separator.read(),
            aya_name=aya_separator.filename,
            results_dir=results_dir,
        )
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save border assets: {e}"
        ) from e

    # Read all uploads into memory so the service layer is IO-agnostic
    images_data = [
        (await f.read(), f.filename or "unknown") for f in images
    ]

    # Delegate to the processing pipeline
    output_summary = process_all_pages(
        images_data=images_data,
        crop_rect=(crop_x, crop_y, crop_w, crop_h),
        line_params={
            "gap_threshold": gap_threshold,
            "min_line_height": min_line_height,
            "padding": padding,
        },
        results_dir=results_dir,
    )

    return {"status": "completed", "results": output_summary}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
