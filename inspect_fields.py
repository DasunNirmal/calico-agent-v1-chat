import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://calico.datatree.com/"
PROFILE = Path("browser-profile")
REPORT = Path("field_inspection.json")


def inspect_page(page):
    return page.evaluate("""() => {
        const visible = (el) => {
            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el);

            return (
                r.width > 0 &&
                r.height > 0 &&
                s.display !== "none" &&
                s.visibility !== "hidden" &&
                Number(s.opacity) > 0
            );
        };

        const rectOf = (el) => {
            const r = el.getBoundingClientRect();
            return {
                x: Math.round(r.x),
                y: Math.round(r.y),
                width: Math.round(r.width),
                height: Math.round(r.height)
            };
        };

        const describe = (el) => {
            const s = getComputedStyle(el);

            return {
                tag: el.tagName.toLowerCase(),
                id: el.id || "",
                className: typeof el.className === "string"
                    ? el.className
                    : "",
                role: el.getAttribute("role") || "",
                title: el.getAttribute("title") || "",
                ariaLabel: el.getAttribute("aria-label") || "",
                backgroundColor: s.backgroundColor,
                color: s.color,
                borderColor: s.borderColor,
                position: s.position,
                ...rectOf(el)
            };
        };

        const cleanText = (value) =>
            (value || "").replace(/\\s+/g, " ").trim();

        // 1. Existing form-control inspection.
        // Do not read values, placeholders or document contents.
        const controls = Array.from(
            document.querySelectorAll(
                "input, textarea, select, button"
            )
        )
        .filter(visible)
        .map(el => {
            const s = getComputedStyle(el);

            return {
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute("type") || "",
                id: el.id || "",
                name: el.getAttribute("name") || "",
                className: typeof el.className === "string"
                    ? el.className
                    : "",
                ariaLabel: el.getAttribute("aria-label") || "",
                title: el.getAttribute("title") || "",
                disabled: !!el.disabled,
                readOnly: !!el.readOnly,
                backgroundColor: s.backgroundColor,
                color: s.color,
                borderColor: s.borderColor,
                ...rectOf(el)
            };
        });

        // 2. Visible UI labels and headings.
        // Excludes form controls and their entered values.
        const labelSelector = [
            "label",
            "legend",
            "h1", "h2", "h3", "h4", "h5", "h6",
            "button",
            "a",
            "[role='heading']",
            "[role='button']",
            "[aria-label]",
            "[title]",
            ".label",
            ".title",
            ".heading",
            ".navbar",
            ".toolbar"
        ].join(",");

        const uiLabels = Array.from(
            document.querySelectorAll(labelSelector)
        )
        .filter(visible)
        .map(el => ({
            text: cleanText(el.innerText || el.textContent).slice(0, 180),
            ...describe(el)
        }))
        .filter(item => item.text || item.ariaLabel || item.title);

        // 3. Short visible text elements.
        // Only inspect elements outside form controls.
        const textElements = Array.from(
            document.querySelectorAll("body *")
        )
        .filter(el => {
            if (!visible(el)) return false;

            if (el.matches(
                "input, textarea, select, option, script, style"
            )) return false;

            if (el.closest("input, textarea, select")) return false;

            const text = cleanText(el.innerText || "");

            if (!text || text.length > 120) return false;

            // Avoid collecting duplicate parent text.
            return !Array.from(el.children).some(child =>
                cleanText(child.innerText || "") === text
            );
        })
        .map(el => ({
            text: cleanText(el.innerText || ""),
            ...describe(el)
        }));

        // 4. Right-side workflow label candidates.
        const screenWidth = window.innerWidth;

        const rightSideCandidates = textElements.filter(item =>
            item.x > screenWidth * 0.55 &&
            item.y < 350
        );

        // 5. Elements in the top toolbar region.
        // Keep all visible non-transparent background candidates.
        const toolbarCandidates = Array.from(
            document.querySelectorAll("body *")
        )
        .filter(el => {
            if (!visible(el)) return false;

            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el);

            const isNearTop = r.y >= 0 && r.y < 180;
            const hasSize = r.width > 80 && r.height > 12;
            const hasBackground =
                s.backgroundColor !== "rgba(0, 0, 0, 0)" &&
                s.backgroundColor !== "transparent";

            return isNearTop && hasSize && hasBackground;
        })
        .map(el => ({
            ...describe(el),
            text: cleanText(el.innerText || "").slice(0, 100)
        }))
        .sort((a, b) => {
            // Wider toolbar-like elements appear first.
            return b.width - a.width;
        })
        .slice(0, 100);

        return {
            pageTitle: document.title,
            pageURL: location.href,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            bodyClass: document.body.className,

            summary: {
                controls: controls.length,
                uiLabels: uiLabels.length,
                textElements: textElements.length,
                rightSideCandidates: rightSideCandidates.length,
                toolbarCandidates: toolbarCandidates.length
            },

            controls,
            uiLabels,
            textElements,
            rightSideCandidates,
            toolbarCandidates
        };
    }""")


def main():
    PROFILE.mkdir(exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE.resolve()),
            headless=False,
            viewport={
                "width": 1600,
                "height": 1000
            }
        )

        page = context.pages[0] if context.pages else context.new_page()

        page.goto(URL, wait_until="domcontentloaded")

        print("\nCalico opened.")
        print("Log in if necessary.")
        print("Open an authorised, non-sensitive test record.")
        print("Wait until the record and toolbar finish loading.")

        input("\nPress ENTER to inspect the current screen...")

        report = inspect_page(page)

        REPORT.write_text(
            json.dumps(report, indent=4),
            encoding="utf-8"
        )

        print("\n========== INSPECTION SUMMARY ==========")
        print(json.dumps(report["summary"], indent=4))

        print("\n========== RIGHT-SIDE TEXT ==========")
        for item in report["rightSideCandidates"]:
            print(
                f"Text: {item['text']!r} | "
                f"Class: {item['className']} | "
                f"Background: {item['backgroundColor']} | "
                f"Position: ({item['x']}, {item['y']})"
            )

        print("\n========== TOP TOOLBAR CANDIDATES ==========")
        for item in report["toolbarCandidates"][:30]:
            print(
                f"Tag: {item['tag']} | "
                f"ID: {item['id']} | "
                f"Class: {item['className']} | "
                f"Background: {item['backgroundColor']} | "
                f"Position: ({item['x']}, {item['y']}) | "
                f"Size: ({item['width']} x {item['height']})"
            )

        print(f"\nFull report saved to: {REPORT.resolve()}")

        input("\nPress ENTER to close the browser...")

        context.close()


if __name__ == "__main__":
    main()