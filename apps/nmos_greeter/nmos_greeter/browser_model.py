from __future__ import annotations

# Available browser choices presented to the user during setup.
# "skip" means the user will decide later from the desktop.
BROWSER_OPTIONS = ["firefox-esr", "chromium", "skip"]

BROWSER_LABELS = {
    "firefox-esr": "Firefox",
    "chromium": "Chromium",
    "skip": "Skip - I'll choose later",
}

BROWSER_DESCRIPTIONS = {
    "firefox-esr": "Open-source browser by Mozilla. Works with Tor-first networking.",
    "chromium": "Open-source browser by Google. Fast and widely compatible.",
    "skip": "No default browser will be set. You can change this later from the desktop.",
}

DEFAULT_BROWSER = "firefox-esr"


def browser_label(browser_id: str) -> str:
    return BROWSER_LABELS.get(browser_id, browser_id)


def browser_description(browser_id: str) -> str:
    return BROWSER_DESCRIPTIONS.get(browser_id, "")


def browser_label_list() -> list[str]:
    return [BROWSER_LABELS[b] for b in BROWSER_OPTIONS]


def resolve_browser(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in BROWSER_OPTIONS else DEFAULT_BROWSER
