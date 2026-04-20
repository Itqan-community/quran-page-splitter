# Quran Page Splitter

A web application and CLI tool designed to process Mushaf (Quran) pages, intelligently crop the page bounds, automatically detect text lines, and classify Sura name decorations. It exports each line as a separate, transparent PNG image.

This project is built for developers or data engineers who need to process datasets of Quran pages into line-by-line images.

## Architecture

- **Backend**: FastAPI server orchestrating image processing via Python (`Pillow`, `NumPy`, `OpenCV`).
- **Frontend**: A vanilla HTML/JS/CSS dual-panel workspace for visual crop alignment and parameter tuning.
- **Core Algorithm**: Uses horizontal projection profiles (row sums) to detect gaps between text lines, combined with `cv2.matchTemplate` to classify special elements like Sura name borders.

---

## 🚀 Getting Started

### 1. Install Dependencies

This project uses `uv` for fast dependency management.

```bash
uv sync
```

### 2. Start the Server

```bash
uv run server.py
```

The server will start on `http://0.0.0.0:8000`.

---

## 🖥️ Using the Frontend UI

The web interface is the easiest way to visually determine the correct crop coordinates and line detection parameters before processing your dataset.

1. **Upload Images**: Drag and drop your page images into the drop zone. _(Note: The frontend allows queueing up to 610 images)._
2. **Set the Targets**:
   - In the toolbar, you will see a dropdown for `Target` (`bounds`, `sura_name`, `aya_separator`).
   - For **`bounds`**: Draw a rectangle around the main text body of the page to crop out the outer margins.
   - For **`sura_name`**: Draw a tight box around a Sura name decoration. This is used as a template to classify Sura headers vs. regular text lines.
   - For **`aya_separator`**: Draw a tight box around an Aya separator ornament. The backend removes the embedded number and uses this template to split detected lines by separator occurrences.
3. **Adjust Parameters**: In the toolbar, you can tweak the line detection algorithms and choose whether pages alternate horizontal margins (see **Algorithm Parameters** below).
4. **Upload All**: Once you have defined your bounds and templates, press `↑ Upload all`. The backend will process every page in the queue and save the results into the `results/` directory.

> **💡 Best Practice: Testing the Output**
> Before uploading hundreds of pages, upload just **1 or 2 representative pages** in the UI. Set your bounds, templates, and parameters, then hit Upload. Check the `results/` folder to ensure lines are splitting correctly and Sura names are properly classified. If lines are merging, you may need to tweak the `Gap thr.` or `Min height`.

---

## ⚙️ Algorithm Parameters

Whether you use the UI or the CLI, the processing pipeline relies on a few critical parameters.

### 1. Crop Coordinates (`crop_x`, `crop_y`, `crop_w`, `crop_h`)

The bounding box of the actual text area on the page. Everything outside this box is discarded before line detection begins.

### 2. Line Detection Parameters

- **`gap_threshold`** _(default: `0.03`)_: Determines how aggressive the line-splitter is. It looks for rows of pixels where the density of text drops below this percentage of the maximum row density.
  - _Increase it_ (e.g., `0.05`) if lines are merging together.
  - _Decrease it_ (e.g., `0.01`) if single lines are being split in half horizontally (e.g., splitting dots from letters).
- **`min_line_height`** _(default: `20`)_: The minimum height (in pixels) a detected band must have to be considered a valid line. Filters out tiny artifacts, dust, or very small stray marks.
- **`padding`** _(default: `4`)_: Number of pixels added to the top and bottom of each detected line before it is cropped and saved. Helps preserve vertical flourishes of Arabic calligraphy.
- **`Alternate margins`** _(default: off)_: When enabled, the crop is mirrored horizontally on every other page, starting from the first page in the upload list. Files are sorted by filename in the frontend before upload, so pages like `001.png`, `002.png` are processed in natural order.

### 3. Sura Template Matching

The backend uses a two-stage classifier to identify Sura name headers:

1. **Height Filter**: It flags any line that is significantly taller (>1.5x) than the median line height on the page.
2. **Template Match**: It takes the left 15% of your provided `sura_name` crop and runs `cv2.matchTemplate` against the candidate line. If the score is ≥ `0.5`, it classifies the line as a Sura name.

- _Output_: Classified Sura lines are saved as `{page}-sura-{idx}.png`.

### 4. Aya Separator Splitting

After line detection, each non-sura line is processed with the uploaded `aya_separator` template:

1. The separator template is cleaned to remove the number in the center.
2. Short lines are trimmed from left/right empty margins.
3. Repeated separator occurrences are detected and each line is split into segments.
4. Each split keeps the separator in the preceding segment.

If no separator is detected in a line, the line is kept as one output image.

- _Output naming_:
  - Unsplit line: `{page}-l001.png`
  - Split segment: `{page}-l001-s01.png`
  - Sura line: `{page}-sura-01.png`

---

## 💻 CLI Usage

If you already know your parameters, you can bypass the server and process pages directly using the CLI:

```bash
uv run main.py path/to/page.png output_dir/ \
  --crop-x 330 --crop-y 300 --crop-w 1844 --crop-h 2860 \
  --gap-threshold 0.03 \
  --min-line-height 20 \
  --padding 4
```

---

## 🛠️ Helper Scripts

### PDF to PNG Extractor

Usually, Mushafs are distributed as PDF files. You can use the provided script to extract them into PNGs for processing:

```bash
uv run script/pdf_to_pngs.py
```

_(Note: Edit the script manually to set your specific input PDF path and output directory)._

---

## 🚧 Known Issues & Future Improvements

1. **Odd/Even Margins**: Some Mushafs have different margins for odd and even pages. Currently, the UI applies a single uniform crop.
2. **Performance**: Processing a massive Mushaf (500+ pages) synchronously takes time. Future iterations could use multiprocessing or asynchronous background tasks.
3. **First Pages**: The first two pages of a Mushaf (Al-Fatiha and Al-Baqarah) are usually heavily decorated inside oval or circular borders. The current rectangle-based bounding box does not handle these cleanly; they should be processed manually or via a separate pipeline.
