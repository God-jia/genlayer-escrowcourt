"""Capture fresh EscrowCourt dApp screenshots for the demo video.

Usage: python tools/shoot.py <track-address>

Drives the locally installed Chrome (headless) with Playwright against the live
GitHub Pages build and writes JPEGs into tools/shots.
"""

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

TOOLS = pathlib.Path(__file__).resolve().parent
SHOTS = TOOLS / "shots"
SHOTS.mkdir(exist_ok=True)
ADDRESS = json.loads((TOOLS / "deployment.json").read_text(encoding="utf-8"))["contract"]
URL = "https://god-jia.github.io/genlayer-escrowcourt/"


def shot(page, name):
    """Screenshot clipped to the page content so there is no dead space."""
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(120)
    content_bottom = page.evaluate(
        "() => Math.ceil(document.querySelector('main').getBoundingClientRect().bottom) + 28"
    )
    view = page.viewport_size
    height = int(min(view["height"], content_bottom))
    page.screenshot(
        path=str(SHOTS / name),
        type="jpeg",
        quality=92,
        clip={"x": 0, "y": 0, "width": view["width"], "height": height},
    )
    print("  wrote", name, "height", height)


def main():
    freelancer = sys.argv[1] if len(sys.argv) > 1 else ""

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1120}, device_scale_factor=2
        )
        page.goto(URL, wait_until="load", timeout=60000)
        page.wait_for_selector('.tab[data-tab="post"]', timeout=60000)

        page.fill("#contract", ADDRESS)
        page.click("#saveContract")
        page.wait_for_timeout(2500)

        print("capturing...")
        shot(page, "escrow-1-post.jpg")

        page.click('.tab[data-tab="job"]')
        page.fill("#jId", "0")
        page.click("#loadJob")
        page.wait_for_selector("#jView .milestone", timeout=90000)
        page.wait_for_timeout(900)
        page.fill("#jId", "0")
        shot(page, "escrow-2-workspace.jpg")

        page.locator("#jView .milestone").first.screenshot(
            path=str(SHOTS / "escrow-5-ruling.jpg"), type="jpeg", quality=92
        )
        print("  wrote escrow-5-ruling.jpg")

        page.click('.tab[data-tab="adjudicate"]')
        page.fill("#aId", "0")
        page.wait_for_timeout(500)
        shot(page, "escrow-3-adjudicate.jpg")

        page.click('.tab[data-tab="track"]')
        if freelancer:
            page.fill("#tAddress", freelancer)
        page.click("#loadTrack")
        page.wait_for_selector("#tView .kv", timeout=90000)
        page.wait_for_timeout(700)
        shot(page, "escrow-4-track.jpg")

        browser.close()

    print("done")


if __name__ == "__main__":
    main()