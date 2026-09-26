import os
import sqlite3
import hashlib
import random
import string
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w") as _f:
    _f.write(
        '[theme]\n'
        'base = "dark"\n'
        'primaryColor = "#8b6bff"\n'
        'backgroundColor = "#0d0d14"\n'
        'secondaryBackgroundColor = "#1a1a26"\n'
        'textColor = "#f5f7ff"\n'
        'font = "sans serif"\n'
    )

try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

DB_NAME = os.environ.get("DB_PATH", "inventory.db")
CATEGORIES = ["Raw Materials", "Finished Goods", "Office Supplies", "Packaging", "Other"]
UOM_OPTIONS = ["pcs", "kg", "g", "litre", "ml", "box", "meter", "pack"]
STATUS_OPTIONS = ["Draft", "Waiting", "Ready", "Done", "Cancelled"]

st.set_page_config(page_title="StockSense IMS", page_icon="📦", layout="wide",
                   initial_sidebar_state="expanded")

# ==================================================================================
# THEMES
# ==================================================================================
THEMES = {
    "Nebula": {
        "bg": "radial-gradient(ellipse 80% 60% at 10% 0%, #2a1749 0%, #150b28 40%, #08060f 100%)",
        "sidebar": "#0e0a1c",
        "accent": "#8b6bff", "accent2": "#22d3ee",
        "text": "#f5f7ff", "muted": "#b0b8d0",
        "border": "rgba(139,107,255,0.22)", "glass": "rgba(255,255,255,0.045)",
        "light": False,
    },
    "Aurora": {
        "bg": "radial-gradient(ellipse 80% 60% at 20% 0%, #0d4a4a 0%, #072025 45%, #03080a 100%)",
        "sidebar": "#050d10",
        "accent": "#2dd4bf", "accent2": "#4ade80",
        "text": "#eafffb", "muted": "#95c9c2",
        "border": "rgba(45,212,191,0.22)", "glass": "rgba(255,255,255,0.045)",
        "light": False,
    },
    "Ember": {
        "bg": "radial-gradient(ellipse 80% 60% at 15% 0%, #3b120c 0%, #1c0806 50%, #0a0503 100%)",
        "sidebar": "#150806",
        "accent": "#fb7185", "accent2": "#fbbf24",
        "text": "#fff3ee", "muted": "#d8bcae",
        "border": "rgba(251,113,133,0.24)", "glass": "rgba(255,255,255,0.045)",
        "light": False,
    },
    "Midnight": {
        "bg": "radial-gradient(ellipse 70% 50% at 50% -10%, #1e1e42 0%, #0d0d1f 55%, #050510 100%)",
        "sidebar": "#08080f",
        "accent": "#a78bfa", "accent2": "#60a5fa",
        "text": "#f0f0ff", "muted": "#a2a2c4",
        "border": "rgba(167,139,250,0.24)", "glass": "rgba(255,255,255,0.045)",
        "light": False,
    },
    "Solar": {
        "bg": "linear-gradient(135deg, #f6f7fc 0%, #eef1f8 100%)",
        "sidebar": "#ffffff",
        "accent": "#6d4aff", "accent2": "#0ea5e9",
        "text": "#0f172a", "muted": "#3d4455",
        "border": "rgba(109,74,255,0.18)", "glass": "#ffffff",
        "light": True,
    },
}
DENSITY = {"Comfortable": "1.0", "Compact": "0.88", "Spacious": "1.12"}
RADIUS = {"Soft": "12px", "Round": "18px", "Sharp": "6px"}


def _init_prefs():
    if "theme_name" not in st.session_state or st.session_state.theme_name not in THEMES:
        st.session_state.theme_name = "Nebula"
    if st.session_state.get("density") not in DENSITY:
        st.session_state.density = "Comfortable"
    if st.session_state.get("radius") not in RADIUS:
        st.session_state.radius = "Round"
    st.session_state.setdefault("cursor_aura", True)
    st.session_state.setdefault("animations", True)
    st.session_state.setdefault("is_demo", False)


_init_prefs()
T = dict(THEMES[st.session_state.theme_name])
IS_LIGHT = T["light"]

# ==================================================================================
# ICONS
# ==================================================================================
ICON_PATHS = {
    "package": '<path d="M21 8V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8"/><path d="M3 8l9-5 9 5-9 5-9-5z"/><path d="M12 13v9"/>',
    "warning": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    "outbox": '<path d="M12 2v13"/><path d="M6 8l6-6 6 6"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7"/>',
    "transfer": '<path d="M17 3l4 4-4 4"/><path d="M21 7H8a4 4 0 0 0-4 4"/><path d="M7 21l-4-4 4-4"/><path d="M3 17h13a4 4 0 0 0 4-4"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "bolt": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "warehouse": '<path d="M3 21V9l9-6 9 6v12"/><rect x="7" y="13" width="10" height="8"/><line x1="7" y1="17" x2="17" y2="17"/>',
    "sparkle": '<path d="M12 3l1.9 5.8L20 10l-5.8 1.9L12 18l-2.1-6.1L4 10l6.1-1.2z"/>',
}


def icon(name, size=22, color="currentColor", sw=1.8):
    path = ICON_PATHS.get(name, ICON_PATHS["sparkle"])
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" '
            f'stroke-linejoin="round" style="display:block;">{path}</svg>')


LOGO_SVG = """
<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="lg1" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
<stop stop-color="#8b6bff"/><stop offset="1" stop-color="#22d3ee"/></linearGradient>
</defs>
<rect width="36" height="36" rx="10" fill="url(#lg1)"/>
<path d="M10 13l8-4.5L26 13v9l-8 4.5L10 22v-9z" stroke="#0a0a12" stroke-width="1.7" stroke-linejoin="round" fill="none"/>
<path d="M10 13l8 4.5 8-4.5M18 17.5v9" stroke="#0a0a12" stroke-width="1.7" stroke-linejoin="round" fill="none"/>
</svg>
"""

HERO_SVG = """
<svg viewBox="0 0 520 380" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">
<defs>
<linearGradient id="hg1" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#8b6bff"/><stop offset="100%" stop-color="#22d3ee"/></linearGradient>
<linearGradient id="hg2" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#22d3ee"/><stop offset="100%" stop-color="#4ade80"/></linearGradient>
<linearGradient id="hg3" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#fbbf24"/><stop offset="100%" stop-color="#fb7185"/></linearGradient>
<radialGradient id="hglow"><stop offset="0%" stop-color="#8b6bff" stop-opacity="0.5"/><stop offset="100%" stop-color="#8b6bff" stop-opacity="0"/></radialGradient>
</defs>
<circle cx="260" cy="180" r="170" fill="url(#hglow)" opacity="0.55"/>
<ellipse cx="260" cy="310" rx="180" ry="26" fill="#000" opacity="0.35"/>
<g transform="translate(340,120)" opacity="0.9">
<rect x="0" y="0" width="120" height="8" rx="3" fill="#3a2f5c"/>
<rect x="0" y="34" width="120" height="8" rx="3" fill="#3a2f5c"/>
<rect x="0" y="68" width="120" height="8" rx="3" fill="#3a2f5c"/>
<rect x="0" y="0" width="8" height="80" rx="3" fill="#2a2246"/>
<rect x="112" y="0" width="8" height="80" rx="3" fill="#2a2246"/>
<rect x="16" y="12" width="20" height="22" rx="3" fill="url(#hg2)" opacity="0.85"/>
<rect x="44" y="12" width="20" height="22" rx="3" fill="#4c9dff" opacity="0.7"/>
<rect x="72" y="46" width="20" height="22" rx="3" fill="url(#hg3)" opacity="0.85"/>
<rect x="16" y="46" width="20" height="22" rx="3" fill="#a78bfa" opacity="0.75"/>
</g>
<g transform="translate(140,150)">
<polygon points="0,30 90,0 180,30 90,60" fill="#2c2650"/>
<polygon points="0,30 0,90 90,120 90,60" fill="url(#hg1)"/>
<polygon points="180,30 180,90 90,120 90,60" fill="#5b3fd1"/>
<rect x="72" y="60" width="36" height="16" rx="3" fill="#0a0a12" opacity="0.55"/>
<text x="90" y="72" font-family="monospace" font-size="9" fill="#22d3ee" text-anchor="middle">SKU-01</text>
</g>
<g transform="translate(30,220)">
<polygon points="0,20 60,0 120,20 60,40" fill="#0d3d40"/>
<polygon points="0,20 0,66 60,86 60,40" fill="url(#hg2)"/>
<polygon points="120,20 120,66 60,86 60,40" fill="#149aab"/>
</g>
<g transform="translate(320,240)">
<polygon points="0,18 55,0 110,18 55,36" fill="#4a2508"/>
<polygon points="0,18 0,60 55,78 55,36" fill="url(#hg3)"/>
<polygon points="110,18 110,60 55,78 55,36" fill="#c67f1f"/>
</g>
<g transform="translate(60,60)">
<rect x="0" y="0" width="96" height="30" rx="8" fill="#fff" fill-opacity="0.08" stroke="#fff" stroke-opacity="0.12"/>
<circle cx="15" cy="15" r="4" fill="#4ade80"/>
<text x="28" y="19" font-family="Inter,sans-serif" font-size="10" fill="#c3c8e0">IN STOCK</text>
</g>
<g transform="translate(370,40)">
<rect x="0" y="0" width="112" height="30" rx="8" fill="#fff" fill-opacity="0.08" stroke="#fff" stroke-opacity="0.12"/>
<circle cx="15" cy="15" r="4" fill="#fbbf24"/>
<text x="28" y="19" font-family="Inter,sans-serif" font-size="10" fill="#c3c8e0">LOW STOCK</text>
</g>
<circle cx="100" cy="130" r="3" fill="#22d3ee"/>
<circle cx="440" cy="180" r="3" fill="#8b6bff"/>
<circle cx="470" cy="300" r="2.5" fill="#fbbf24"/>
<circle cx="70" cy="330" r="2.5" fill="#4ade80"/>
</svg>
"""

# ==================================================================================
# CSS
# ==================================================================================
CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root, .stApp {
    --accent: __ACCENT__;
    --accent2: __ACCENT2__;
    --text: __TEXT__;
    --muted: __MUTED__;
    --border: __BORDER__;
    --glass: __GLASS__;
    --radius: __RADIUS__;
    --density: __DENSITY__;
    --surface: __SURFACE__;
    --surface-2: __SURFACE2__;
    --input-bg: __INPUT_BG__;
    --sidebar-solid: __SIDEBAR__;

    --background-color: transparent !important;
    --secondary-background-color: transparent !important;
    --text-color: __TEXT__ !important;
    --primary-color: __ACCENT__ !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { background: transparent !important; }
[data-testid="stDecoration"] { display: none !important; }

[data-testid="stToolbar"] button,
[data-testid="stToolbar"] a,
[data-testid="stMainMenu"] button,
#MainMenu button {
    color: var(--text) !important;
    background: transparent !important;
    border-radius: 8px !important;
}
[data-testid="stToolbar"] button:hover,
[data-testid="stToolbar"] a:hover,
[data-testid="stMainMenu"] button:hover {
    background: var(--surface-2) !important;
    color: var(--accent) !important;
}
[data-testid="stMainMenu"],
[data-testid="stMainMenuList"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
}
[data-testid="stMainMenu"] svg { fill: currentColor !important; }

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button {
    color: var(--text) !important;
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover {
    background: var(--accent) !important;
    color: #ffffff !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapsedControl"] svg {
    fill: currentColor !important;
}

html, body, [class*="css"], .stApp {
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--text) !important;
}
h1,h2,h3,h4,.font-display { font-family: 'Space Grotesk', 'Inter', sans-serif; letter-spacing: -0.02em; }
code, pre, .mono { font-family: 'JetBrains Mono', monospace; }

.stApp {
    background: __BG__ !important;
    background-attachment: fixed;
}
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 0;
    background-image:
        linear-gradient(__GRID__ 1px, transparent 1px),
        linear-gradient(90deg, __GRID__ 1px, transparent 1px);
    background-size: 44px 44px;
}
.stApp > section, .main, .block-container, [data-testid="stAppViewContainer"] {
    position: relative;
    z-index: 2;
    background: transparent !important;
}

.orb {
    position: fixed; border-radius: 50%; filter: blur(100px);
    pointer-events: none; z-index: 0;
    animation: orbFloat 24s ease-in-out infinite;
}
.orb-1 { width: 520px; height: 520px; background: var(--accent); top: -180px; left: -180px; opacity: 0.35; }
.orb-2 { width: 440px; height: 440px; background: var(--accent2); bottom: -140px; right: -120px; opacity: 0.30; animation-delay: -8s; }
.orb-3 { width: 380px; height: 380px; background: var(--accent); top: 40%; left: 55%; opacity: 0.14; animation-delay: -16s; }
@keyframes orbFloat {
    0%,100% { transform: translate(0,0) scale(1); }
    33% { transform: translate(40px,-50px) scale(1.08); }
    66% { transform: translate(-30px, 30px) scale(0.94); }
}

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"],
[data-testid="stSidebarHeader"] {
    background: var(--sidebar-solid) !important;
    background-color: var(--sidebar-solid) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}
section[data-testid="stSidebar"] {
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.1rem; }
section[data-testid="stSidebar"] * { color: var(--text); }

.sidebar-brand {
    display: flex; align-items: center; gap: 12px;
    padding: 4px 4px 18px 4px; margin-bottom: 8px;
    border-bottom: 1px solid var(--border);
}
.sidebar-brand-text {
    font-family: 'Space Grotesk', sans-serif; font-weight: 700;
    font-size: 1.15rem; letter-spacing: -0.02em; color: var(--text) !important; line-height: 1;
}
.sidebar-brand-sub { font-size: 0.68rem; color: var(--muted) !important; letter-spacing: 0.14em;
    text-transform: uppercase; margin-top: 4px; }

.user-chip {
    display: flex; align-items: center; gap: 12px;
    background: __CHIP_BG__;
    border: 1px solid var(--border);
    border-radius: var(--radius); padding: 10px 12px; margin-bottom: 12px;
    transition: transform .25s ease, box-shadow .25s ease;
}
.user-chip:hover { transform: translateY(-2px); box-shadow: 0 8px 22px -10px rgba(0,0,0,0.35); }
.user-avatar {
    width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; color: #ffffff !important; font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem; box-shadow: 0 6px 20px rgba(139,107,255,0.35);
}
.user-name { font-weight: 600; color: var(--text) !important; font-size: 0.92rem; line-height: 1.1; }
.user-role { font-size: 0.7rem; color: var(--muted) !important; margin-top: 3px; }

.nav-link {
    border-radius: 12px !important;
    margin: 4px 0 !important;
    padding: 11px 14px !important;
    transition: all .22s cubic-bezier(.2,.8,.2,1) !important;
    color: var(--muted) !important;
    font-weight: 500 !important;
    background: __NAV_BG__ !important;
    border: 1px solid transparent !important;
}
.nav-link:hover {
    background: __NAV_HOVER__ !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
    transform: translateX(3px);
}
.nav-link-selected {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: 1px solid transparent !important;
    box-shadow: 0 6px 16px -10px rgba(139,107,255,0.55) !important;
}
.nav-link-selected:hover { transform: translateX(0); }
.nav-link-selected .icon,
.nav-link-selected svg,
.nav-link-selected i { color: #ffffff !important; opacity: 1 !important; }

.app-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.15rem; font-weight: 700; letter-spacing: -0.035em;
    background: linear-gradient(90deg, var(--text) 0%, var(--accent) 50%, var(--accent2) 100%);
    background-size: 200% auto;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0; display: inline-block;
    animation: shine 6s linear infinite;
}
@keyframes shine { to { background-position: 200% center; } }
.app-subtitle { color: var(--muted) !important; margin-top: -4px; margin-bottom: 16px;
    font-size: 0.82rem; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 500; }

h1, h2, h3, h4 { color: var(--text) !important; }
h2 { font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.35rem !important; font-weight: 600 !important; letter-spacing: -0.02em; margin-bottom: 4px !important; }
h3, h5 { font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.05rem !important; font-weight: 600 !important; letter-spacing: -0.01em;
    color: var(--text) !important;
    margin: 1.2rem 0 0.6rem !important; }

.stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span, [data-testid="stMarkdownContainer"] li {
    color: var(--text) !important;
}
[data-testid="stCaptionContainer"], .stCaption, small {
    color: var(--muted) !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: var(--surface-2) !important;
    box-shadow: __CARD_SHADOW__ !important;
    transition: border-color .3s ease, box-shadow .3s ease, transform .3s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--accent) !important;
    box-shadow: 0 20px 45px -18px rgba(139,107,255,0.45) !important;
    transform: translateY(-2px);
}

.kpi-card {
    border-radius: var(--radius); padding: 18px 20px 16px; height: 100%;
    background: var(--surface-2);
    border: 1px solid var(--border);
    box-shadow: __CARD_SHADOW__;
    position: relative; overflow: hidden;
    transition: transform .35s ease, box-shadow .35s ease, border-color .35s ease;
    animation: riseIn .55s ease both;
}
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background: linear-gradient(90deg, transparent, var(--kpi-color), transparent);
    opacity: 0.9;
}
.kpi-card:hover {
    transform: translateY(-6px);
    border-color: var(--kpi-color);
    box-shadow: 0 26px 50px -20px var(--kpi-color);
}
.kpi-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.kpi-icon-wrap {
    width: 40px; height: 40px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    background: __KPI_ICON_BG__;
    border: 1px solid var(--border);
}
.kpi-pulse {
    width: 8px; height: 8px; border-radius: 50%;
    animation: pulse 2s ease-out infinite;
}
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 var(--kpi-color); }
    70% { box-shadow: 0 0 0 10px transparent; }
    100% { box-shadow: 0 0 0 0 transparent; }
}
.kpi-value {
    font-family: 'Space Grotesk', sans-serif; font-weight: 700;
    font-size: 2.1rem; letter-spacing: -0.03em; color: var(--text) !important;
    line-height: 1; margin: 0 0 6px 0;
}
.kpi-label { color: var(--muted) !important; font-size: 0.74rem; letter-spacing: 0.1em;
    text-transform: uppercase; font-weight: 600; }
@keyframes riseIn { from { opacity:0; transform: translateY(14px); } to { opacity:1; transform: none; } }

button, .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button,
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-primaryFormSubmit"],
button[data-testid="stBaseButton-secondaryFormSubmit"],
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-secondary"],
button[kind="primary"], button[kind="secondary"],
button[kind="primaryFormSubmit"], button[kind="secondaryFormSubmit"] {
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    border: 1px solid var(--border) !important;
    background: __BTN_BG__ !important;
    color: var(--text) !important;
    transition: all .25s ease !important;
    box-shadow: none !important;
}
button:hover, .stButton > button:hover, .stFormSubmitButton > button:hover,
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover,
button[kind="primary"]:hover, button[kind="secondary"]:hover {
    border-color: var(--accent) !important;
    color: #ffffff !important;
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    box-shadow: 0 12px 30px -8px rgba(139,107,255,0.55) !important;
    transform: translateY(-2px);
}
button[kind="primary"], button[kind="primaryFormSubmit"],
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"],
button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 10px 26px -8px rgba(139,107,255,0.55) !important;
}
button[kind="primary"] p, button[kind="primaryFormSubmit"] p,
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primaryFormSubmit"] p { color: #ffffff !important; }

.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div,
div[data-baseweb="input"], div[data-baseweb="base-input"] {
    background: var(--input-bg) !important;
    background-color: var(--input-bg) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 12px !important;
    transition: border-color .2s ease, box-shadow .2s ease;
}
.stTextInput input::placeholder { color: var(--muted) !important; }
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(139,107,255,0.22) !important;
}
label, .stTextInput label, .stSelectbox label, .stNumberInput label,
.stTextArea label, .stMultiSelect label {
    color: var(--muted) !important; font-size: 0.78rem !important;
    font-weight: 600 !important; letter-spacing: 0.06em; text-transform: uppercase;
}
div[data-baseweb="select"] span, div[data-baseweb="select"] div[role="button"] {
    color: var(--text) !important;
}
div[data-baseweb="popover"], div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li,
div[role="listbox"], div[role="option"] {
    background: var(--input-bg) !important;
    background-color: var(--input-bg) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
div[role="option"]:hover, div[data-baseweb="popover"] li:hover {
    background: __NAV_HOVER__ !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 2px !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important; color: var(--muted) !important;
    border-radius: 12px 12px 0 0 !important; padding: 8px 16px !important;
    transition: all .25s ease !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] span {
    color: inherit !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text) !important;
    background: __NAV_HOVER__ !important;
}
.stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span {
    color: var(--accent) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background: var(--accent) !important;
    background-color: var(--accent) !important;
    height: 2px !important;
}
.stTabs [data-baseweb="tab-border"] { background: transparent !important; }

[data-testid="stExpander"], .streamlit-expander, details {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary, .streamlit-expanderHeader, details summary,
details > summary {
    background: var(--surface-2) !important;
    background-color: var(--surface-2) !important;
    color: var(--text) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 12px 16px !important;
}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary div,
[data-testid="stExpander"] summary label,
details > summary p, details > summary span {
    color: var(--text) !important;
}
[data-testid="stExpander"] summary svg,
[data-testid="stExpander"] svg,
details > summary svg {
    fill: var(--text) !important;
    color: var(--text) !important;
}
[data-testid="stExpander"] > div, [data-testid="stExpander"] [role="region"] {
    background: transparent !important;
}

[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] > div > div,
[data-testid="stDataFrameResizable"],
[data-testid="stDataFrameResizable"] > div,
.stDataFrame, .stDataFrame > div,
[data-testid="stTable"], [data-testid="stTable"] table,
[data-testid="stTable"] tbody, [data-testid="stTable"] thead,
[data-testid="stTable"] tr, [data-testid="stTable"] td, [data-testid="stTable"] th {
    background: var(--input-bg) !important;
    background-color: var(--input-bg) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
[data-testid="stDataFrame"] canvas { background: var(--input-bg) !important; }
[data-testid="stTable"] th { color: var(--text) !important; font-weight: 600 !important; }

.stAlert, [data-testid="stAlert"] {
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: var(--surface-2) !important;
}
.stAlert p, .stAlert div, .stAlert span, [data-testid="stAlert"] p {
    color: var(--text) !important;
}

.badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 11px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
}
.badge::before { content:''; width:6px; height:6px; border-radius:50%; background: currentColor; }
.badge-done { background: rgba(74,222,128,0.14); color:#4ade80; border:1px solid rgba(74,222,128,.45); }
.badge-draft { background: rgba(250,204,21,0.16); color:#facc15; border:1px solid rgba(250,204,21,.45); }
.badge-waiting { background: rgba(96,165,250,0.16); color:#60a5fa; border:1px solid rgba(96,165,250,.45); }
.badge-ready { background: rgba(192,132,252,0.16); color:#c084fc; border:1px solid rgba(192,132,252,.45); }
.badge-cancelled { background: rgba(248,113,113,0.16); color:#f87171; border:1px solid rgba(248,113,113,.45); }

.brand-row { display: flex; align-items: center; gap: 14px; margin-bottom: 2px; }
.pill-row { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
.pill {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 9px 14px; border-radius: 999px;
    background: var(--surface-2); border: 1px solid var(--border);
    font-size: 0.82rem; font-weight: 600;
    color: var(--text) !important; transition: all .25s ease;
}
.pill:hover { border-color: var(--accent); transform: translateY(-2px);
    box-shadow: 0 10px 24px -10px var(--accent); }
.pill svg { color: var(--accent); }
.login-hero { padding: 6px 0; }
.login-hero h1 { font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.035em;
    color: var(--text) !important; margin-bottom: 14px; }
.login-hero p { color: var(--muted) !important; font-size: 1rem; line-height: 1.55; }

.toast {
    position: fixed; bottom: 26px; right: 26px; z-index: 9999;
    padding: 14px 22px; border-radius: 14px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #ffffff; font-weight: 700;
    box-shadow: 0 20px 45px -12px rgba(0,0,0,0.55);
    animation: toastIn .4s ease;
}
@keyframes toastIn { from { opacity:0; transform: translateY(24px) scale(0.95); } to { opacity:1; transform: none; } }

#cursor-aura {
    position: fixed; top: 0; left: 0;
    width: 420px; height: 420px; border-radius: 50%;
    pointer-events: none; z-index: 1;
    background: radial-gradient(circle, rgba(139,107,255,0.22), transparent 62%);
    filter: blur(20px);
    transition: transform .05s linear;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--accent), var(--accent2));
    border-radius: 10px; border: 2px solid transparent; background-clip: padding-box;
}
hr { border: none; border-top: 1px solid var(--border); margin: 1.2rem 0; }

.block-container { animation: pageIn .5s ease; }
@keyframes pageIn { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: none; } }
</style>
"""

_surface_2 = "#ffffff" if IS_LIGHT else "rgba(255,255,255,0.045)"
_input_bg = "#ffffff" if IS_LIGHT else "#1a1a26"
_btn_bg = "#ffffff" if IS_LIGHT else "rgba(255,255,255,0.06)"
_chip_bg = "rgba(109,74,255,0.06)" if IS_LIGHT else "rgba(255,255,255,0.05)"
_nav_bg = "rgba(109,74,255,0.03)" if IS_LIGHT else "rgba(255,255,255,0.025)"
_nav_hover = "rgba(109,74,255,0.09)" if IS_LIGHT else "rgba(255,255,255,0.07)"
_kpi_icon_bg = "rgba(109,74,255,0.06)" if IS_LIGHT else "rgba(255,255,255,0.06)"
_grid_line = "rgba(109,74,255,0.05)" if IS_LIGHT else "rgba(255,255,255,0.022)"
_card_shadow = ("0 4px 14px -8px rgba(15,23,42,0.10)" if IS_LIGHT
                else "0 4px 14px -4px rgba(0,0,0,0.35)")

CSS = CSS_TEMPLATE
CSS = CSS.replace("__ACCENT__", T["accent"])
CSS = CSS.replace("__ACCENT2__", T["accent2"])
CSS = CSS.replace("__TEXT__", T["text"])
CSS = CSS.replace("__MUTED__", T["muted"])
CSS = CSS.replace("__BORDER__", T["border"])
CSS = CSS.replace("__GLASS__", T["glass"])
CSS = CSS.replace("__BG__", T["bg"])
CSS = CSS.replace("__SIDEBAR__", T["sidebar"])
CSS = CSS.replace("__RADIUS__", RADIUS[st.session_state.radius])
CSS = CSS.replace("__DENSITY__", DENSITY[st.session_state.density])
CSS = CSS.replace("__SURFACE__", "#ffffff" if IS_LIGHT else "#141420")
CSS = CSS.replace("__SURFACE2__", _surface_2)
CSS = CSS.replace("__INPUT_BG__", _input_bg)
CSS = CSS.replace("__BTN_BG__", _btn_bg)
CSS = CSS.replace("__CHIP_BG__", _chip_bg)
CSS = CSS.replace("__NAV_BG__", _nav_bg)
CSS = CSS.replace("__NAV_HOVER__", _nav_hover)
CSS = CSS.replace("__KPI_ICON_BG__", _kpi_icon_bg)
CSS = CSS.replace("__GRID__", _grid_line)
CSS = CSS.replace("__CARD_SHADOW__", _card_shadow)

st.markdown(CSS, unsafe_allow_html=True)
st.markdown('<div class="orb orb-1"></div><div class="orb orb-2"></div><div class="orb orb-3"></div>',
            unsafe_allow_html=True)

if st.session_state.cursor_aura:
    st.markdown('<div id="cursor-aura"></div>', unsafe_allow_html=True)
    components.html("""
    <script>
    const pdoc = window.parent.document;
    let aura = pdoc.getElementById('cursor-aura');
    if (aura) {
        pdoc.addEventListener('mousemove', (e) => {
            aura.style.transform = `translate(${e.clientX - 210}px, ${e.clientY - 210}px)`;
        });
    }
    </script>
    """, height=0)

# ==================================================================================
# HELPERS
# ==================================================================================
CATEGORY_ICONS = {
    "Raw Materials": "🧱", "Finished Goods": "📦", "Office Supplies": "🖇️",
    "Packaging": "🥡", "Other": "🔹",
}


def badge(status):
    cls = {"Done":"badge-done","Draft":"badge-draft","Waiting":"badge-waiting",
           "Ready":"badge-ready","Cancelled":"badge-cancelled"}.get(status, "badge-draft")
    return f'<span class="badge {cls}">{status}</span>'


def render_html(text):
    cleaned = "\n".join(line.lstrip() for line in text.strip("\n").split("\n"))
    st.markdown(cleaned, unsafe_allow_html=True)


def toast(msg):
    render_html(f'<div class="toast">✓ {msg}</div>')


def kpi_card(icon_name, label, value, color):
    svg = icon(icon_name, 20, color, 2.0)
    render_html(f"""
    <div class="kpi-card" style="--kpi-color:{color};">
      <div class="kpi-head">
        <div class="kpi-icon-wrap">{svg}</div>
        <div class="kpi-pulse" style="background:{color}; --kpi-color:{color};"></div>
      </div>
      <div class="kpi-value">{value:,}</div>
      <div class="kpi-label">{label}</div>
    </div>
    """)


# ==================================================================================
# DB
# ==================================================================================
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def run(query, params=(), fetch=False, many=False):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if many:
            cur.executemany(query, params)
        else:
            cur.execute(query, params)
        data = cur.fetchall() if fetch else None
        cols = [d[0] for d in cur.description] if (fetch and cur.description) else None
        conn.commit()
        if fetch:
            return pd.DataFrame(data, columns=cols) if cols else pd.DataFrame()
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def init_db():
    run("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, full_name TEXT, email TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, otp TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    run("""CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        name TEXT NOT NULL, location TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        name TEXT NOT NULL, sku TEXT NOT NULL,
        category TEXT, uom TEXT,
        reorder_point INTEGER DEFAULT 5, reorder_qty INTEGER DEFAULT 20)""")
    run("""CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        product_id INTEGER NOT NULL, warehouse_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 0)""")
    run("""CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        supplier TEXT, warehouse_id INTEGER,
        status TEXT DEFAULT 'Draft', created_at TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS receipt_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        receipt_id INTEGER, product_id INTEGER, quantity INTEGER)""")
    run("""CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        customer TEXT, warehouse_id INTEGER,
        status TEXT DEFAULT 'Draft', created_at TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS delivery_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        delivery_id INTEGER, product_id INTEGER, quantity INTEGER)""")
    run("""CREATE TABLE IF NOT EXISTS transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        product_id INTEGER,
        from_warehouse_id INTEGER, to_warehouse_id INTEGER, quantity INTEGER,
        status TEXT DEFAULT 'Draft', created_at TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        product_id INTEGER, warehouse_id INTEGER,
        counted_qty INTEGER, diff INTEGER, status TEXT DEFAULT 'Done', created_at TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS move_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
        timestamp TEXT, product_id INTEGER,
        warehouse_id INTEGER, change_qty INTEGER,
        move_type TEXT, reference TEXT)""")

    conn = get_conn()
    cur = conn.cursor()
    tables = ["warehouses", "products", "stock", "receipts", "receipt_items",
              "deliveries", "delivery_items", "transfers", "adjustments", "move_history"]
    for tbl in tables:
        cur.execute(f"PRAGMA table_info({tbl})")
        cols = [r[1] for r in cur.fetchall()]
        if "owner_id" not in cols:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN owner_id INTEGER")
    cur.execute("PRAGMA table_info(adjustments)")
    if "status" not in [r[1] for r in cur.fetchall()]:
        cur.execute("ALTER TABLE adjustments ADD COLUMN status TEXT DEFAULT 'Done'")
    conn.commit()

    try:
        cur.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if row:
            uid = row[0]
            for tbl in tables:
                try:
                    cur.execute(f"UPDATE {tbl} SET owner_id=? WHERE owner_id IS NULL", (uid,))
                    conn.commit()
                except sqlite3.OperationalError:
                    conn.rollback()
    except sqlite3.OperationalError:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ==================================================================================
# AUTH
# ==================================================================================
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def create_user(u, p, fn, e):
    try:
        run("INSERT INTO users (username, password_hash, full_name, email) VALUES (?,?,?,?)",
            (u, hash_pw(p), fn, e))
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "That username is already taken."


def check_login(u, p):
    df = run("SELECT * FROM users WHERE username=?", (u,), fetch=True)
    return (not df.empty) and df.iloc[0]["password_hash"] == hash_pw(p)


def current_user_id():
    if not st.session_state.get("logged_in"):
        return None
    u = st.session_state.get("username")
    if not u:
        return None
    df = run("SELECT id FROM users WHERE username=?", (u,), fetch=True)
    return int(df.iloc[0]["id"]) if not df.empty else None


def generate_otp(u):
    otp = "".join(random.choices(string.digits, k=6))
    run("INSERT INTO password_resets (username, otp, created_at) VALUES (?,?,?)",
        (u, otp, datetime.now().isoformat()))
    return otp


def verify_otp(u, otp):
    df = run("SELECT * FROM password_resets WHERE username=? ORDER BY id DESC LIMIT 1",
             (u,), fetch=True)
    if df.empty:
        return False
    row = df.iloc[0]
    if datetime.now() - datetime.fromisoformat(row["created_at"]) > timedelta(minutes=10):
        return False
    return row["otp"] == otp


def reset_password(u, p):
    run("UPDATE users SET password_hash=? WHERE username=?", (hash_pw(p), u))


# ==================================================================================
# STOCK HELPERS
# ==================================================================================
def get_stock_qty(pid, wid):
    uid = current_user_id()
    if uid is None:
        return 0
    df = run("SELECT quantity FROM stock WHERE owner_id=? AND product_id=? AND warehouse_id=?",
             (uid, pid, wid), fetch=True)
    return int(df.iloc[0]["quantity"]) if not df.empty else 0


def adjust_stock(pid, wid, delta):
    uid = current_user_id()
    cur = get_stock_qty(pid, wid)
    new = cur + delta
    existing = run("SELECT id FROM stock WHERE owner_id=? AND product_id=? AND warehouse_id=?",
                   (uid, pid, wid), fetch=True)
    if existing.empty:
        run("INSERT INTO stock (owner_id, product_id, warehouse_id, quantity) VALUES (?,?,?,?)",
            (uid, pid, wid, new))
    else:
        run("UPDATE stock SET quantity=? WHERE owner_id=? AND product_id=? AND warehouse_id=?",
            (new, uid, pid, wid))


def set_stock_qty(pid, wid, qty):
    uid = current_user_id()
    existing = run("SELECT id FROM stock WHERE owner_id=? AND product_id=? AND warehouse_id=?",
                   (uid, pid, wid), fetch=True)
    if existing.empty:
        run("INSERT INTO stock (owner_id, product_id, warehouse_id, quantity) VALUES (?,?,?,?)",
            (uid, pid, wid, qty))
    else:
        run("UPDATE stock SET quantity=? WHERE owner_id=? AND product_id=? AND warehouse_id=?",
            (qty, uid, pid, wid))


def log_move(pid, wid, delta, mtype, ref):
    uid = current_user_id()
    run("""INSERT INTO move_history
           (owner_id, timestamp, product_id, warehouse_id, change_qty, move_type, reference)
           VALUES (?,?,?,?,?,?,?)""",
        (uid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid, wid, delta, mtype, ref))


def get_products_df():
    uid = current_user_id()
    if uid is None:
        return pd.DataFrame()
    return run("SELECT * FROM products WHERE owner_id=? ORDER BY name", (uid,), fetch=True)


def get_warehouses_df():
    uid = current_user_id()
    if uid is None:
        return pd.DataFrame()
    return run("SELECT * FROM warehouses WHERE owner_id=? ORDER BY name", (uid,), fetch=True)


def get_stock_df():
    uid = current_user_id()
    if uid is None:
        return pd.DataFrame()
    return run("""
    SELECT p.id as product_id, p.name, p.sku, p.category, p.uom, p.reorder_point,
           w.id as warehouse_id, w.name as warehouse, COALESCE(s.quantity,0) as quantity
    FROM products p
    CROSS JOIN warehouses w
    LEFT JOIN stock s ON s.product_id=p.id AND s.warehouse_id=w.id AND s.owner_id=?
    WHERE p.owner_id=? AND w.owner_id=?
    ORDER BY p.name, w.name""", (uid, uid, uid), fetch=True)


def product_label_map(df):
    return {f"{r['name']} ({r['sku']})": r["id"] for _, r in df.iterrows()}


def warehouse_label_map(df):
    return {r["name"]: r["id"] for _, r in df.iterrows()}


# ==================================================================================
# DEMO
# ==================================================================================
def seed_demo_data(user_id):
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")

    run("INSERT INTO warehouses (owner_id, name, location) VALUES (?,?,?)",
        (user_id, "Main Warehouse", "Bengaluru HQ"))
    run("INSERT INTO warehouses (owner_id, name, location) VALUES (?,?,?)",
        (user_id, "Overflow Storage", "Whitefield"))
    wh_main = int(run("SELECT id FROM warehouses WHERE owner_id=? AND name='Main Warehouse'",
                      (user_id,), fetch=True).iloc[0]["id"])
    wh_over = int(run("SELECT id FROM warehouses WHERE owner_id=? AND name='Overflow Storage'",
                      (user_id,), fetch=True).iloc[0]["id"])

    demo_products = [
        ("Steel Rods 12mm", "STL-ROD-12", "Raw Materials", "kg", 100, 500, 850),
        ("Aluminium Sheets", "ALU-SHT", "Raw Materials", "kg", 50, 200, 320),
        ("Wooden Pallet", "WOD-PLT", "Packaging", "pcs", 20, 100, 145),
        ("Shipping Carton", "SHIP-CTN", "Packaging", "pcs", 200, 1000, 2400),
        ("Office Chair", "OFF-CHR", "Office Supplies", "pcs", 5, 20, 12),
        ("Steel Frame Kit", "STL-FRM-KIT", "Finished Goods", "box", 15, 60, 38),
        ("Insulated Panel", "INS-PNL", "Finished Goods", "pcs", 30, 120, 22),
        ("A4 Paper Ream", "OFF-PPR-A4", "Office Supplies", "pack", 40, 200, 95),
    ]
    for name, sku, cat, uom, rp, rq, init_qty in demo_products:
        run("""INSERT INTO products (owner_id, name, sku, category, uom, reorder_point, reorder_qty)
               VALUES (?,?,?,?,?,?,?)""", (user_id, name, sku, cat, uom, rp, rq))
        pid = int(run("SELECT id FROM products WHERE owner_id=? AND sku=?",
                      (user_id, sku), fetch=True).iloc[0]["id"])
        half = init_qty // 2
        run("INSERT INTO stock (owner_id, product_id, warehouse_id, quantity) VALUES (?,?,?,?)",
            (user_id, pid, wh_main, half))
        run("INSERT INTO stock (owner_id, product_id, warehouse_id, quantity) VALUES (?,?,?,?)",
            (user_id, pid, wh_over, init_qty - half))
        run("""INSERT INTO move_history
               (owner_id, timestamp, product_id, warehouse_id, change_qty, move_type, reference)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, ts, pid, wh_main, half, "Initial Stock", "Demo seed"))

    r_ts = (now - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")
    run("""INSERT INTO receipts (owner_id, supplier, warehouse_id, status, created_at)
           VALUES (?,?,?,?,?)""", (user_id, "Tata Steel Ltd.", wh_main, "Done", r_ts))
    rid = int(run("SELECT id FROM receipts WHERE owner_id=? ORDER BY id DESC LIMIT 1",
                  (user_id,), fetch=True).iloc[0]["id"])
    pid_rods = int(run("SELECT id FROM products WHERE owner_id=? AND sku='STL-ROD-12'",
                       (user_id,), fetch=True).iloc[0]["id"])
    run("INSERT INTO receipt_items (owner_id, receipt_id, product_id, quantity) VALUES (?,?,?,?)",
        (user_id, rid, pid_rods, 200))

    d_ts = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    run("""INSERT INTO deliveries (owner_id, customer, warehouse_id, status, created_at)
           VALUES (?,?,?,?,?)""", (user_id, "Sharma Constructions", wh_main, "Draft", d_ts))
    did = int(run("SELECT id FROM deliveries WHERE owner_id=? ORDER BY id DESC LIMIT 1",
                  (user_id,), fetch=True).iloc[0]["id"])
    pid_pallets = int(run("SELECT id FROM products WHERE owner_id=? AND sku='WOD-PLT'",
                          (user_id,), fetch=True).iloc[0]["id"])
    run("INSERT INTO delivery_items (owner_id, delivery_id, product_id, quantity) VALUES (?,?,?,?)",
        (user_id, did, pid_pallets, 15))

    pid_alu = int(run("SELECT id FROM products WHERE owner_id=? AND sku='ALU-SHT'",
                      (user_id,), fetch=True).iloc[0]["id"])
    t_ts = (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    run("""INSERT INTO transfers
           (owner_id, product_id, from_warehouse_id, to_warehouse_id, quantity, status, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (user_id, pid_alu, wh_main, wh_over, 40, "Draft", t_ts))

    pid_chairs = int(run("SELECT id FROM products WHERE owner_id=? AND sku='OFF-CHR'",
                         (user_id,), fetch=True).iloc[0]["id"])
    a_ts = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    run("""INSERT INTO adjustments
           (owner_id, product_id, warehouse_id, counted_qty, diff, status, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (user_id, pid_chairs, wh_main, 10, -2, "Done", a_ts))


def login_as_demo():
    try:
        uname = "demo"
        pwd = "demo1234"
        df = run("SELECT id FROM users WHERE username=?", (uname,), fetch=True)
        if df.empty:
            ok, msg = create_user(uname, pwd, "Demo Account", "demo@stocksense.app")
            if not ok:
                st.error(f"Could not create demo user: {msg}")
                return
            df = run("SELECT id FROM users WHERE username=?", (uname,), fetch=True)
        if df.empty:
            st.error("Demo user could not be found. Try again.")
            return
        uid = int(df.iloc[0]["id"])

        for tbl in ["move_history", "adjustments", "transfers",
                    "delivery_items", "deliveries", "receipt_items", "receipts",
                    "stock", "products", "warehouses"]:
            run(f"DELETE FROM {tbl} WHERE owner_id=?", (uid,))

        seed_demo_data(uid)

        st.session_state.logged_in = True
        st.session_state.username = uname
        st.session_state.is_demo = True
        st.rerun()
    except sqlite3.OperationalError as e:
        st.error(f"Database error: {e}. Close other tabs and refresh.")
    except Exception as e:
        st.error(f"Demo login failed: {type(e).__name__}: {e}")


def seed_user_defaults(user_id):
    run("INSERT INTO warehouses (owner_id, name, location) VALUES (?,?,?)",
        (user_id, "Main Warehouse", "HQ"))


# ==================================================================================
# CHARTS
# ==================================================================================
def chart_donut(df, val_col, name_col, center_label, center_value, height=340):
    colors = [T["accent"], T["accent2"], "#fbbf24", "#fb7185", "#4ade80", "#a78bfa", "#60a5fa"]
    fig = go.Figure(go.Pie(
        labels=df[name_col], values=df[val_col], hole=0.74,
        marker=dict(colors=colors[:len(df)], line=dict(color="rgba(0,0,0,0)", width=2)),
        textinfo="none", sort=False, direction="clockwise",
        hovertemplate="<b>%{label}</b><br>%{value:,} units • %{percent}<extra></extra>",
    ))
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
                    font=dict(color=T["muted"], size=12, family="Inter"), bgcolor="rgba(0,0,0,0)"),
        annotations=[
            dict(text=f"<b>{center_value:,}</b>", x=0.5, y=0.53, showarrow=False,
                 font=dict(color=T["text"], family="Space Grotesk", size=30)),
            dict(text=center_label.upper(), x=0.5, y=0.42, showarrow=False,
                 font=dict(color=T["muted"], size=10, family="Inter")),
        ],
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=6, b=6), height=height,
    )
    return fig


def chart_hbar(df, label_col, value_col, height=340):
    df = df.sort_values(value_col, ascending=True).tail(8)
    fig = go.Figure(go.Bar(
        x=df[value_col], y=df[label_col], orientation="h",
        marker=dict(color=df[value_col],
                    colorscale=[[0, T["accent"]], [1, T["accent2"]]], line=dict(width=0)),
        text=[f"{v:,}" for v in df[value_col]], textposition="outside",
        textfont=dict(color=T["text"], family="Space Grotesk", size=12),
        hovertemplate="<b>%{y}</b><br>%{x:,} units<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=40, t=10, b=10), height=height,
        xaxis=dict(showgrid=True, gridcolor=T["border"], color=T["muted"],
                   zeroline=False, tickfont=dict(family="Inter", size=11)),
        yaxis=dict(showgrid=False, color=T["text"],
                   tickfont=dict(family="Inter", size=12)),
        showlegend=False, bargap=0.42,
    )
    return fig


# ==================================================================================
# LOGIN
# ==================================================================================
def auth_screen():
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        render_html(f"""
        <div class="login-hero">
          <div class="brand-row">
            {LOGO_SVG}
            <div>
              <div class="app-title" style="font-size:1.6rem;">StockSense</div>
              <div class="app-subtitle" style="margin-top:2px;">Inventory Management</div>
            </div>
          </div>
          <h1 style="font-size:3.1rem; line-height:1.04;">Every box,<br/>every move,<br/>
          <span style="background:linear-gradient(90deg,{T['accent']},{T['accent2']});
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">perfectly tracked.</span></h1>
          <p style="max-width:400px;">Replace registers and spreadsheets with one clean
          dashboard — receipts, deliveries, transfers, and live counts, in a single pane.</p>

          <div style="width:40px; height:2px; background:linear-gradient(90deg,{T['accent']},{T['accent2']});
                      border-radius:2px; margin-top:26px;"></div>

          <div style="display:flex; gap:28px; margin-top:20px; align-items:center; flex-wrap:wrap;">
            <div>
              <div style="font-family:'Space Grotesk',sans-serif; font-size:1.7rem;
                          font-weight:700; color:var(--text); line-height:1;">5+</div>
              <div style="font-size:0.7rem; color:var(--muted); letter-spacing:0.12em;
                          text-transform:uppercase; margin-top:4px;">Warehouses</div>
            </div>
            <div style="width:1px; height:34px; background:var(--border);"></div>
            <div>
              <div style="font-family:'Space Grotesk',sans-serif; font-size:1.7rem;
                          font-weight:700; color:var(--text); line-height:1;">&infin;</div>
              <div style="font-size:0.7rem; color:var(--muted); letter-spacing:0.12em;
                          text-transform:uppercase; margin-top:4px;">Products</div>
            </div>
            <div style="width:1px; height:34px; background:var(--border);"></div>
            <div>
              <div style="font-family:'Space Grotesk',sans-serif; font-size:1.7rem;
                          font-weight:700; color:var(--text); line-height:1;">4</div>
              <div style="font-size:0.7rem; color:var(--muted); letter-spacing:0.12em;
                          text-transform:uppercase; margin-top:4px;">Doc types</div>
            </div>
          </div>

          <div class="pill-row" style="margin-top:22px;">
            <div class="pill">{icon('warehouse',16,T['accent'])} Multi-warehouse</div>
            <div class="pill">{icon('chart',16,T['accent'])} Live analytics</div>
            <div class="pill">{icon('shield',16,T['accent'])} Secure login</div>
            <div class="pill">{icon('bolt',16,T['accent'])} Real-time ledger</div>
          </div>

          <div style="margin-top:22px;">{HERO_SVG}</div>
        </div>
        """)

    with right:
        render_html('<div style="height:32px;"></div>')
        render_html("""
        <div style="padding:22px 24px 8px 24px;">
          <div style="font-family:'Space Grotesk';font-size:1.35rem;font-weight:600;
                      letter-spacing:-0.02em;">Welcome back</div>
          <div style="color:var(--muted);font-size:0.86rem;margin-top:4px;">
            Sign in to continue to your dashboard</div>
        </div>
        """)
        tab_login, tab_signup, tab_forgot = st.tabs(["🔐 Log In", "✨ Sign Up", "🔑 Reset"])

        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Username", key="login_user")
                p = st.text_input("Password", type="password", key="login_pass")
                if st.form_submit_button("Sign In →", use_container_width=True, type="primary"):
                    if check_login(u, p):
                        st.session_state.logged_in = True
                        st.session_state.username = u
                        st.session_state.is_demo = False
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            render_html("""
            <div style="display:flex;align-items:center;gap:10px;margin:16px 0 12px 0;">
              <div style="flex:1;height:1px;background:var(--border);"></div>
              <div style="color:var(--muted);font-size:0.72rem;letter-spacing:0.14em;
                          text-transform:uppercase;">or</div>
              <div style="flex:1;height:1px;background:var(--border);"></div>
            </div>
            """)
            if st.button("⚡ Try Demo Account", use_container_width=True, key="demo_login_btn"):
                login_as_demo()

        with tab_signup:
            with st.form("signup_form"):
                fn = st.text_input("Full Name")
                e = st.text_input("Email")
                nu = st.text_input("Username")
                npw = st.text_input("Password", type="password")
                cpw = st.text_input("Confirm Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True, type="primary"):
                    if not nu.strip() or not npw.strip():
                        st.warning("Username and password are required.")
                    elif npw != cpw:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = create_user(nu.strip(), npw, fn.strip(), e.strip())
                        if ok:
                            new_id = int(run("SELECT id FROM users WHERE username=?",
                                             (nu.strip(),), fetch=True).iloc[0]["id"])
                            seed_user_defaults(new_id)
                        (st.success if ok else st.error)(msg)

        with tab_forgot:
            st.caption("Demo mode: OTP is shown on screen.")
            if "otp_stage" not in st.session_state:
                st.session_state.otp_stage = "request"
            if st.session_state.otp_stage == "request":
                with st.form("otp_req"):
                    fp = st.text_input("Username")
                    if st.form_submit_button("Send OTP", use_container_width=True):
                        if run("SELECT 1 FROM users WHERE username=?", (fp,), fetch=True).empty:
                            st.error("No account with that username.")
                        else:
                            otp = generate_otp(fp)
                            st.session_state.otp_stage = "verify"
                            st.session_state.otp_user = fp
                            st.session_state.otp_display = otp
                            st.rerun()
            else:
                st.info(f"OTP: **{st.session_state.get('otp_display','')}** (valid 10 min)")
                with st.form("otp_verify"):
                    inp = st.text_input("Enter OTP")
                    npw = st.text_input("New Password", type="password")
                    cpw = st.text_input("Confirm Password", type="password")
                    if st.form_submit_button("Reset Password", use_container_width=True, type="primary"):
                        if npw != cpw:
                            st.error("Passwords do not match.")
                        elif not verify_otp(st.session_state.otp_user, inp):
                            st.error("Invalid or expired OTP.")
                        else:
                            reset_password(st.session_state.otp_user, npw)
                            st.success("Password reset. Please log in.")
                            st.session_state.otp_stage = "request"


# ==================================================================================
# STOCK TABLE
# ==================================================================================
def styled_stock_table(view_df, key=None):
    if view_df.empty:
        st.info("No matching stock records.")
        return
    display_df = view_df.copy()
    display_df["Category"] = display_df["category"].apply(
        lambda c: f"{CATEGORY_ICONS.get(c,'🔹')} {c or ''}")
    max_qty = max(int(display_df["quantity"].max()), 1)
    cols = ["name", "sku", "Category", "warehouse", "quantity", "reorder_point"]
    if "uom" in display_df.columns:
        cols.insert(4, "uom")
    if "Status" in display_df.columns:
        cols.append("Status")
    st.dataframe(
        display_df[cols], use_container_width=True, hide_index=True, key=key,
        column_config={
            "name": st.column_config.TextColumn("Product"),
            "sku": st.column_config.TextColumn("SKU"),
            "uom": st.column_config.TextColumn("UOM"),
            "warehouse": st.column_config.TextColumn("Warehouse"),
            "quantity": st.column_config.ProgressColumn(
                "Stock Level", min_value=0, max_value=max_qty, format="%d"),
            "reorder_point": st.column_config.NumberColumn("Reorder At"),
        },
    )


# ==================================================================================
# DASHBOARD
# ==================================================================================
def page_dashboard():
    st.subheader("📊 Inventory Dashboard")
    products = get_products_df()
    warehouses = get_warehouses_df()
    stock_df = get_stock_df()
    uid = current_user_id()

    total_products = len(products)
    low_stock_df = stock_df[stock_df["quantity"] < stock_df["reorder_point"]] if not stock_df.empty else pd.DataFrame()
    low_stock_count = low_stock_df["product_id"].nunique() if not low_stock_df.empty else 0

    pending_receipts = run("SELECT COUNT(*) c FROM receipts WHERE owner_id=? AND status NOT IN ('Done','Cancelled')", (uid,), fetch=True).iloc[0]["c"]
    pending_deliveries = run("SELECT COUNT(*) c FROM deliveries WHERE owner_id=? AND status NOT IN ('Done','Cancelled')", (uid,), fetch=True).iloc[0]["c"]
    scheduled_transfers = run("SELECT COUNT(*) c FROM transfers WHERE owner_id=? AND status NOT IN ('Done','Cancelled')", (uid,), fetch=True).iloc[0]["c"]

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        kpi_card("package", "Total Products", int(total_products), T["accent"])
    with c2:
        kpi_card("warning", "Low / Out of Stock", int(low_stock_count), "#fb7185")
    with c3:
        kpi_card("inbox", "Pending Receipts", int(pending_receipts), "#60a5fa")
    with c4:
        kpi_card("outbox", "Pending Deliveries", int(pending_deliveries), T["accent2"])
    with c5:
        kpi_card("transfer", "Transfers Scheduled", int(scheduled_transfers), "#fbbf24")

    st.write("")
    chart_l, chart_r = st.columns([1, 1], gap="medium")
    with chart_l:
        with st.container(border=True):
            st.markdown("##### Stock Distribution by Category")
            if not stock_df.empty and stock_df["quantity"].sum() > 0:
                cat = stock_df.groupby("category")["quantity"].sum().reset_index()
                st.plotly_chart(
                    chart_donut(cat, "quantity", "category", "total units",
                                int(cat["quantity"].sum())),
                    use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No stock data yet.")
    with chart_r:
        with st.container(border=True):
            st.markdown("##### Top Products by Stock")
            if not stock_df.empty:
                top = stock_df.groupby("name")["quantity"].sum().reset_index()
                st.plotly_chart(chart_hbar(top, "name", "quantity"),
                                use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No stock data yet.")

    st.write("")
    st.markdown("##### 🔍 Filters")
    fc1, fc2, fc3, fc4 = st.columns(4, gap="small")
    doc_type = fc1.selectbox("Document", ["All", "Receipts", "Delivery", "Internal", "Adjustments"])
    status_filter = fc2.selectbox("Status", ["All"] + STATUS_OPTIONS)
    wh_opts = ["All"] + list(warehouses["name"]) if not warehouses.empty else ["All"]
    wh_filter = fc3.selectbox("Warehouse", wh_opts)
    cat_opts = ["All"] + sorted(products["category"].dropna().unique().tolist()) if not products.empty else ["All"]
    cat_filter = fc4.selectbox("Category", cat_opts)

    ops_df = build_operations_view(doc_type, status_filter, wh_filter, cat_filter)
    with st.container(border=True):
        st.markdown("##### 📋 Operations Overview")
        if ops_df.empty:
            st.info("No operations match the selected filters.")
        else:
            display_df = ops_df.copy()
            display_df["status"] = display_df["status"].apply(badge)
            render_html(display_df.to_html(escape=False, index=False))

    if not low_stock_df.empty:
        st.write("")
        st.error(f"⚠️ {low_stock_count} product(s) are low or out of stock.")
        with st.container(border=True):
            styled_stock_table(low_stock_df, key="low_stock_table")


def build_operations_view(doc_type, status_filter, wh_filter, cat_filter):
    uid = current_user_id()
    if uid is None:
        return pd.DataFrame()
    rows = []

    if doc_type in ("All", "Receipts"):
        df = run("""SELECT r.id, 'Receipt' as doc_type, r.supplier as party,
                    w.name as warehouse, r.status, r.created_at
                    FROM receipts r
                    LEFT JOIN warehouses w ON w.id=r.warehouse_id
                    WHERE r.owner_id=?""", (uid,), fetch=True)
        if not df.empty:
            if cat_filter != "All":
                keep = run("""SELECT DISTINCT receipt_id FROM receipt_items i
                              JOIN products p ON p.id=i.product_id
                              WHERE p.category=? AND i.owner_id=?""",
                           (cat_filter, uid), fetch=True)
                df = df[df["id"].isin(keep["receipt_id"])] if not keep.empty else df.iloc[0:0]
            rows.append(df)

    if doc_type in ("All", "Delivery"):
        df = run("""SELECT d.id, 'Delivery' as doc_type, d.customer as party,
                    w.name as warehouse, d.status, d.created_at
                    FROM deliveries d
                    LEFT JOIN warehouses w ON w.id=d.warehouse_id
                    WHERE d.owner_id=?""", (uid,), fetch=True)
        if not df.empty:
            if cat_filter != "All":
                keep = run("""SELECT DISTINCT delivery_id FROM delivery_items i
                              JOIN products p ON p.id=i.product_id
                              WHERE p.category=? AND i.owner_id=?""",
                           (cat_filter, uid), fetch=True)
                df = df[df["id"].isin(keep["delivery_id"])] if not keep.empty else df.iloc[0:0]
            rows.append(df)

    if doc_type in ("All", "Internal"):
        df = run("""SELECT t.id, 'Internal Transfer' as doc_type,
                    (fw.name || ' → ' || tw.name) as party, fw.name as warehouse,
                    t.status, t.created_at, p.category
                    FROM transfers t
                    LEFT JOIN warehouses fw ON fw.id=t.from_warehouse_id
                    LEFT JOIN warehouses tw ON tw.id=t.to_warehouse_id
                    LEFT JOIN products p ON p.id=t.product_id
                    WHERE t.owner_id=?""", (uid,), fetch=True)
        if not df.empty:
            if cat_filter != "All":
                df = df[df["category"] == cat_filter]
            rows.append(df.drop(columns=["category"], errors="ignore"))

    if doc_type in ("All", "Adjustments"):
        df = run("""SELECT a.id, 'Adjustment' as doc_type, 'Stock Count' as party,
                    w.name as warehouse, a.status, a.created_at, p.category
                    FROM adjustments a
                    LEFT JOIN warehouses w ON w.id=a.warehouse_id
                    LEFT JOIN products p ON p.id=a.product_id
                    WHERE a.owner_id=?""", (uid,), fetch=True)
        if not df.empty:
            if cat_filter != "All":
                df = df[df["category"] == cat_filter]
            rows.append(df.drop(columns=["category"], errors="ignore"))

    if not rows:
        return pd.DataFrame()
    combined = pd.concat(rows, ignore_index=True)
    if wh_filter != "All":
        combined = combined[combined["warehouse"] == wh_filter]
    if status_filter != "All":
        combined = combined[combined["status"] == status_filter]
    return combined.sort_values("created_at", ascending=False)


# ==================================================================================
# PRODUCTS
# ==================================================================================
def page_products():
    st.subheader("🧾 Product Management")
    warehouses = get_warehouses_df()
    if warehouses.empty:
        st.warning("Add at least one warehouse in Settings first.")
        return
    uid = current_user_id()

    with st.expander("➕ Add New Product", expanded=False):
        with st.form("add_product_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Product Name*")
            sku = c2.text_input("SKU / Code*")
            c3, c4 = st.columns(2)
            category = c3.selectbox("Category", CATEGORIES)
            uom = c4.selectbox("Unit of Measure", UOM_OPTIONS)
            wh_map = warehouse_label_map(warehouses)
            c5, c6 = st.columns(2)
            init_wh = c5.selectbox("Initial Warehouse", list(wh_map.keys()))
            init_qty = c6.number_input("Initial Stock", min_value=0, step=1, value=0)
            c7, c8 = st.columns(2)
            rp = c7.number_input("Reorder Point", min_value=0, step=1, value=5)
            rq = c8.number_input("Reorder Quantity", min_value=0, step=1, value=20)
            if st.form_submit_button("Save Product", use_container_width=True, type="primary"):
                if name.strip() and sku.strip():
                    dup = run("SELECT 1 FROM products WHERE owner_id=? AND sku=?",
                              (uid, sku.strip()), fetch=True)
                    if not dup.empty:
                        st.error("A product with this SKU already exists.")
                    else:
                        run("""INSERT INTO products
                               (owner_id, name, sku, category, uom, reorder_point, reorder_qty)
                               VALUES (?,?,?,?,?,?,?)""",
                            (uid, name.strip(), sku.strip(), category, uom, rp, rq))
                        nid = int(run("SELECT id FROM products WHERE owner_id=? AND sku=?",
                                      (uid, sku.strip()), fetch=True).iloc[0]["id"])
                        if init_qty > 0:
                            set_stock_qty(nid, wh_map[init_wh], int(init_qty))
                            log_move(nid, wh_map[init_wh], int(init_qty),
                                     "Initial Stock", f"Product #{nid}")
                        st.success(f"Product '{name}' added.")
                else:
                    st.warning("Name and SKU are required.")

    st.write("")
    st.markdown("##### 📦 Current Inventory")
    stock_df = get_stock_df()
    if stock_df.empty:
        st.info("No products registered yet.")
        return

    fc1, fc2, fc3 = st.columns([2, 1, 1])
    q = fc1.text_input("🔍 Search by name or SKU")
    cat_opts = ["All"] + sorted(stock_df["category"].dropna().unique().tolist())
    sel_cat = fc2.selectbox("Category", cat_opts)
    wh_opts = ["All"] + list(warehouses["name"])
    sel_wh = fc3.selectbox("Warehouse", wh_opts)

    view = stock_df.copy()
    if sel_cat != "All":
        view = view[view["category"] == sel_cat]
    if sel_wh != "All":
        view = view[view["warehouse"] == sel_wh]
    if q.strip():
        view = view[view["name"].str.contains(q, case=False, na=False)
                    | view["sku"].str.contains(q, case=False, na=False)]
    view["Status"] = view.apply(
        lambda r: "⚠️ Low Stock" if r["quantity"] < r["reorder_point"] else "✅ In Stock", axis=1)
    with st.container(border=True):
        styled_stock_table(view, key="products_table")

    with st.expander("🛠️ Edit or Delete a Product"):
        products = get_products_df()
        pmap = product_label_map(products)
        if pmap:
            label = st.selectbox("Select product", list(pmap.keys()))
            pid = pmap[label]
            prow = products[products["id"] == pid].iloc[0]
            c1, c2 = st.columns(2)
            with c1:
                en = st.text_input("Name", value=prow["name"], key="en")
                ci = CATEGORIES.index(prow["category"]) if prow["category"] in CATEGORIES else 0
                ec = st.selectbox("Category", CATEGORIES, index=ci, key="ec")
                ui = UOM_OPTIONS.index(prow["uom"]) if prow["uom"] in UOM_OPTIONS else 0
                eu = st.selectbox("UOM", UOM_OPTIONS, index=ui, key="eu")
            with c2:
                erp = st.number_input("Reorder Point", min_value=0, step=1,
                                      value=int(prow["reorder_point"]), key="erp")
                erq = st.number_input("Reorder Quantity", min_value=0, step=1,
                                      value=int(prow["reorder_qty"]), key="erq")
            b1, b2 = st.columns(2)
            if b1.button("💾 Update Product", use_container_width=True):
                run("""UPDATE products SET name=?, category=?, uom=?, reorder_point=?, reorder_qty=?
                       WHERE id=? AND owner_id=?""", (en, ec, eu, erp, erq, int(pid), uid))
                st.success("Product updated.")
                st.rerun()
            if b2.button("🗑️ Delete Product", use_container_width=True):
                run("DELETE FROM products WHERE id=? AND owner_id=?", (int(pid), uid))
                run("DELETE FROM stock WHERE product_id=? AND owner_id=?", (int(pid), uid))
                st.warning("Product deleted.")
                st.rerun()


# ==================================================================================
# RECEIPTS
# ==================================================================================
def page_receipts():
    st.subheader("📥 Receipts")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or warehouses.empty:
        st.info("Add products and warehouses first.")
        return
    uid = current_user_id()

    with st.expander("➕ New Receipt", expanded=False):
        with st.form("new_receipt", clear_on_submit=True):
            supplier = st.text_input("Supplier")
            wh_map = warehouse_label_map(warehouses)
            wh = st.selectbox("Warehouse", list(wh_map.keys()))
            if st.form_submit_button("Create Draft", use_container_width=True, type="primary"):
                run("""INSERT INTO receipts (owner_id, supplier, warehouse_id, status, created_at)
                       VALUES (?,?,?,?,?)""",
                    (uid, supplier, wh_map[wh], "Draft",
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                st.success("Draft receipt created.")

    st.write("")
    receipts = run("""SELECT r.*, w.name as warehouse_name FROM receipts r
                       LEFT JOIN warehouses w ON w.id=r.warehouse_id
                       WHERE r.owner_id=? ORDER BY r.id DESC""", (uid,), fetch=True)
    if receipts.empty:
        st.info("No receipts yet.")
        return
    for _, r in receipts.iterrows():
        with st.container(border=True):
            top = st.columns([3, 2, 2, 2])
            top[0].markdown(f"**Receipt #{r['id']}** — {r['supplier'] or 'No supplier'}")
            top[1].markdown(f"🏢 {r['warehouse_name']}")
            top[2].markdown(badge(r["status"]), unsafe_allow_html=True)
            top[3].caption(r["created_at"])
            items = run("""SELECT ri.id, p.name, p.sku, ri.quantity, ri.product_id
                           FROM receipt_items ri JOIN products p ON p.id=ri.product_id
                           WHERE ri.receipt_id=? AND ri.owner_id=?""", (r["id"], uid), fetch=True)
            if not items.empty:
                st.dataframe(items[["name", "sku", "quantity"]],
                             use_container_width=True, hide_index=True)
            if r["status"] == "Draft":
                pmap = product_label_map(products)
                ac1, ac2, ac3 = st.columns([3, 1, 1])
                pc = ac1.selectbox("Product", list(pmap.keys()), key=f"rp_{r['id']}")
                qc = ac2.number_input("Qty", min_value=1, step=1, value=1, key=f"rq_{r['id']}")
                if ac3.button("Add Line", key=f"radd_{r['id']}", use_container_width=True):
                    run("""INSERT INTO receipt_items (owner_id, receipt_id, product_id, quantity)
                           VALUES (?,?,?,?)""", (uid, int(r["id"]), pmap[pc], int(qc)))
                    st.rerun()
                b1, b2 = st.columns(2)
                if b1.button("✅ Validate", key=f"rval_{r['id']}",
                             use_container_width=True, type="primary"):
                    if items.empty:
                        st.warning("Add at least one product line first.")
                    else:
                        for _, it in items.iterrows():
                            adjust_stock(int(it["product_id"]), int(r["warehouse_id"]),
                                         int(it["quantity"]))
                            log_move(int(it["product_id"]), int(r["warehouse_id"]),
                                     int(it["quantity"]), "Receipt", f"Receipt #{r['id']}")
                        run("UPDATE receipts SET status='Done' WHERE id=? AND owner_id=?",
                            (int(r["id"]), uid))
                        st.success("Receipt validated — stock increased.")
                        st.rerun()
                if b2.button("🚫 Cancel", key=f"rcx_{r['id']}", use_container_width=True):
                    run("UPDATE receipts SET status='Cancelled' WHERE id=? AND owner_id=?",
                        (int(r["id"]), uid))
                    st.rerun()


# ==================================================================================
# DELIVERIES
# ==================================================================================
def page_deliveries():
    st.subheader("📤 Delivery Orders")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or warehouses.empty:
        st.info("Add products and warehouses first.")
        return
    uid = current_user_id()

    with st.expander("➕ New Delivery", expanded=False):
        with st.form("new_delivery", clear_on_submit=True):
            customer = st.text_input("Customer")
            wh_map = warehouse_label_map(warehouses)
            wh = st.selectbox("Warehouse", list(wh_map.keys()))
            if st.form_submit_button("Create Draft", use_container_width=True, type="primary"):
                run("""INSERT INTO deliveries (owner_id, customer, warehouse_id, status, created_at)
                       VALUES (?,?,?,?,?)""",
                    (uid, customer, wh_map[wh], "Draft",
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                st.success("Draft delivery created.")

    st.write("")
    deliveries = run("""SELECT d.*, w.name as warehouse_name FROM deliveries d
                         LEFT JOIN warehouses w ON w.id=d.warehouse_id
                         WHERE d.owner_id=? ORDER BY d.id DESC""", (uid,), fetch=True)
    if deliveries.empty:
        st.info("No delivery orders yet.")
        return
    for _, d in deliveries.iterrows():
        with st.container(border=True):
            top = st.columns([3, 2, 2, 2])
            top[0].markdown(f"**Delivery #{d['id']}** — {d['customer'] or 'No customer'}")
            top[1].markdown(f"🏢 {d['warehouse_name']}")
            top[2].markdown(badge(d["status"]), unsafe_allow_html=True)
            top[3].caption(d["created_at"])
            items = run("""SELECT di.id, p.name, p.sku, di.quantity, di.product_id
                           FROM delivery_items di JOIN products p ON p.id=di.product_id
                           WHERE di.delivery_id=? AND di.owner_id=?""", (d["id"], uid), fetch=True)
            if not items.empty:
                st.dataframe(items[["name", "sku", "quantity"]],
                             use_container_width=True, hide_index=True)
            if d["status"] == "Draft":
                pmap = product_label_map(products)
                ac1, ac2, ac3 = st.columns([3, 1, 1])
                pc = ac1.selectbox("Product", list(pmap.keys()), key=f"dp_{d['id']}")
                qc = ac2.number_input("Qty", min_value=1, step=1, value=1, key=f"dq_{d['id']}")
                if ac3.button("Add Line", key=f"dadd_{d['id']}", use_container_width=True):
                    run("""INSERT INTO delivery_items (owner_id, delivery_id, product_id, quantity)
                           VALUES (?,?,?,?)""", (uid, int(d["id"]), pmap[pc], int(qc)))
                    st.rerun()
                b1, b2 = st.columns(2)
                if b1.button("✅ Validate & Ship", key=f"dval_{d['id']}",
                             use_container_width=True, type="primary"):
                    if items.empty:
                        st.warning("Add at least one line first.")
                    else:
                        shortage = [it for _, it in items.iterrows()
                                    if get_stock_qty(int(it["product_id"]),
                                                     int(d["warehouse_id"])) < it["quantity"]]
                        if shortage:
                            st.error("Not enough stock for one or more items.")
                        else:
                            for _, it in items.iterrows():
                                adjust_stock(int(it["product_id"]), int(d["warehouse_id"]),
                                             -int(it["quantity"]))
                                log_move(int(it["product_id"]), int(d["warehouse_id"]),
                                         -int(it["quantity"]), "Delivery", f"Delivery #{d['id']}")
                            run("UPDATE deliveries SET status='Done' WHERE id=? AND owner_id=?",
                                (int(d["id"]), uid))
                            st.success("Delivery validated.")
                            st.rerun()
                if b2.button("🚫 Cancel", key=f"dcx_{d['id']}", use_container_width=True):
                    run("UPDATE deliveries SET status='Cancelled' WHERE id=? AND owner_id=?",
                        (int(d["id"]), uid))
                    st.rerun()


# ==================================================================================
# TRANSFERS
# ==================================================================================
def page_transfers():
    st.subheader("🔁 Internal Transfers")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or len(warehouses) < 2:
        st.info("Need at least 2 warehouses and 1 product.")
        return
    uid = current_user_id()

    with st.form("transfer_form", clear_on_submit=True):
        pmap = product_label_map(products)
        wh_map = warehouse_label_map(warehouses)
        pc = st.selectbox("Product", list(pmap.keys()))
        c1, c2, c3 = st.columns(3)
        fw = c1.selectbox("From", list(wh_map.keys()))
        tw = c2.selectbox("To", list(wh_map.keys()), index=min(1, len(wh_map) - 1))
        q = c3.number_input("Qty", min_value=1, step=1, value=1)
        b1, b2 = st.columns(2)
        schedule = b1.form_submit_button("🕒 Schedule", use_container_width=True)
        execute = b2.form_submit_button("⚡ Execute Now", use_container_width=True, type="primary")
        if schedule or execute:
            if fw == tw:
                st.warning("Source and destination must differ.")
            else:
                pid = pmap[pc]
                if execute:
                    avail = get_stock_qty(pid, wh_map[fw])
                    if avail < q:
                        st.error(f"Not enough stock (available: {avail}).")
                    else:
                        adjust_stock(pid, wh_map[fw], -int(q))
                        adjust_stock(pid, wh_map[tw], int(q))
                        run("""INSERT INTO transfers
                               (owner_id, product_id, from_warehouse_id, to_warehouse_id,
                                quantity, status, created_at) VALUES (?,?,?,?,?,?,?)""",
                            (uid, pid, wh_map[fw], wh_map[tw], int(q), "Done",
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        log_move(pid, wh_map[fw], -int(q), "Internal Transfer", f"To {tw}")
                        log_move(pid, wh_map[tw], int(q), "Internal Transfer", f"From {fw}")
                        st.success(f"Moved {q} from {fw} to {tw}.")
                        st.rerun()
                else:
                    run("""INSERT INTO transfers
                           (owner_id, product_id, from_warehouse_id, to_warehouse_id,
                            quantity, status, created_at) VALUES (?,?,?,?,?,?,?)""",
                        (uid, pid, wh_map[fw], wh_map[tw], int(q), "Draft",
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    st.success("Scheduled as Draft.")
                    st.rerun()

    st.write("")
    pending = run("""SELECT t.id, p.name, p.sku, fw.name as from_wh, tw.name as to_wh,
                     t.quantity, t.status, t.created_at, t.product_id,
                     t.from_warehouse_id, t.to_warehouse_id
                     FROM transfers t
                     JOIN products p ON p.id=t.product_id
                     JOIN warehouses fw ON fw.id=t.from_warehouse_id
                     JOIN warehouses tw ON tw.id=t.to_warehouse_id
                     WHERE t.owner_id=? AND t.status IN ('Draft','Waiting','Ready')
                     ORDER BY t.id DESC""", (uid,), fetch=True)
    if not pending.empty:
        st.markdown("##### Scheduled Transfers")
        for _, t in pending.iterrows():
            with st.container(border=True):
                cols = st.columns([3, 2, 2, 2, 2])
                cols[0].markdown(f"**#{t['id']}** — {t['name']}")
                cols[1].markdown(f"{t['from_wh']} → {t['to_wh']}")
                cols[2].markdown(f"Qty **{t['quantity']}**")
                cols[3].markdown(badge(t["status"]), unsafe_allow_html=True)
                b = cols[4].columns(2)
                if b[0].button("✅", key=f"ex_{t['id']}", help="Execute"):
                    avail = get_stock_qty(int(t["product_id"]), int(t["from_warehouse_id"]))
                    if avail < t["quantity"]:
                        st.error(f"Not enough stock ({avail}).")
                    else:
                        adjust_stock(int(t["product_id"]), int(t["from_warehouse_id"]),
                                     -int(t["quantity"]))
                        adjust_stock(int(t["product_id"]), int(t["to_warehouse_id"]),
                                     int(t["quantity"]))
                        run("UPDATE transfers SET status='Done' WHERE id=? AND owner_id=?",
                            (int(t["id"]), uid))
                        log_move(int(t["product_id"]), int(t["from_warehouse_id"]),
                                 -int(t["quantity"]), "Internal Transfer", f"Transfer #{t['id']}")
                        log_move(int(t["product_id"]), int(t["to_warehouse_id"]),
                                 int(t["quantity"]), "Internal Transfer", f"Transfer #{t['id']}")
                        st.rerun()
                if b[1].button("🚫", key=f"cx_{t['id']}", help="Cancel"):
                    run("UPDATE transfers SET status='Cancelled' WHERE id=? AND owner_id=?",
                        (int(t["id"]), uid))
                    st.rerun()
        st.write("")

    hist = run("""SELECT t.id, p.name, p.sku, fw.name as from_wh, tw.name as to_wh,
                  t.quantity, t.status, t.created_at FROM transfers t
                  JOIN products p ON p.id=t.product_id
                  JOIN warehouses fw ON fw.id=t.from_warehouse_id
                  JOIN warehouses tw ON tw.id=t.to_warehouse_id
                  WHERE t.owner_id=? AND t.status IN ('Done','Cancelled')
                  ORDER BY t.id DESC""", (uid,), fetch=True)
    st.markdown("##### History")
    if hist.empty:
        st.info("No completed transfers yet.")
    else:
        with st.container(border=True):
            st.dataframe(hist, use_container_width=True, hide_index=True)


# ==================================================================================
# ADJUSTMENTS
# ==================================================================================
def page_adjustments():
    st.subheader("🧮 Stock Adjustments")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or warehouses.empty:
        st.info("Add products and warehouses first.")
        return
    uid = current_user_id()

    with st.form("adj_form", clear_on_submit=True):
        pmap = product_label_map(products)
        wh_map = warehouse_label_map(warehouses)
        pc = st.selectbox("Product", list(pmap.keys()))
        wc = st.selectbox("Warehouse", list(wh_map.keys()))
        pid, wid = pmap[pc], wh_map[wc]
        cur = get_stock_qty(pid, wid)
        st.caption(f"System recorded stock: **{cur}**")
        counted = st.number_input("Physical Counted Quantity", min_value=0, step=1, value=cur)
        if st.form_submit_button("Apply Adjustment", use_container_width=True, type="primary"):
            diff = int(counted) - cur
            set_stock_qty(pid, wid, int(counted))
            run("""INSERT INTO adjustments
                   (owner_id, product_id, warehouse_id, counted_qty, diff, status, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (uid, pid, wid, int(counted), diff, "Done",
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            log_move(pid, wid, diff, "Adjustment", "Physical count")
            st.success(f"Adjusted by {diff:+d}. New: {counted}.")
            st.rerun()

    st.write("")
    st.markdown("##### Adjustment History")
    hist = run("""SELECT a.id, p.name, p.sku, w.name as warehouse, a.counted_qty, a.diff,
                  a.status, a.created_at FROM adjustments a
                  JOIN products p ON p.id=a.product_id
                  JOIN warehouses w ON w.id=a.warehouse_id
                  WHERE a.owner_id=? ORDER BY a.id DESC""", (uid,), fetch=True)
    if hist.empty:
        st.info("No adjustments recorded yet.")
    else:
        with st.container(border=True):
            st.dataframe(hist, use_container_width=True, hide_index=True)


# ==================================================================================
# MOVE HISTORY
# ==================================================================================
def page_move_history():
    st.subheader("📜 Move History")
    products = get_products_df()
    warehouses = get_warehouses_df()
    uid = current_user_id()
    c1, c2, c3 = st.columns(3)
    prod_opts = ["All"] + list(products["name"]) if not products.empty else ["All"]
    pf = c1.selectbox("Product", prod_opts)
    wh_opts = ["All"] + list(warehouses["name"]) if not warehouses.empty else ["All"]
    wf = c2.selectbox("Warehouse", wh_opts)
    tf = c3.selectbox("Type", ["All", "Receipt", "Delivery", "Internal Transfer",
                                "Adjustment", "Initial Stock"])
    ledger = run("""SELECT m.timestamp, p.name as product, w.name as warehouse,
                    m.change_qty, m.move_type, m.reference FROM move_history m
                    JOIN products p ON p.id=m.product_id
                    JOIN warehouses w ON w.id=m.warehouse_id
                    WHERE m.owner_id=? ORDER BY m.id DESC""", (uid,), fetch=True)
    if ledger.empty:
        st.info("No stock movements recorded yet.")
        return
    if pf != "All":
        ledger = ledger[ledger["product"] == pf]
    if wf != "All":
        ledger = ledger[ledger["warehouse"] == wf]
    if tf != "All":
        ledger = ledger[ledger["move_type"] == tf]
    with st.container(border=True):
        st.dataframe(ledger, use_container_width=True, hide_index=True)


# ==================================================================================
# SETTINGS
# ==================================================================================
def page_settings():
    st.subheader("⚙️ Settings")
    uid = current_user_id()
    tab_wh, tab_app = st.tabs(["🏢 Warehouses", "🎨 Appearance"])

    with tab_wh:
        with st.form("add_wh", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Warehouse Name")
            l = c2.text_input("Address / Notes")
            if st.form_submit_button("Add Warehouse", use_container_width=True, type="primary"):
                if not n.strip():
                    st.warning("Name is required.")
                else:
                    dup = run("SELECT 1 FROM warehouses WHERE owner_id=? AND name=?",
                              (uid, n.strip()), fetch=True)
                    if not dup.empty:
                        st.error("Warehouse name already exists.")
                    else:
                        run("""INSERT INTO warehouses (owner_id, name, location)
                               VALUES (?,?,?)""", (uid, n.strip(), l.strip()))
                        st.success(f"'{n}' added.")
                        st.rerun()
        st.write("")
        warehouses = get_warehouses_df()
        if warehouses.empty:
            st.info("No warehouses yet.")
        else:
            with st.container(border=True):
                st.dataframe(warehouses, use_container_width=True, hide_index=True)
            with st.expander("🗑️ Delete a Warehouse"):
                wmap = warehouse_label_map(warehouses)
                wc = st.selectbox("Select warehouse", list(wmap.keys()))
                if st.button("Delete Warehouse", use_container_width=True):
                    wid = wmap[wc]
                    in_use = run("""SELECT COUNT(*) c FROM stock
                                    WHERE owner_id=? AND warehouse_id=? AND quantity>0""",
                                 (uid, wid), fetch=True).iloc[0]["c"]
                    if in_use > 0:
                        st.error("Warehouse still has stock — clear it first.")
                    else:
                        run("DELETE FROM warehouses WHERE id=? AND owner_id=?", (wid, uid))
                        st.warning("Deleted.")
                        st.rerun()

    with tab_app:
        st.markdown("##### Theme")
        names = list(THEMES.keys())
        idx = names.index(st.session_state.theme_name) if st.session_state.theme_name in names else 0
        nt = st.selectbox("Color theme", names, index=idx)
        if nt != st.session_state.theme_name:
            st.session_state.theme_name = nt
            st.rerun()

        st.markdown("##### Density & Shape")
        di = list(DENSITY.keys()).index(st.session_state.density)
        nd = st.selectbox("Content density", list(DENSITY.keys()), index=di)
        if nd != st.session_state.density:
            st.session_state.density = nd
            st.rerun()
        ri = list(RADIUS.keys()).index(st.session_state.radius)
        nr = st.selectbox("Corner style", list(RADIUS.keys()), index=ri)
        if nr != st.session_state.radius:
            st.session_state.radius = nr
            st.rerun()

        st.markdown("##### Effects")
        aura = st.toggle("Cursor aura glow", value=st.session_state.cursor_aura)
        if aura != st.session_state.cursor_aura:
            st.session_state.cursor_aura = aura
            st.rerun()
        an = st.toggle("Animated background", value=st.session_state.animations)
        if an != st.session_state.animations:
            st.session_state.animations = an
            st.rerun()


# ==================================================================================
# PROFILE
# ==================================================================================
def page_profile():
    st.subheader("👤 My Profile")
    uid = current_user_id()
    user = run("SELECT * FROM users WHERE id=?", (uid,), fetch=True).iloc[0]
    with st.form("profile_form"):
        fn = st.text_input("Full Name", value=user["full_name"] or "")
        em = st.text_input("Email", value=user["email"] or "")
        if st.form_submit_button("Save Changes", use_container_width=True, type="primary"):
            run("UPDATE users SET full_name=?, email=? WHERE id=?", (fn, em, uid))
            st.success("Profile updated.")
    st.write("")
    st.markdown("##### 🔑 Change Password")
    with st.form("change_pw", clear_on_submit=True):
        op = st.text_input("Current Password", type="password")
        np = st.text_input("New Password", type="password")
        cp = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button("Update Password", use_container_width=True):
            if not check_login(st.session_state.username, op):
                st.error("Current password is incorrect.")
            elif np != cp:
                st.error("New passwords do not match.")
            elif not np.strip():
                st.warning("New password cannot be empty.")
            else:
                reset_password(st.session_state.username, np)
                st.success("Password updated.")


# ==================================================================================
# MAIN
# ==================================================================================
def main():
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        auth_screen()
        return

    uid = current_user_id()
    user_row = run("SELECT * FROM users WHERE id=?", (uid,), fetch=True)
    dn = st.session_state.username
    if not user_row.empty and user_row.iloc[0]["full_name"]:
        dn = user_row.iloc[0]["full_name"]
    initial = dn.strip()[0].upper() if dn.strip() else "U"

    with st.sidebar:
        render_html(f"""
        <div class="sidebar-brand">{LOGO_SVG}
          <div>
            <div class="sidebar-brand-text">StockSense</div>
            <div class="sidebar-brand-sub">Inventory</div>
          </div>
        </div>
        <div class="user-chip">
          <div class="user-avatar">{initial}</div>
          <div>
            <div class="user-name">{dn}</div>
            <div class="user-role">● Online</div>
          </div>
        </div>
        """)

        if st.session_state.get("is_demo"):
            render_html("""
            <div style="margin-top:8px; padding:8px 12px; border-radius:12px;
                        background: linear-gradient(135deg, rgba(251,191,36,0.14), rgba(251,113,133,0.10));
                        border:1px solid rgba(251,191,36,0.35);
                        font-size:0.74rem; color:#fbbf24; font-weight:600;
                        display:flex; align-items:center; gap:8px;">
                <span style="width:6px;height:6px;border-radius:50%;background:#fbbf24;"></span>
                Demo Mode — sample data, resets on exit
            </div>
            """)

        page_names = ["Dashboard", "Products", "Receipts", "Delivery Orders",
                      "Internal Transfers", "Stock Adjustments", "Move History",
                      "Settings", "My Profile"]
        if HAS_OPTION_MENU:
            menu = option_menu(
                menu_title=None,
                options=page_names,
                icons=["speedometer2", "box-seam", "box-arrow-in-down", "box-arrow-up-right",
                       "arrow-left-right", "sliders", "clock-history", "gear", "person-circle"],
                default_index=0,
                styles={
                    "container": {"padding": "0", "background-color": "transparent"},
                    "icon": {"color": T["muted"], "font-size": "16px"},
                    "nav-link": {"font-size": "13.5px", "font-weight": "600",
                                 "color": T["muted"], "border-radius": "12px",
                                 "margin": "4px 0", "padding": "11px 14px"},
                    "nav-link-selected": {
                        "background": f"linear-gradient(135deg, {T['accent']}, {T['accent2']})",
                        "color": "#ffffff"},
                },
            )
        else:
            menu = st.radio("Navigation", page_names, label_visibility="collapsed")

        st.write("")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_demo = False
            st.rerun()

    render_html(f"""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:2px;">
        {LOGO_SVG}
        <span class="app-title">StockSense</span>
    </div>
    """)
    render_html('<div class="app-subtitle">Inventory Management System</div>')

    pages = {
        "Dashboard": page_dashboard,
        "Products": page_products,
        "Receipts": page_receipts,
        "Delivery Orders": page_deliveries,
        "Internal Transfers": page_transfers,
        "Stock Adjustments": page_adjustments,
        "Move History": page_move_history,
        "Settings": page_settings,
        "My Profile": page_profile,
    }
    pages[menu]()


if __name__ == "__main__":
    main()