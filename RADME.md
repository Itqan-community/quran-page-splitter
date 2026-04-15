# Quran Page Splitter

This project is a web application that allows users to upload a Quran page and split it into individual lines.

## Usage

1. install dependencies

   ```bash
   uv sync
   ```

   > Make sure you have `uv` installed.

2. Run the server

   ```bash
   uv run server.py
   ```

3. Open the page `http://0.0.0.0:8000`

4. Press brows or drag and drop the images.

5. The first page will appear to a cropping area to specify the page content (by removing the border).

6. Press `Start Cropping`. A preview will appear to help you to specify the area correctly. Also, you can adjust the cordinates (left, top, width, and height) from the inputs in the toolbar section above the preview area.

7. After you finishPress `Upload ALL`.

8. A post request with all the files and the cropping coordinates will be sent to the server that will handle the splitting and the results will be saved in the `results` directory.

## Issues

1. Some mushaf have different margins for odd and even pages, so we need to handle that.
2. Testing it with a mushaf with 523 page (shamarli mushaf) took about 23 minutes, which is too long. We need to optimize it.
3. In the same mushaf (shamarli), the sura header (the decoration with the name of the sura in it) has what is consered as an empty line according to the algorithm used here. So, we also, need to take a different approach to make this part of the page is handled differently and cropped correctly.
4. Currently, this app handles the mushaf starting from page 3, since the first two pages have different bordering and usually the text is inside an oval shape which is hard to crop using a rectangle coordinates. This will be handled separetly.
5. When uploading the images in the browser, you will notice the need to select them twice. I do not know the cause of this issue, but I will try to debug it.

## Helpers

### [pdf_to_pngs](./script/pdf_to_pngs.py)

This script converts a PDF file to a series of PNG images, one for each page.
Since usually you find the mushaf in a PDF format and if you find it in pngs, it will be hard to download all at once.

You can use it by running:

```bash
uv run scripts/pdf_to_pngs.py
```

Currently, you need to go to the script and adjust the file path because it is hard coded. This will be changed later.
