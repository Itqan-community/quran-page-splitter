import io
import logging
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from script.line_cutter import crop_lines

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Line Cutter Server")

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the frontend HTML
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = Path("index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return index_path.read_text(encoding="utf-8")

def make_transparent(crop: Image.Image, threshold: int = 200) -> Image.Image:
    """Convert white background to transparent."""
    rgba = crop.convert("RGBA")
    data = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = data[x, y]
            if r > threshold and g > threshold and b > threshold:
                data[x, y] = (r, g, b, 0)
    return rgba


def _save_upload_to_results(
    data: bytes,
    original_name: Optional[str],
    default_name: str,
    results_dir: Path,
) -> Path:
    """Write bytes under results_dir using the upload basename only."""
    base = Path(original_name or default_name).name
    if not base or base in (".", ".."):
        base = default_name
    path = results_dir / base
    path.write_bytes(data)
    return path


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
    """
    Accept multiple images and a single crop rectangle.
    For each image:
        - Crop to (crop_x, crop_y, crop_x+crop_w, crop_y+crop_h)
        - Split into text lines using crop_lines (margins = 0)
        - Save each line as {stem}-{line_number}.png in 'results/'
    """
    if crop_w <= 0 or crop_h <= 0:
        raise HTTPException(status_code=400, detail="Invalid crop dimensions")

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    try:
        sura_path = _save_upload_to_results(
            await sura_name.read(), sura_name.filename, "sura_name.png", results_dir
        )
        logger.info(f"Saved {sura_path}")
        aya_path = _save_upload_to_results(
            await aya_separator.read(), aya_separator.filename, "aya_separator.png", results_dir
        )
        logger.info(f"Saved {aya_path}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save border assets: {e}") from e

    output_summary = []

    for file in images:
        filename = file.filename or "unknown"
        logger.info(f"Processing {filename}")

        # Read image
        try:
            contents = await file.read()
            img = Image.open(io.BytesIO(contents))
        except Exception as e:
            logger.error(f"Failed to open {filename}: {e}")
            output_summary.append({
                "filename": filename,
                "status": "error",
                "message": f"Failed to open image: {str(e)}"
            })
            continue

        # Apply crop
        try:
            # Ensure crop rectangle is within image bounds
            img_w, img_h = img.size
            left = max(0, crop_x)
            top = max(0, crop_y)
            right = min(img_w, left + crop_w)
            bottom = min(img_h, top + crop_h)
            if right <= left or bottom <= top:
                raise ValueError("Crop rectangle is outside image bounds")
            cropped = img.crop((left, top, right, bottom))
        except Exception as e:
            logger.error(f"Crop failed for {filename}: {e}")
            output_summary.append({
                "filename": filename,
                "status": "error",
                "message": f"Crop failed: {str(e)}"
            })
            continue

        # Split into lines (margins = 0 because we already cropped to region)
        try:
            line_images = crop_lines(
                cropped,
                gap_threshold=gap_threshold,
                min_line_height=min_line_height,
                padding=padding,
            )
        except Exception as e:
            logger.error(f"Line detection failed for {filename}: {e}")
            output_summary.append({
                "filename": filename,
                "status": "error",
                "message": f"Line detection failed: {str(e)}"
            })
            continue

        if not line_images:
            logger.warning(f"No lines detected in {filename}")
            output_summary.append({
                "filename": filename,
                "status": "no_lines",
                "message": "No text lines detected",
                "outputs": []
            })
            continue

        # Save each line
        stem = Path(filename).stem
        saved_paths = []
        for idx, line_img in enumerate(line_images, start=1):
            out_name = f"{stem}-{idx}.png"
            out_path = results_dir / out_name
            make_transparent(line_img).save(out_path)
            saved_paths.append(str(out_path))
            logger.info(f"Saved {out_path}")

        output_summary.append({
            "filename": filename,
            "status": "success",
            "lines": len(line_images),
            "outputs": saved_paths
        })
        logger.info(f"Finished {filename}: {len(line_images)} lines")

    return {"status": "completed", "results": output_summary}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
