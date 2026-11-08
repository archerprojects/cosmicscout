"""
Cosmic Scout — theme.py  (v1.1.0 — Monday 9 November 2026)

Two palettes, deliberately. The main app is LIGHT (the canonical #f8f8f6 series
carried from every prior version). The dashboard is a single dark "cockpit"
surface — the one place the app goes dark, by design decision. Nothing else
adopts the dark palette unless that decision is revisited.

Evidence-badge colours live here too so the dashboard, the legend, and every
Cosmos page grade content identically.
"""

# --- LIGHT: the main application shell and all pages except the dashboard ----
LIGHT = {
    "bg":        "#f8f8f6",   # light gray background
    "panel":     "#eeeeec",   # panel / card
    "input":     "#ffffff",   # input field
    "text":      "#1a1a1a",   # near-black primary text
    "input_txt": "#000000",
    "subtle":    "#555555",   # medium gray secondary
    "accent":    "#2e7d52",   # deep green accent
    "border":    "#c0c0bc",
    "neg":       "#8b2020",
    "warn":      "#c87820",
}

# --- DARK: the dashboard cockpit only ---------------------------------------
DARK = {
    "bg":     "#141428",
    "card":   "#1b1b34",
    "track":  "#2c2c4a",
    "text":   "#f2f2f7",
    "subtle": "#9a9ab8",
    "center": "#4a4a6a",
    "comp":   "#ff6b6b",
}

# --- evidence badges (mirror the evidence-spine spec) -----------------------
# Bright set: tuned for the DARK dashboard cockpit only.
BADGE_COLORS = {
    "VALIDATED":   "#3ecf8e",
    "EMERGING":    "#4aa8e0",
    "CONTESTED":   "#e0a03a",
    "TRADITIONAL": "#a98ad0",
    "REFUTED":     "#d05a5a",   # never shown as guidance; used only in myth-context
}

# Dark set: the SAME badges darkened for legibility on the LIGHT #f8f8f6 pages.
# Every light-background surface (Cycles, Patterns, Cosmos pages, legends) uses
# these; only the dashboard uses the bright set above.
BADGE_COLORS_LIGHT = {
    "VALIDATED":   "#1f8a5a",   # deep green — readable on white, not mint
    "EMERGING":    "#2a6fa0",   # deep blue
    "CONTESTED":   "#b06a10",   # amber-brown
    "TRADITIONAL": "#6a4a9a",   # deep violet
    "REFUTED":     "#a83232",   # deep red
}


def light_qss() -> str:
    """Base stylesheet for the light application shell."""
    L = LIGHT
    return f"""
        QWidget {{ background: {L['bg']}; color: {L['text']};
                   font-family: 'DejaVu Sans'; font-size: 14px; }}
        QLabel {{ background: transparent; }}
        QCheckBox {{ background: transparent; spacing: 8px; }}
        QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 7px;
                                border: 1px solid {L['border']}; background: {L['border']};
                                image: none; }}
        QCheckBox::indicator:hover {{ border-color: {L['accent']}; }}
        QCheckBox::indicator:checked {{ background: {L['accent']}; border-color: {L['accent']}; }}
        QLabel#Title {{ font-size: 18px; font-weight: bold; }}
        QLabel#Subtle {{ color: {L['subtle']}; }}
        QFrame#Card {{ background: {L['panel']}; border: 1px solid {L['border']};
                       border-radius: 10px; }}
        QPushButton {{ background: {L['panel']}; border: 1px solid {L['border']};
                       border-radius: 6px; padding: 6px 12px; }}
        QPushButton:hover {{ border-color: {L['accent']}; }}
    """
