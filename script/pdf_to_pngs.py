from pdf2image import pdfinfo_from_path, convert_from_path
import os

pdf_path = "data/shamarli.pdf"
output_dir = "data/shamarli"
dpi = 300

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Get the total number of pages in the PDF
info = pdfinfo_from_path(pdf_path)
total_pages = info["Pages"]

print(f"Total pages to process: {total_pages}")

# Process and save one page at a time
for page_num in range(1, total_pages + 1):
    print(f"Processing page {page_num}/{total_pages}")
    
    # Read only the specific page into memory
    images = convert_from_path(
        pdf_path, 
        dpi=dpi, 
        first_page=page_num, 
        last_page=page_num
    )
    
    # Save the page and release memory
    if images:
        img = images[0]
        # We use an f-string to ensure consistent naming if needed, 
        # e.g., 001.png for easier sorting
        save_path = os.path.join(output_dir, f"{page_num:03d}.png")
        img.save(save_path, "PNG")
