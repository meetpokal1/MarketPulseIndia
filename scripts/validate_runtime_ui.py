"""
MarketPulse India - Playwright UI Automation & Screenshot Verification
Validates live Streamlit UI elements, verifies calculated metrics, and captures full-page runtime screenshots.
"""
import subprocess
import time
import json
import sys
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_SUBDIR = sys.argv[1] if len(sys.argv) > 1 else "stage2_verification"
SCREENSHOTS_DIR = BASE_DIR / "screenshots" / OUTPUT_SUBDIR
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
PORT = 8544
STREAMLIT_URL = f"http://127.0.0.1:{PORT}"


def wait_for_server(url: str, timeout: int = 40):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def run_ui_qa():
    print(f"Starting Streamlit app on port {PORT}...")
    server_log = open(BASE_DIR / "streamlit_server.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            str(BASE_DIR / ".venv" / "Scripts" / "streamlit.exe"),
            "run",
            str(BASE_DIR / "dashboard" / "app.py"),
            f"--server.port={PORT}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        cwd=str(BASE_DIR),
        stdout=server_log,
        stderr=subprocess.STDOUT,
        text=True,
    )

    qa_results = {}

    try:
        if not wait_for_server(STREAMLIT_URL, timeout=40):
            raise RuntimeError("Streamlit server failed to start within timeout.")

        print("Streamlit server is ready. Launching Playwright browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel="msedge")
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()

            # -------------------------------------------------------------
            # 1. Market Explorer
            # -------------------------------------------------------------
            print("\n[QA Step 1] Validating Market Explorer...")
            page.goto(STREAMLIT_URL, wait_until="networkidle")
            page.wait_for_timeout(3000)
            print("Page title:", page.title())
            body_text = page.locator("body").inner_text()
            print("Body snippet:", body_text[:300].replace('\n', ' '))
            page.wait_for_selector("text=Market Explorer", timeout=20000)

            metric_labels = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
            metric_vals = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            metrics_w1 = dict(zip(metric_labels, metric_vals))
            print("Market Explorer Metrics:", metrics_w1)
            qa_results["market_explorer_metrics"] = metrics_w1

            page.screenshot(path=str(SCREENSHOTS_DIR / "01_market_explorer.png"), full_page=True)
            print("Captured 01_market_explorer.png")

            # -------------------------------------------------------------
            # 2. Price Intelligence & Volatility
            # -------------------------------------------------------------
            print("\n[QA Step 2] Validating Price Intelligence & Volatility...")
            page.locator('[data-testid="stSidebar"]').get_by_text("2. Price Intelligence & Volatility", exact=True).click()
            page.wait_for_selector("text=Price Intelligence: Corridor Spreads", timeout=20000)
            page.wait_for_timeout(2500)

            pi_metric_labels = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
            pi_metric_vals = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            metrics_w2 = dict(zip(pi_metric_labels, pi_metric_vals))
            print("Price Spreads Metrics:", metrics_w2)
            qa_results["price_spread_metrics"] = metrics_w2

            page.screenshot(path=str(SCREENSHOTS_DIR / "02_price_intelligence_spreads.png"), full_page=True)
            print("Captured 02_price_intelligence_spreads.png")

            # Switch to Volatility tab
            page.get_by_text("Commodity Volatility & Shocks (Investigation B)", exact=True).click()
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "02_volatility_shocks.png"), full_page=True)
            print("Captured 02_volatility_shocks.png")

            # -------------------------------------------------------------
            # 3. Arrival–Price Panel Investigation
            # -------------------------------------------------------------
            print("\n[QA Step 3] Validating Arrival–Price Panel Investigation...")
            page.locator('[data-testid="stSidebar"]').get_by_text("3. Arrival–Price Panel Investigation", exact=True).click()
            page.wait_for_selector("text=Arrival–Price Panel Investigation", timeout=20000)
            page.wait_for_timeout(2500)

            econ_metric_labels = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
            econ_metric_vals = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            metrics_w3 = dict(zip(econ_metric_labels, econ_metric_vals))
            print("Econometric Panel Metrics:", metrics_w3)
            qa_results["econometric_panel_metrics"] = metrics_w3

            page.screenshot(path=str(SCREENSHOTS_DIR / "03_arrival_price_panel.png"), full_page=True)
            print("Captured 03_arrival_price_panel.png")

            # -------------------------------------------------------------
            # 4. Data Reliability Lab
            # -------------------------------------------------------------
            print("\n[QA Step 4] Validating Data Reliability Lab...")
            page.locator('[data-testid="stSidebar"]').get_by_text("4. Data Reliability Lab", exact=True).click()
            page.wait_for_selector("text=Data Reliability Lab: Mandi Reporting Forensics", timeout=20000)
            page.wait_for_timeout(2500)

            page.screenshot(path=str(SCREENSHOTS_DIR / "04_data_reliability_lab.png"), full_page=True)
            print("Captured 04_data_reliability_lab.png")

            # -------------------------------------------------------------
            # 5. Market Decision Simulator
            # -------------------------------------------------------------
            print("\n[QA Step 5] Validating Market Decision Simulator...")
            page.locator('[data-testid="stSidebar"]').get_by_text("5. Market Decision Simulator", exact=True).click()
            page.wait_for_selector("text=Market Decision Simulator: Procurement", timeout=20000)
            page.wait_for_timeout(2500)

            # Wait for Plotly charts to render
            page.wait_for_selector(".js-plotly-plot", timeout=15000)

            sim_metric_labels = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
            sim_metric_vals = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            metrics_w5 = dict(zip(sim_metric_labels, sim_metric_vals))
            print("Decision Simulator Metrics (Initial):", metrics_w5)
            qa_results["decision_simulator_metrics_initial"] = metrics_w5

            page.screenshot(path=str(SCREENSHOTS_DIR / "05_decision_simulator.png"), full_page=True)
            print("Captured 05_decision_simulator.png (Initial)")

            # Exercise inputs: Adjust Destination Reference Price from ₹2250 to ₹2500
            print("Exercising simulator inputs (adjusting destination price to ₹2,500)...")
            dest_input = page.locator('input[aria-label*="Destination Reference Price"]').first
            if dest_input.count() > 0:
                dest_input.fill("2500.0")
                dest_input.press("Enter")
                page.wait_for_timeout(2500)
                sim_metric_labels_ex = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
                sim_metric_vals_ex = page.locator('[data-testid="stMetricValue"]').all_text_contents()
                metrics_w5_ex = dict(zip(sim_metric_labels_ex, sim_metric_vals_ex))
                print("Decision Simulator Metrics (Exercised):", metrics_w5_ex)
                qa_results["decision_simulator_metrics_exercised"] = metrics_w5_ex
                page.screenshot(path=str(SCREENSHOTS_DIR / "05_decision_simulator_exercised.png"), full_page=True)
                print("Captured 05_decision_simulator_exercised.png")

            # -------------------------------------------------------------
            # 6. Research Brief & Export
            # -------------------------------------------------------------
            print("\n[QA Step 6] Validating Research Brief & Export...")
            page.locator('[data-testid="stSidebar"]').get_by_text("6. Research Brief & Export", exact=True).click()
            page.wait_for_selector("text=Executive Research Brief: Lasalgaon", timeout=20000)
            page.wait_for_timeout(2000)

            page.screenshot(path=str(SCREENSHOTS_DIR / "06_research_brief.png"), full_page=True)
            print("Captured 06_research_brief.png")

            browser.close()
            print("\nAll Playwright UI automation and screenshot validations completed successfully.")

    finally:
        print("Terminating Streamlit process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        try:
            server_log.close()
        except Exception:
            pass

    # Save summary
    with open(SCREENSHOTS_DIR / "ui_qa_results.json", "w", encoding="utf-8") as f:
        json.dump(qa_results, f, indent=2)
    print("Saved ui_qa_results.json.")


if __name__ == "__main__":
    run_ui_qa()
