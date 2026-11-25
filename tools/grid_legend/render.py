"""La legenda del grid: docs/SAGGA-GRID-LEGENDA.pdf e la sua prima pagina, docs/grid-legenda.png.

    python3 tools/grid_legend/render.py

Il testo sta in legend_data.js, il disegno delle pagine in legenda.html. Serve Playwright con il suo Chromium
(pip install playwright; python3 -m playwright install chromium) e il font Inter; senza Inter Chromium usa
DejaVu Sans e le righe vanno a capo in altri punti.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PDF = REPO / "docs" / "SAGGA-GRID-LEGENDA.pdf"
PNG = REPO / "docs" / "grid-legenda.png"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1122, "height": 793})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((HERE / "legenda.html").as_uri())
        page.wait_for_selector('body[data-ready="1"]', timeout=30000)
        if errors:
            sys.exit("legenda.html: " + errors[0])
        page.emulate_media(media="screen")
        pages = page.locator("section.page")
        n = pages.count()
        pages.first.screenshot(path=str(PNG))
        # A4 landscape, no margins: a page of the HTML (1122 x 793 px) is a page of the PDF
        page.pdf(path=str(PDF), width="297mm", height="210mm", print_background=True, prefer_css_page_size=True,
                 margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, outline=True, tagged=True)
        browser.close()
    print(f"{PDF.relative_to(REPO)}: {n} pagine; {PNG.relative_to(REPO)}: la prima")


if __name__ == "__main__":
    main()
