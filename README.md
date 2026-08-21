# Download Klett Book

## 1) Install dependencies

```bash
pip install requests pillow img2pdf
```

## 2) Get values from browser

- `base_url`: the URL prefix that comes before `page_X/ScaleY.png`
- cookies: copy your browser cookies for the book page (DevTools → Application/Storage → Cookies)

## 3) Run

```bash
python main.py --base-url "https://example.com/path/" --cookies '{"cookie_name":"cookie_value"}'
```

## Useful options

- `--scale 4` image quality scale
- `--max-pages 570` max pages to try
- `--stop-after-failures 5` stop when many pages fail in a row
- `--output combined.pdf` output file name
- `--download-dir pages` where page images are stored
- `--keep-images` keep PNG files after PDF is created

If you skip `--base-url`, the script will ask for it interactively.
