#!/usr/bin/env python3
"""
Zyxel USG Flex H Series - Diagnostics Collector

Connects to a Zyxel USG Flex H series device via HTTPS,
triggers diagnostics collection, and downloads the result.
"""

import argparse
import glob
import os
import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def find_bundled_browser():
    """Find Chromium browser bundled alongside the executable."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Look for chromium in a 'chromium' subdirectory next to executable
    chromium_dir = os.path.join(base_dir, "chromium")
    if os.path.isdir(chromium_dir):
        # Find the actual chrome executable
        for root, dirs, files in os.walk(chromium_dir):
            for f in files:
                if f in ("chrome", "chrome.exe", "Google Chrome for Testing"):
                    return os.path.join(root, f)
            for d in dirs:
                if d.endswith(".app"):
                    app_bin = os.path.join(
                        root, d, "Contents", "MacOS", "Google Chrome for Testing"
                    )
                    if os.path.isfile(app_bin):
                        return app_bin
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect diagnostics from Zyxel USG Flex H series device"
    )
    parser.add_argument("host", help="Device IP address (e.g. 192.168.1.1)")
    parser.add_argument("username", help="Admin username")
    parser.add_argument("password", help="Admin password")
    parser.add_argument(
        "-o", "--output-dir",
        default=".",
        help="Output directory for downloaded file (default: current directory)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=900,
        help="Max wait time in seconds for collection (default: 900)",
    )
    return parser.parse_args()


def log(msg):
    print(f"[cso_diag] {msg}", flush=True)


def run(args):
    base_url = f"https://{args.host}"
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        log("Launching browser...")
        bundled = find_bundled_browser()
        launch_opts = {"headless": True}
        if bundled:
            log(f"Using bundled browser: {bundled}")
            launch_opts["executable_path"] = bundled
        browser = p.chromium.launch(**launch_opts)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # ── Step 1: Login ──
        log(f"Connecting to {base_url} ...")
        page.goto(base_url, wait_until="networkidle", timeout=30000)

        # Wait for login form
        page.wait_for_selector('input[name="username"]', timeout=15000)
        log("Login page loaded. Logging in...")
        page.fill('input[name="username"]', args.username)
        page.fill('input[name="password"]', args.password)
        page.click('button:has-text("Login")')

        # Wait for dashboard to load
        try:
            page.wait_for_url("**/dashboard/**", timeout=15000)
        except PlaywrightTimeout:
            # Check if login failed
            body_text = page.text_content("body")
            if "login" in page.url.lower():
                log("ERROR: Login failed. Please check username/password.")
                browser.close()
                return False
            # Might be on a different page, continue anyway

        log("Login successful. Navigating to Diagnostics...")

        # ── Step 2: Navigate to Maintenance > Diagnostics ──
        page.click("text=Maintenance")
        page.wait_for_timeout(1500)
        page.click("text=Diagnostics")
        page.wait_for_timeout(5000)

        # Verify we're on diagnostics page
        if "diagnostics" not in page.url.lower():
            log("ERROR: Failed to navigate to Diagnostics page.")
            page.screenshot(path=os.path.join(output_dir, "error_nav.png"))
            browser.close()
            return False

        log("Diagnostics page loaded.")

        # ── Step 3: Check status and start collection ──
        def get_status():
            text = page.text_content("body")
            if "Data collection in progress" in text:
                return "collecting"
            if "Standby" in text:
                return "standby"
            return "unknown"

        status = get_status()
        if status == "collecting":
            log("A collection is already in progress. Waiting for it to finish...")
        elif status == "standby":
            log("Starting diagnostics collection...")
            page.click('button:has-text("Collect Now")')
            page.wait_for_timeout(3000)
            status = get_status()
            if status != "collecting":
                log("WARNING: Status did not change to 'collecting'. Current: " + status)
        else:
            log(f"WARNING: Unexpected status: {status}. Attempting to click Collect Now...")
            try:
                page.click('button:has-text("Collect Now")', timeout=5000)
                page.wait_for_timeout(3000)
                status = get_status()
            except PlaywrightTimeout:
                log("ERROR: Could not find 'Collect Now' button.")
                browser.close()
                return False

        # ── Step 4: Wait for collection to complete ──
        start_time = time.time()
        poll_interval = 10
        while status == "collecting":
            elapsed = int(time.time() - start_time)
            if elapsed > args.timeout:
                log(f"ERROR: Collection timed out after {args.timeout} seconds.")
                browser.close()
                return False
            remaining = args.timeout - elapsed
            log(f"Collecting... ({elapsed}s elapsed, timeout in {remaining}s)")
            page.wait_for_timeout(poll_interval * 1000)
            status = get_status()

        if status != "standby":
            log(f"ERROR: Unexpected status after collection: {status}")
            browser.close()
            return False

        log("Collection complete!")

        # ── Step 5: Get file info ──
        page.wait_for_timeout(2000)
        file_info = page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr');
            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 4) {
                    const name = cells[1]?.textContent?.trim();
                    if (name && name.includes('diaginfo')) {
                        return { name, size: cells[2]?.textContent?.trim() };
                    }
                }
            }
            return null;
        }""")

        if not file_info:
            log("ERROR: No diagnostics file found in the file list.")
            page.screenshot(path=os.path.join(output_dir, "error_nofile.png"))
            browser.close()
            return False

        filename = file_info["name"]
        size_bytes = int(file_info["size"])
        size_mb = size_bytes / (1024 * 1024)
        log(f"File ready: {filename} ({size_mb:.1f} MB)")

        # ── Step 6: Select file and download ──
        log("Selecting file and starting download...")

        # Click the checkbox in the row containing the file
        diag_row = page.locator('tr:has-text("diaginfo")')
        diag_row.locator('input[type="checkbox"]').click(force=True)
        page.wait_for_timeout(1000)

        # Start download
        with page.expect_download(timeout=120000) as download_info:
            page.click('text=Download')

        download = download_info.value
        dest_path = os.path.join(output_dir, download.suggested_filename)
        download.save_as(dest_path)

        log(f"Download complete: {dest_path}")
        log(f"File size: {os.path.getsize(dest_path) / (1024*1024):.1f} MB")

        # ── Cleanup ──
        browser.close()
        return True


def main():
    args = parse_args()
    success = run(args)
    if success:
        log("Done!")
        sys.exit(0)
    else:
        log("Failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
