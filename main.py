import requests
import os
import logging
import img2pdf

# ====================
# CONFIGURATIONS BELOW
# ====================
base_url = "" # Change this to change wich book to use. you are going to need to check it in the network tab
COOKIES = {}
scale = 4 # 1 to 4 i think. 4 Works garanteed biger number = bigger files = higher quality
# ====================
# CONFIGURATIONS ABOVE
# ====================

def download_image(session: requests.Session, url: str, filename: str) -> int:
    try:
        with session.get(url, timeout=15, stream=True) as r:
            if r.status_code != 200:
                return r.status_code

            content_type = r.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                return -3  # not an image (likely auth failed)

            with open(filename, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)

        return 0

    except requests.exceptions.RequestException:
        return -1
    except OSError:
        return -2

session = requests.Session()

# Attach cookies
session.cookies.update(COOKIES)

# Browser-like headers (important for Joomla/media endpoints)
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
})


ret = 500
for n in range(570):
    print(f"downloading {n}.png from {base_url}page_{n}/Scale{scale}.png")
    ret = download_image(session, base_url + f"page_{n}/Scale{scale}.png", f"{n}.png")
    print(f"downloaded {n}.png")
    
print(f"{ret}\n" if not ret == 0 else "", end = "")
print("Downloaded all files")

# ---------- Logging Setup ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ---------- Config ----------
FOLDER = "."  # folder containing PNGs
OUTPUT_PDF = "combined.pdf"


def collect_images(folder="."):
    """Collect all numbered PNGs sorted numerically."""
    files = [
        f for f in os.listdir(folder)
        if f.endswith(".png") and f[:-4].isdigit()
    ]
    files.sort(key=lambda x: int(x[:-4]))
    return files


def create_pdf(folder=".", output_pdf="combined.pdf"):
    image_files = collect_images(folder)

    if not image_files:
        log.error("No numbered PNG files found in folder %s", folder)
        return

    log.info("Found %d images", len(image_files))

    # Build full paths
    image_paths = [os.path.join(folder, f) for f in image_files]

    # Optional: print progress while feeding paths
    for idx, path in enumerate(image_paths, start=1):
        try:
            with Image.open(path) as im:
                log.info("[%d/%d] %s (%dx%d)", idx, len(image_paths), path, im.width, im.height)
        except Exception as e:
            log.warning("[%d/%d] Could not open %s: %s", idx, len(image_paths), path, e)

    # Create PDF (memory-efficient)
    try:
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(image_paths))
        log.info("PDF successfully created: %s", output_pdf)
    except Exception as e:
        log.exception("Failed to create PDF: %s", e)


from PIL import Image  # required for logging image sizes
create_pdf(FOLDER, OUTPUT_PDF)

image_files = collect_images(FOLDER)

for file in image_files:
    os.remove(file)
    
print("cleanup done")