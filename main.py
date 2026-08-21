import argparse
import json
import logging
import os
from pathlib import Path

import img2pdf
import requests
from PIL import Image


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a Klett book and combine pages into a PDF.")
    parser.add_argument("--base-url", help="Book base URL ending before page_X/ScaleY.png.")
    parser.add_argument(
        "--cookies",
        default="{}",
        help='Cookies as JSON, e.g. \'{"JSESSIONID":"...","cookie2":"..."}\'.',
    )
    parser.add_argument("--scale", type=int, default=4, help="Image scale (usually 1-4). Default: 4")
    parser.add_argument("--max-pages", type=int, default=570, help="Maximum pages to try. Default: 570")
    parser.add_argument(
        "--stop-after-failures",
        type=int,
        default=5,
        help="Stop after N consecutive failed page downloads. Default: 5",
    )
    parser.add_argument("--output", default="combined.pdf", help="Output PDF file name. Default: combined.pdf")
    parser.add_argument(
        "--download-dir",
        default="pages",
        help="Directory to save downloaded images. Default: pages",
    )
    parser.add_argument("--keep-images", action="store_true", help="Keep PNG files after PDF creation.")
    return parser.parse_args()


def prompt_if_missing(value: str | None, prompt: str) -> str:
    if value:
        return value.strip()
    return input(prompt).strip()


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip()
    return base_url if base_url.endswith("/") else base_url + "/"


def parse_cookies(cookie_json: str) -> dict:
    try:
        cookies = json.loads(cookie_json)
        if not isinstance(cookies, dict):
            raise ValueError
        return cookies
    except (json.JSONDecodeError, ValueError):
        raise ValueError("Invalid cookies JSON. Expected an object like {\"name\":\"value\"}.")


def download_image(session: requests.Session, url: str, filename: Path) -> int:
    try:
        with session.get(url, timeout=15, stream=True) as response:
            if response.status_code != 200:
                return response.status_code

            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                return -3

            with filename.open("wb") as output:
                for chunk in response.iter_content(8192):
                    if chunk:
                        output.write(chunk)
        return 0
    except requests.exceptions.RequestException:
        return -1
    except OSError:
        return -2


def collect_images(folder: Path) -> list[Path]:
    files = [f for f in folder.iterdir() if f.name.endswith(".png") and f.stem.isdigit()]
    files.sort(key=lambda x: int(x.stem))
    return files


def create_pdf(image_paths: list[Path], output_pdf: Path) -> bool:
    if not image_paths:
        log.error("No numbered PNG files found.")
        return False

    log.info("Found %d images", len(image_paths))
    for idx, path in enumerate(image_paths, start=1):
        try:
            with Image.open(path) as image:
                log.info("[%d/%d] %s (%dx%d)", idx, len(image_paths), path.name, image.width, image.height)
        except Exception as error:
            log.warning("[%d/%d] Could not open %s: %s", idx, len(image_paths), path.name, error)

    try:
        with output_pdf.open("wb") as output:
            output.write(img2pdf.convert([str(p) for p in image_paths]))
        log.info("PDF successfully created: %s", output_pdf)
        return True
    except Exception as error:
        log.exception("Failed to create PDF: %s", error)
        return False


def main() -> int:
    args = parse_args()
    base_url = normalize_base_url(prompt_if_missing(args.base_url, "Enter base URL: "))
    if not base_url:
        log.error("Base URL is required.")
        return 1

    try:
        cookies = parse_cookies(args.cookies)
    except ValueError as error:
        log.error("%s", error)
        return 1

    download_dir = Path(args.download_dir)
    output_pdf = Path(args.output)
    download_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
    )

    consecutive_failures = 0
    success_count = 0
    for page in range(args.max_pages):
        page_url = f"{base_url}page_{page}/Scale{args.scale}.png"
        image_path = download_dir / f"{page}.png"
        print(f"Downloading page {page}: {page_url}")
        result = download_image(session, page_url, image_path)

        if result == 0:
            success_count += 1
            consecutive_failures = 0
            print(f"Saved {image_path}")
            continue

        consecutive_failures += 1
        print(f"Failed page {page} (code: {result})")
        if consecutive_failures >= args.stop_after_failures:
            print(f"Stopping after {consecutive_failures} consecutive failures.")
            break

    if success_count == 0:
        log.error("No pages were downloaded. Check base URL/cookies/scale.")
        return 1

    image_files = collect_images(download_dir)
    if not create_pdf(image_files, output_pdf):
        return 1

    if not args.keep_images:
        for file in image_files:
            file.unlink(missing_ok=True)
        print("Cleanup done.")
    else:
        print(f"Kept images in: {download_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())