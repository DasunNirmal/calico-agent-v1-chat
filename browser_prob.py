
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("screenshots")
BROWSER_PROFILE = Path("browser-profile")


def main():
    url = input("Enter your authorised Calico URL: ").strip()
    url = url.strip("'\"")

    if not url.startswith(("https://", "http://")):
        print("Please enter a valid HTTP or HTTPS URL.")
        return

    SCREENSHOT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as playwright:
        browser_context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
            viewport={"width": 1600, "height": 1000},
        )

        try:
            page = (
                browser_context.pages[0]
                if browser_context.pages
                else browser_context.new_page()
            )

            page.goto(url, wait_until="domcontentloaded")

            print("\nBrowser opened.")
            print("Log in manually if necessary.")
            print("Open an authorised, non-sensitive test record.")
            input("\nPress Enter here when the test screen is ready...")

            print("\n--- Browser inspection ---")
            print("Page title:", page.title())
            print("Current URL:", page.url)

            selectors = {
                "Input fields": "input",
                "Text areas": "textarea",
                "Dropdowns": "select",
                "Buttons": "button",
                "Dialog boxes": '[role="dialog"]',
                "Elements with textbox role": '[role="textbox"]',
                "Elements with combobox role": '[role="combobox"]',
            }

            for label, selector in selectors.items():
                try:
                    count = page.locator(selector).count()
                    print(f"{label}: {count}")
                except Exception:
                    print(f"{label}: inspection unavailable")

            screenshot_path = SCREENSHOT_DIR / "browser-screen.png"
            page.screenshot(path=str(screenshot_path))

            print("\nScreenshot saved locally:")
            print(screenshot_path.resolve())
            print("\nInspection complete. No fields were edited or submitted.")

        finally:
            browser_context.close()


if __name__ == "__main__":
    main()
