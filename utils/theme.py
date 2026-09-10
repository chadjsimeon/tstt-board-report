"""Light/dark report styling for the board pack.

The pages are written in the DARK palette. That is the source of truth: on the
dark theme nothing in here does any work. The light theme is derived by mapping
each dark colour literal to its light counterpart as the page renders, so there
is only ever one copy of the dashboard to keep in step.

Why dark is the source and not light: the light design collapses ten different
dark greys onto ``#5B6675`` and 71 uses of ``white`` onto ``#1F2328``, so
light -> dark cannot be recovered mechanically. dark -> light is 1:1.

Why the hook is central rather than a palette that every page imports: the
colours are hardcoded across sixteen pages, inside inline HTML and Plotly
figures -- roughly five hundred sites in the files that produce the board pack.
Wrapping ``markdown`` and ``plotly_chart`` once leaves those pages untouched.

COLOUR_MAP was extracted mechanically from commit 6cdad52 ("Switch the
dashboard to a light theme"): for every line that commit changed, the Nth
colour on the dark side pairs with the Nth colour on the light side. It is the
reviewed light design, not a fresh guess at one. Pairs for pages recoloured
outside that commit (DPDI, Export, Rev by LOB) are marked below.

Adding a colour to a page: a dark literal that is missing from the map renders
unchanged on the light theme, which on white usually means invisible. Add the
pair here at the same time.
"""
import re

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

DARK, LIGHT = "dark", "light"
THEMES = (DARK, LIGHT)
LABELS = {DARK: "Dark (PowerPoint)", LIGHT: "Light (Word)"}
_KEY = "report_theme"

# Background each theme is captured on, for the exporters' slide/page fill.
BACKGROUND_RGB = {DARK: (0, 0, 0), LIGHT: (255, 255, 255)}

# dark literal -> light literal. Keys are lower-case; values keep their case.
COLOUR_MAP = {
    "#000000": "#FFFFFF",
    "#00aa55": "#00875A",
    "#00cc55": "#00875A",
    "#00d4a0": "#00786C",
    "#00e676": "#00875A",
    "#00ff88": "#00875A",
    "#00ff8855": "#00875A55",
    "#00ff8866": "#00875A66",
    "#0d0d1a": "#F6F8FA",
    "#0d1117": "#FFFFFF",
    "#0d1118": "#EBEFF4",
    "#0d2040": "#E3EDFA",
    "#0f1e3c": "#EAF1FB",
    "#0f2e1a": "#DFF3E7",
    "#111111": "#E6EAF0",
    "#111122": "#F6F8FA",
    "#111128": "#F6F8FA",
    "#161630": "#E6EAF0",
    "#16163a": "#E6EAF0",
    "#161b22": "#F6F8FA",
    "#1a2234": "#EEF3FA",
    "#1d4ed8": "#1D4ED8",
    "#1e1e3a": "#E6EAF0",
    "#1e2a3a": "#EEF3FA",
    "#1e2a4a": "#EEF3FA",
    "#1e3050": "#EEF3FA",
    "#1e40af": "#1E40AF",
    "#21262d": "#D0D7DE",
    "#224422": "#E9F7EF",
    "#22c55e": "#15803D",
    "#252545": "#D0D7DE",
    "#2a2a4a": "#D0D7DE",
    "#2a2a5a": "#D0D7DE",
    "#2a3a5a": "#D0D7DE",
    "#333344": "#D0D7DE",
    "#333366": "#D0D7DE",
    "#3a1212": "#FBE0E0",
    "#3a3a5a": "#D0D7DE",
    "#3a4455": "#D0D7DE",
    "#3a4466": "#D0D7DE",
    "#3b82f6": "#1D4ED8",
    "#442222": "#FDECEC",
    "#445566": "#7A8494",
    "#4488ff": "#1D4ED8",
    "#44eeff": "#0E7490",
    "#4a9eff": "#0B6BCB",
    "#4b5563": "#3B4351",
    "#555577": "#C4CBD4",
    "#556677": "#7A8494",
    "#5566aa": "#7A8494",
    "#55aa66": "#15803D",
    "#60a5fa": "#2563EB",
    "#6366f1": "#4338CA",
    "#666666": "#5B6675",
    "#6677aa": "#5B6675",
    "#6688aa": "#5B6675",
    "#6b7280": "#5B6675",
    "#7788aa": "#5B6675",
    "#8888aa": "#5B6675",
    "#8899aa": "#5B6675",
    "#8899bb": "#5B6675",
    "#93c5fd": "#3B82F6",
    "#94a3b8": "#5B6675",
    "#a78bfa": "#6D28D9",
    "#aa44ff": "#7C2BD9",
    "#aaaaaa": "#5B6675",
    "#aaaacc": "#3B4351",
    "#aabbcc": "#3B4351",
    "#c0c8d8": "#3B4351",
    "#c8d8ee": "#3B4351",
    "#ccccdd": "#3B4351",
    "#ccccee": "#3B4351",
    "#ddddee": "#3B4351",
    "#ef4444": "#B91C1C",
    "#f0dfa8": "#6B5310",
    "#f59e0b": "#B45309",
    "#f87171": "#D14343",
    "#fb923c": "#C2410C",
    "#ff4444": "#B91C1C",
    "#ff6b6b": "#C53030",
    "#ff8844": "#C2410C",
    "#ffd700": "#A16207",
    "#ffffff": "#1F2328",
    "rgba(0,0,0,0.85)": "rgba(255,255,255,0.90)",
    "rgba(0,212,160,0.07)": "rgba(0,135,122,0.08)",
    "rgba(0,230,118,0.07)": "rgba(0,135,90,0.08)",
    "rgba(0,255,136,0.1)": "rgba(0,135,90,0.10)",
    "rgba(0,255,136,0.12)": "rgba(0,135,90,0.12)",
    "rgba(10,10,30,0.75)": "rgba(246,248,250,0.90)",
    "rgba(100,220,100,0.10)": "rgba(21,128,61,0.12)",
    "rgba(140,140,180,0.55)": "rgba(110,120,140,0.55)",
    "rgba(20,20,40,0.8)": "rgba(246,248,250,0.92)",
    "rgba(22,27,34,0.82)": "rgba(246,248,250,0.92)",
    "rgba(239,68,68,0.12)": "rgba(185,28,28,0.12)",
    "rgba(239,68,68,0.35)": "rgba(185,28,28,0.35)",
    "rgba(255,136,68,0.07)": "rgba(194,65,12,0.08)",
    "rgba(255,215,0,0.08)": "#FDF6E3",
    "rgba(255,215,0,0.28)": "#E8D9A8",
    "rgba(255,255,255,0.04)": "rgba(31,35,40,0.04)",
    "rgba(255,255,255,0.06)": "rgba(31,35,40,0.06)",
    "rgba(255,255,255,0.15)": "rgba(31,35,40,0.15)",
    # AOP/PY reference lines: dark ink on white needs more alpha than white
    # ink on black did, so these two shift opacity as well as colour.
    "rgba(255,255,255,0.20)": "rgba(31,35,40,0.34)",
    "rgba(255,255,255,0.27)": "rgba(31,35,40,0.42)",
    "rgba(255,255,255,0.3)": "#F6F8FA",
    "rgba(255,255,255,0.35)": "#F6F8FA",
    "rgba(255,255,255,0.4)": "rgba(31,35,40,0.48)",
    "rgba(255,255,255,0.78)": "rgba(31,35,40,0.82)",
    "rgba(68,136,255,0.04)": "rgba(29,78,216,0.05)",
    "rgba(68,136,255,0.15)": "rgba(29,78,216,0.15)",
    "rgba(74,158,255,0.07)": "rgba(11,107,203,0.07)",
    "rgba(74,158,255,0.08)": "rgba(11,107,203,0.08)",
    "rgba(90,90,130,0.28)": "rgba(120,130,150,0.35)",
    "white": "#1F2328",
}

# Longest-first, so "#00ff8866" is claimed before "#00ff88" can match its head.
# "white" needs the boundary guard or it eats the "white" in "white-space".
_LITERALS = sorted((k for k in COLOUR_MAP if k != "white"), key=len, reverse=True)
_PATTERN = re.compile(
    "|".join(
        [re.escape(k) for k in _LITERALS]
        + [r"(?<![\w-])white(?![-\w])",
           r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)"]
    ),
    re.IGNORECASE,
)
_RGBA = re.compile(
    r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", re.IGNORECASE
)


def _swap(match):
    text = match.group(0)
    mapped = COLOUR_MAP.get(text.lower())
    if mapped is not None:
        return mapped
    # utils/charts.dim() builds its rgba() strings at import time, so those
    # never appear as literals anywhere for the extractor to have paired.
    # Translate the base colour and keep the alpha. Fully transparent stays
    # transparent -- rgba(0,0,0,0) means "no fill", not the colour black.
    m = _RGBA.match(text)
    if m:
        r, g, b, alpha = m.groups()
        if float(alpha) == 0:
            return text
        base = COLOUR_MAP.get("#%02x%02x%02x" % (int(r), int(g), int(b)))
        if base and base.startswith("#") and len(base) == 7:
            return "rgba(%d,%d,%d,%s)" % (
                int(base[1:3], 16), int(base[3:5], 16), int(base[5:7], 16), alpha,
            )
    return text


def active():
    """The theme for this session.

    ``?theme=light`` in the URL wins on first load, which is how the headless
    exporters ask for a style -- the same trick focus_month already uses."""
    if _KEY not in st.session_state:
        wanted = st.query_params.get("theme")
        st.session_state[_KEY] = wanted if wanted in THEMES else DARK
    return st.session_state[_KEY]


def is_light():
    return active() == LIGHT


def tint(value):
    """Recolour a string for the active theme. A no-op on dark."""
    if not isinstance(value, str) or not is_light():
        return value
    return _PATTERN.sub(_swap, value)


def tint_figure(fig):
    """Recolour a Plotly figure for the active theme. A no-op on dark.

    Walks the figure's JSON rather than its object graph: colours live under
    dozens of different keys (marker.line.color, annotations[].font.color,
    shapes[].fillcolor, and HTML inside title and annotation text), and every
    one of them is a string leaf."""
    if not is_light():
        return fig
    try:
        import plotly.graph_objects as go
    except ImportError:
        return fig

    def walk(node):
        if isinstance(node, str):
            return _PATTERN.sub(_swap, node)
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, (list, tuple)):
            return [walk(v) for v in node]
        return node

    if not hasattr(fig, "to_plotly_json"):
        return walk(fig)
    try:
        return go.Figure(walk(fig.to_plotly_json()))
    except Exception:
        return fig                  # never lose a chart over a styling nicety


_installed = False


def install():
    """Route every markdown block and Plotly chart through the tinter.

    Patches DeltaGenerator rather than only the ``st.*`` shortcuts, so that
    ``col.markdown(...)`` and ``st.sidebar.markdown(...)`` are covered too --
    the KPI cards are written that way. The ``st.*`` names are bound methods
    captured at import time, so they are rebound onto the patched functions."""
    global _installed
    if _installed:
        return
    _installed = True

    for name, wrap in (("markdown", _wrap_markdown),
                       ("plotly_chart", _wrap_plotly)):
        original = getattr(DeltaGenerator, name)
        patched = wrap(original)
        setattr(DeltaGenerator, name, patched)
        shortcut = getattr(st, name, None)
        if shortcut is not None and hasattr(shortcut, "__self__"):
            setattr(st, name, patched.__get__(shortcut.__self__))


def _wrap_markdown(original):
    def markdown(self, body="", *args, **kwargs):
        return original(self, tint(body), *args, **kwargs)
    markdown.__name__ = original.__name__
    markdown.__doc__ = original.__doc__
    return markdown


def _wrap_plotly(original):
    def plotly_chart(self, figure_or_data=None, *args, **kwargs):
        return original(self, tint_figure(figure_or_data), *args, **kwargs)
    plotly_chart.__name__ = original.__name__
    plotly_chart.__doc__ = original.__doc__
    return plotly_chart


def theme_selector():
    """Sidebar control. Writes the choice to the URL as well as the session, so
    a link -- and the exporters' headless browser -- can carry it."""
    current = active()
    with st.sidebar:
        st.markdown("---")
        choice = st.radio(
            "Report style",
            THEMES,
            index=THEMES.index(current),
            format_func=lambda name: LABELS[name],
            key="_theme_choice",
            help="Dark is the PowerPoint board pack, light is the Word one. "
                 "Both exports screenshot this dashboard, so whichever is "
                 "selected here is what the report looks like.",
        )
    if choice != current:
        st.session_state[_KEY] = choice
        st.query_params["theme"] = choice
        st.rerun()
    return choice
