import sqlite3
import hashlib
import random
import string
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

DB_NAME = "inventory.db"
CATEGORIES = ["Raw Materials", "Finished Goods", "Office Supplies", "Packaging", "Other"]
UOM_OPTIONS = ["pcs", "kg", "g", "litre", "ml", "box", "meter", "pack"]
STATUS_OPTIONS = ["Draft", "Waiting", "Ready", "Done", "Cancelled"]

# ----------------------------------------------------------------------------------
# PAGE CONFIG + GLOBAL STYLE
# ----------------------------------------------------------------------------------
st.set_page_config(page_title="StockSense IMS", page_icon="📦", layout="wide")

ACCENT = "#7c5cff"
ACCENT2 = "#22d3ee"

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', 'Poppins', sans-serif; }
    h1, h2, h3, .app-title { font-family: 'Poppins', sans-serif; }

    .stApp {
        background: radial-gradient(circle at 10% 0%, #1b1030 0%, #0d0f16 45%, #0a0c12 100%);
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(200deg, #171225 0%, #0d0e17 70%);
        border-right: 1px solid rgba(124,92,255,0.15);
    }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }

    .sidebar-brand {
        display: flex; align-items: center; gap: 10px;
        padding: 6px 4px 18px 4px; margin-bottom: 6px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .sidebar-brand-text { font-family: 'Poppins',sans-serif; font-weight: 800; font-size: 1.15rem; color: #f5f6ff; }
    .sidebar-brand-sub { font-size: 0.72rem; color: #8b93ab; margin-top: -3px; }

    .user-chip {
        display: flex; align-items: center; gap: 10px;
        background: linear-gradient(135deg, rgba(124,92,255,0.16), rgba(34,211,238,0.10));
        border: 1px solid rgba(124,92,255,0.3);
        border-radius: 14px; padding: 10px 12px; margin-bottom: 4px;
    }
    .user-avatar {
        width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
        background: linear-gradient(135deg, #7c5cff, #22d3ee);
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; color: #0d0e17; font-family: 'Poppins',sans-serif;
    }
    .user-name { font-weight: 600; color: #f0f1ff; font-size: 0.92rem; line-height: 1.1; }
    .user-role { font-size: 0.72rem; color: #9aa3c0; }

    /* ---- Titles ---- */
    .app-title {
        font-size: 2.15rem; font-weight: 800; letter-spacing: -0.5px;
        background: linear-gradient(90deg, #b794ff 0%, #7c5cff 35%, #22d3ee 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px; display: inline-block;
    }
    .app-subtitle { color: #9aa3b2; margin-top: -4px; margin-bottom: 14px; font-size: 0.95rem; }

    /* ---- Metric / KPI cards ---- */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1e2e 0%, #232a45 100%);
        border: 1px solid #333a58;
        padding: 16px 18px 12px 18px;
        border-radius: 16px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.30);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 26px rgba(124,92,255,0.25);
    }
    div[data-testid="stMetricValue"] { color: #f5f7ff; font-family: 'Poppins', sans-serif; }
    div[data-testid="stMetricLabel"] { color: #a8b0c8; }

    .kpi-card {
        border-radius: 16px; padding: 16px 18px; height: 100%;
        background: linear-gradient(135deg, #1a1e2e 0%, #20263d 100%);
        border-left: 4px solid var(--kpi-color, #7c5cff);
        box-shadow: 0 6px 18px rgba(0,0,0,0.28);
        transition: transform 0.15s ease;
    }
    .kpi-card:hover { transform: translateY(-3px); }
    .kpi-icon { font-size: 1.4rem; }
    .kpi-value { font-family: 'Poppins',sans-serif; font-size: 1.8rem; font-weight: 700; color: #f5f7ff; margin: 2px 0 0 0; }
    .kpi-label { color: #9aa3c0; font-size: 0.82rem; margin-top: 2px; }

    /* ---- Cards / containers ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid rgba(124,92,255,0.18) !important;
        background: linear-gradient(160deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(124,92,255,0.45) !important;
        box-shadow: 0 8px 20px rgba(124,92,255,0.10);
    }

    /* ---- Badges ---- */
    .badge {
        display: inline-block; padding: 4px 12px; border-radius: 999px;
        font-size: 0.76rem; font-weight: 700; letter-spacing: 0.2px;
    }
    .badge-done { background: rgba(74,222,128,0.14); color: #4ade80; border: 1px solid rgba(74,222,128,0.35); }
    .badge-draft { background: rgba(250,204,21,0.14); color: #facc15; border: 1px solid rgba(250,204,21,0.35); }
    .badge-waiting { background: rgba(96,165,250,0.14); color: #60a5fa; border: 1px solid rgba(96,165,250,0.35); }
    .badge-ready { background: rgba(192,132,252,0.14); color: #c084fc; border: 1px solid rgba(192,132,252,0.35); }
    .badge-cancelled { background: rgba(248,113,113,0.14); color: #f87171; border: 1px solid rgba(248,113,113,0.35); }

    /* ---- Buttons ---- */
    .stButton>button {
        border-radius: 10px; font-weight: 600; border: 1px solid #33395a;
        background: linear-gradient(135deg, #1c2030, #232840);
        color: #e7e9f7; transition: all 0.15s ease;
    }
    .stButton>button:hover {
        border-color: #7c5cff; color: #ffffff;
        background: linear-gradient(135deg, #7c5cff, #6a4de8);
        box-shadow: 0 4px 14px rgba(124,92,255,0.35);
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #7c5cff, #22d3ee); border: none; color: #0d0e17;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab"] { font-weight: 600; color: #9aa3c0; }
    .stTabs [aria-selected="true"] { color: #b794ff !important; }

    /* ---- Misc ---- */
    hr { border-color: #262b3a; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-thumb { background: #33395a; border-radius: 8px; }
    .block-container { animation: fadeIn 0.35s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px);} to { opacity: 1; transform: translateY(0);} }
    </style>
    """,
    unsafe_allow_html=True,
)

CATEGORY_ICONS = {
    "Raw Materials": "🧱", "Finished Goods": "📦", "Office Supplies": "🖇️",
    "Packaging": "🥡", "Other": "🔹",
}

LOGO_SVG = """
<svg width="34" height="34" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="lg" x1="0" y1="0" x2="34" y2="34" gradientUnits="userSpaceOnUse">
<stop stop-color="#7c5cff"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs>
<rect width="34" height="34" rx="9" fill="url(#lg)"/>
<path d="M9 12.5L17 8L25 12.5V21.5L17 26L9 21.5V12.5Z" stroke="#0d0e17" stroke-width="1.6" stroke-linejoin="round"/>
<path d="M9 12.5L17 17L25 12.5" stroke="#0d0e17" stroke-width="1.6" stroke-linejoin="round"/>
<path d="M17 17V26" stroke="#0d0e17" stroke-width="1.6"/>
</svg>
"""

HERO_SVG = """
<svg width="100%" height="260" viewBox="0 0 480 320" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="glow" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#7c5cff" stop-opacity="0.55"/>
    <stop offset="100%" stop-color="#22d3ee" stop-opacity="0.35"/>
  </linearGradient>
  <linearGradient id="box1" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#9d7bff"/><stop offset="100%" stop-color="#6a4de8"/>
  </linearGradient>
  <linearGradient id="box2" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#4de0f5"/><stop offset="100%" stop-color="#1fb8cf"/>
  </linearGradient>
  <linearGradient id="box3" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#ffd166"/><stop offset="100%" stop-color="#f0a63a"/>
  </linearGradient>
</defs>
<circle cx="240" cy="160" r="150" fill="url(#glow)" opacity="0.25"/>
<g transform="translate(120,150)">
  <polygon points="0,20 60,0 120,20 60,40" fill="#2a2f4a"/>
  <polygon points="0,20 0,70 60,90 60,40" fill="url(#box1)"/>
  <polygon points="120,20 120,70 60,90 60,40" fill="#5b3fd1"/>
  <line x1="30" y1="30" x2="30" y2="80" stroke="#0d0e17" stroke-width="1.5" opacity="0.4"/>
  <line x1="90" y1="30" x2="90" y2="80" stroke="#0d0e17" stroke-width="1.5" opacity="0.4"/>
</g>
<g transform="translate(30,190)">
  <polygon points="0,15 45,0 90,15 45,30" fill="#173c40"/>
  <polygon points="0,15 0,55 45,68 45,30" fill="url(#box2)"/>
  <polygon points="90,15 90,55 45,68 45,30" fill="#149aab"/>
</g>
<g transform="translate(260,205)">
  <polygon points="0,13 40,0 80,13 40,26" fill="#5a3d12"/>
  <polygon points="0,13 0,48 40,60 40,26" fill="url(#box3)"/>
  <polygon points="80,13 80,48 40,60 40,26" fill="#c67f1f"/>
</g>
<circle cx="90" cy="90" r="4" fill="#7c5cff"/>
<circle cx="360" cy="110" r="5" fill="#22d3ee"/>
<circle cx="380" cy="230" r="3" fill="#ffd166"/>
<circle cx="60" cy="250" r="3" fill="#22d3ee"/>
</svg>
"""


def badge(status: str) -> str:
    cls = {
        "Done": "badge-done", "Draft": "badge-draft", "Waiting": "badge-waiting",
        "Ready": "badge-ready", "Cancelled": "badge-cancelled",
    }.get(status, "badge-draft")
    return f'<span class="badge {cls}">{status}</span>'


def styled_stock_table(view_df: pd.DataFrame, key: str = None):
    if view_df.empty:
        st.info("No matching stock records.")
        return
    display_df = view_df.copy()
    display_df["Category"] = display_df["category"].apply(lambda c: f"{CATEGORY_ICONS.get(c, '🔹')} {c or ''}")
    max_qty = max(int(display_df["quantity"].max()), 1)
    cols = ["name", "sku", "Category", "warehouse", "quantity", "reorder_point"]
    if "uom" in display_df.columns:
        cols.insert(4, "uom")
    if "Status" in display_df.columns:
        cols.append("Status")
    st.dataframe(
        display_df[cols],
        use_container_width=True,
        hide_index=True,
        key=key,
        column_config={
            "name": st.column_config.TextColumn("Product"),
            "sku": st.column_config.TextColumn("SKU"),
            "uom": st.column_config.TextColumn("UOM"),
            "warehouse": st.column_config.TextColumn("Warehouse"),
            "quantity": st.column_config.ProgressColumn("Stock Level", min_value=0, max_value=max_qty, format="%d"),
            "reorder_point": st.column_config.NumberColumn("Reorder At"),
        },
    )


def render_html(text: str):
    """st.markdown treats lines indented 4+ spaces as a code block, which breaks
    HTML built from f-strings inside indented functions (divs/spans/paragraphs
    print as literal text instead of rendering). Stripping each line's leading
    whitespace before handing it to st.markdown avoids that entirely."""
    cleaned = "\n".join(line.lstrip() for line in text.strip("\n").split("\n"))
    st.markdown(cleaned, unsafe_allow_html=True)


def kpi_card(icon: str, label: str, value, color: str):
    render_html(
        f"""
        <div class="kpi-card" style="--kpi-color:{color};">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>
        """
    )


# ----------------------------------------------------------------------------------
# DB HELPERS
# ----------------------------------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def run(query, params=(), fetch=False, many=False):
    conn = get_conn()
    cur = conn.cursor()
    if many:
        cur.executemany(query, params)
    else:
        cur.execute(query, params)
    data = cur.fetchall() if fetch else None
    cols = [d[0] for d in cur.description] if (fetch and cur.description) else None
    conn.commit()
    conn.close()
    if fetch:
        return pd.DataFrame(data, columns=cols) if cols else pd.DataFrame()
    return None


def init_db():
    run("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            email TEXT
        )""")
    run("""CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            otp TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
    run("""CREATE TABLE IF NOT EXISTS warehouses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            location TEXT
        )""")
    run("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            category TEXT,
            uom TEXT,
            reorder_point INTEGER DEFAULT 5,
            reorder_qty INTEGER DEFAULT 20
        )""")
    run("""CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 0,
            UNIQUE(product_id, warehouse_id)
        )""")
    run("""CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT, warehouse_id INTEGER,
            status TEXT DEFAULT 'Draft', created_at TEXT
        )""")
    run("""CREATE TABLE IF NOT EXISTS receipt_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id INTEGER, product_id INTEGER, quantity INTEGER
        )""")
    run("""CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT, warehouse_id INTEGER,
            status TEXT DEFAULT 'Draft', created_at TEXT
        )""")
    run("""CREATE TABLE IF NOT EXISTS delivery_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_id INTEGER, product_id INTEGER, quantity INTEGER
        )""")
    run("""CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER, from_warehouse_id INTEGER, to_warehouse_id INTEGER,
            quantity INTEGER, status TEXT DEFAULT 'Draft', created_at TEXT
        )""")
    run("""CREATE TABLE IF NOT EXISTS adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER, warehouse_id INTEGER,
            counted_qty INTEGER, diff INTEGER, created_at TEXT
        )""")
    run("""CREATE TABLE IF NOT EXISTS move_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, product_id INTEGER, warehouse_id INTEGER,
            change_qty INTEGER, move_type TEXT, reference TEXT
        )""")


def seed_defaults():
    wh = run("SELECT COUNT(*) c FROM warehouses", fetch=True)
    if wh.iloc[0]["c"] == 0:
        run("INSERT INTO warehouses (name, location) VALUES (?,?)", ("Main Warehouse", "HQ"))


def migrate_schema():
    """Fixes up an old/pre-existing inventory.db so it matches the current schema,
    instead of erroring out. Safe to run every time the app starts."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(products)")
    prod_cols = [r[1] for r in cur.fetchall()]

    if "category" not in prod_cols:
        cur.execute("ALTER TABLE products ADD COLUMN category TEXT")
    if "uom" not in prod_cols:
        cur.execute("ALTER TABLE products ADD COLUMN uom TEXT DEFAULT 'pcs'")
    if "reorder_point" not in prod_cols:
        cur.execute("ALTER TABLE products ADD COLUMN reorder_point INTEGER DEFAULT 5")
    if "reorder_qty" not in prod_cols:
        cur.execute("ALTER TABLE products ADD COLUMN reorder_qty INTEGER DEFAULT 20")
    conn.commit()

    # If this is an old database that stored quantity directly on products,
    # carry that stock over into the new per-warehouse stock table once.
    cur.execute("PRAGMA table_info(products)")
    prod_cols = [r[1] for r in cur.fetchall()]
    if "quantity" in prod_cols:
        cur.execute("SELECT id FROM warehouses ORDER BY id LIMIT 1")
        wh_row = cur.fetchone()
        if wh_row:
            default_wh = wh_row[0]
            cur.execute("SELECT id, quantity FROM products")
            for pid, qty in cur.fetchall():
                cur.execute("SELECT COUNT(*) FROM stock WHERE product_id=?", (pid,))
                already_has_stock = cur.fetchone()[0]
                if already_has_stock == 0 and qty:
                    cur.execute(
                        "INSERT INTO stock (product_id, warehouse_id, quantity) VALUES (?,?,?)",
                        (pid, default_wh, qty),
                    )
            conn.commit()

    conn.close()


# ----------------------------------------------------------------------------------
# AUTH HELPERS
# ----------------------------------------------------------------------------------
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def create_user(username, password, full_name, email):
    try:
        run("INSERT INTO users (username, password_hash, full_name, email) VALUES (?,?,?,?)",
            (username, hash_pw(password), full_name, email))
        return True, "Account created! Please log in."
    except sqlite3.IntegrityError:
        return False, "That username is already taken."


def check_login(username, password):
    df = run("SELECT * FROM users WHERE username=?", (username,), fetch=True)
    if df.empty:
        return False
    return df.iloc[0]["password_hash"] == hash_pw(password)


def generate_otp(username):
    otp = "".join(random.choices(string.digits, k=6))
    run("INSERT INTO password_resets (username, otp, created_at) VALUES (?,?,?)",
        (username, otp, datetime.now().isoformat()))
    return otp


def verify_otp(username, otp):
    df = run("SELECT * FROM password_resets WHERE username=? ORDER BY id DESC LIMIT 1",
              (username,), fetch=True)
    if df.empty:
        return False
    row = df.iloc[0]
    created = datetime.fromisoformat(row["created_at"])
    if datetime.now() - created > timedelta(minutes=10):
        return False
    return row["otp"] == otp


def reset_password(username, new_password):
    run("UPDATE users SET password_hash=? WHERE username=?", (hash_pw(new_password), username))


# ----------------------------------------------------------------------------------
# STOCK / LEDGER HELPERS
# ----------------------------------------------------------------------------------
def get_stock_qty(product_id, warehouse_id):
    df = run("SELECT quantity FROM stock WHERE product_id=? AND warehouse_id=?",
              (product_id, warehouse_id), fetch=True)
    return int(df.iloc[0]["quantity"]) if not df.empty else 0


def adjust_stock(product_id, warehouse_id, delta):
    current = get_stock_qty(product_id, warehouse_id)
    new_qty = current + delta
    run("""INSERT INTO stock (product_id, warehouse_id, quantity) VALUES (?,?,?)
           ON CONFLICT(product_id, warehouse_id) DO UPDATE SET quantity=?""",
        (product_id, warehouse_id, new_qty, new_qty))


def set_stock_qty(product_id, warehouse_id, qty):
    run("""INSERT INTO stock (product_id, warehouse_id, quantity) VALUES (?,?,?)
           ON CONFLICT(product_id, warehouse_id) DO UPDATE SET quantity=?""",
        (product_id, warehouse_id, qty, qty))


def log_move(product_id, warehouse_id, change_qty, move_type, reference):
    run("""INSERT INTO move_history (timestamp, product_id, warehouse_id, change_qty, move_type, reference)
           VALUES (?,?,?,?,?,?)""",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_id, warehouse_id, change_qty, move_type, reference))


def get_products_df():
    return run("SELECT * FROM products ORDER BY name", fetch=True)


def get_warehouses_df():
    return run("SELECT * FROM warehouses ORDER BY name", fetch=True)


def get_stock_df():
    q = """
    SELECT p.id as product_id, p.name, p.sku, p.category, p.uom,
           p.reorder_point, w.id as warehouse_id, w.name as warehouse,
           COALESCE(s.quantity,0) as quantity
    FROM products p
    CROSS JOIN warehouses w
    LEFT JOIN stock s ON s.product_id=p.id AND s.warehouse_id=w.id
    ORDER BY p.name, w.name
    """
    return run(q, fetch=True)


def product_label_map(df):
    return {f"{r['name']} ({r['sku']})": r["id"] for _, r in df.iterrows()}


def warehouse_label_map(df):
    return {r["name"]: r["id"] for _, r in df.iterrows()}


# ----------------------------------------------------------------------------------
# AUTH PAGES
# ----------------------------------------------------------------------------------
def auth_screen():
    hero_col, form_col = st.columns([1.1, 1], gap="large")

    with hero_col:
        render_html(
            f"""
            <div style="padding-top:10px;">
                <div style="display:flex;align-items:center;gap:12px;">{LOGO_SVG}
                    <span class="app-title" style="font-size:2rem;">StockSense</span>
                </div>
                <p style="color:#c3c8e0; font-size:1.05rem; max-width:420px; margin-top:14px;">
                    One clean dashboard for every receipt, delivery, transfer and stock count —
                    built to replace registers, spreadsheets and guesswork.
                </p>
                {HERO_SVG}
            </div>
            """
        )
        f1, f2, f3 = st.columns(3)
        f1.markdown("✅ **Multi-warehouse**")
        f2.markdown("📊 **Live dashboard**")
        f3.markdown("🔒 **Secure login**")

    with form_col:
        render_html('<div class="app-subtitle" style="margin-top:0;">Welcome — sign in to continue</div>')
        tab_login, tab_signup, tab_forgot = st.tabs(["🔐 Log In", "🆕 Sign Up", "❓ Forgot Password"])
        _auth_tabs_body(tab_login, tab_signup, tab_forgot)


def _auth_tabs_body(tab_login, tab_signup, tab_forgot):

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Log In", use_container_width=True)
            if submitted:
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Welcome back! Redirecting to dashboard...")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab_signup:
        with st.form("signup_form"):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            new_user = st.text_input("Choose a Username")
            new_pass = st.text_input("Choose a Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                if not new_user.strip() or not new_pass.strip():
                    st.warning("Username and password are required.")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = create_user(new_user.strip(), new_pass, full_name.strip(), email.strip())
                    (st.success if ok else st.error)(msg)

    with tab_forgot:
        st.caption("This demo simulates OTP delivery by showing it on screen instead of emailing it, "
                   "since no email service is configured yet.")
        if "otp_stage" not in st.session_state:
            st.session_state.otp_stage = "request"

        if st.session_state.otp_stage == "request":
            with st.form("otp_request_form"):
                fp_user = st.text_input("Enter your Username")
                req_submit = st.form_submit_button("Send OTP", use_container_width=True)
                if req_submit:
                    df = run("SELECT * FROM users WHERE username=?", (fp_user,), fetch=True)
                    if df.empty:
                        st.error("No account found with that username.")
                    else:
                        otp = generate_otp(fp_user)
                        st.session_state.otp_stage = "verify"
                        st.session_state.otp_user = fp_user
                        st.info(f"Your OTP is: **{otp}** (valid for 10 minutes)")
                        st.rerun()

        if st.session_state.otp_stage == "verify":
            st.write(f"Resetting password for **{st.session_state.otp_user}**")
            with st.form("otp_verify_form"):
                otp_input = st.text_input("Enter OTP")
                new_pw = st.text_input("New Password", type="password")
                confirm_pw = st.text_input("Confirm New Password", type="password")
                verify_submit = st.form_submit_button("Reset Password", use_container_width=True)
                if verify_submit:
                    if new_pw != confirm_pw:
                        st.error("Passwords do not match.")
                    elif not verify_otp(st.session_state.otp_user, otp_input):
                        st.error("Invalid or expired OTP.")
                    else:
                        reset_password(st.session_state.otp_user, new_pw)
                        st.success("Password reset! You can now log in.")
                        st.session_state.otp_stage = "request"
            if st.button("Start Over"):
                st.session_state.otp_stage = "request"
                st.rerun()


# ----------------------------------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------------------------------
def page_dashboard():
    st.subheader("📊 Inventory Dashboard")

    products = get_products_df()
    warehouses = get_warehouses_df()
    stock_df = get_stock_df()

    total_products = len(products)
    low_stock_df = stock_df[stock_df["quantity"] < stock_df["reorder_point"]] if not stock_df.empty else pd.DataFrame()
    low_stock_count = low_stock_df["product_id"].nunique() if not low_stock_df.empty else 0

    pending_receipts = run("SELECT COUNT(*) c FROM receipts WHERE status NOT IN ('Done','Cancelled')", fetch=True).iloc[0]["c"]
    pending_deliveries = run("SELECT COUNT(*) c FROM deliveries WHERE status NOT IN ('Done','Cancelled')", fetch=True).iloc[0]["c"]
    scheduled_transfers = run("SELECT COUNT(*) c FROM transfers WHERE status NOT IN ('Done','Cancelled')", fetch=True).iloc[0]["c"]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("📦", "Total Products", total_products, "#7c5cff")
    with c2:
        kpi_card("⚠️", "Low / Out of Stock", int(low_stock_count), "#f87171")
    with c3:
        kpi_card("📥", "Pending Receipts", int(pending_receipts), "#60a5fa")
    with c4:
        kpi_card("📤", "Pending Deliveries", int(pending_deliveries), "#22d3ee")
    with c5:
        kpi_card("🔁", "Transfers Scheduled", int(scheduled_transfers), "#facc15")

    st.write("---")
    st.write("### 🔍 Filters")
    fc1, fc2, fc3, fc4 = st.columns(4)
    doc_type = fc1.selectbox("Document Type", ["All", "Receipts", "Delivery", "Internal", "Adjustments"])
    status_filter = fc2.selectbox("Status", ["All"] + STATUS_OPTIONS)
    wh_filter = fc3.selectbox("Warehouse", ["All"] + list(warehouses["name"]) if not warehouses.empty else ["All"])
    cat_filter = fc4.selectbox("Category", ["All"] + sorted(products["category"].dropna().unique().tolist()) if not products.empty else ["All"])

    ops_df = build_operations_view(doc_type, status_filter, wh_filter, cat_filter)
    st.write("### 📋 Operations Overview")
    if ops_df.empty:
        st.info("No operations match the selected filters.")
    else:
        display_df = ops_df.copy()
        display_df["status"] = display_df["status"].apply(badge)
        render_html(display_df.to_html(escape=False, index=False))

    st.write("---")
    if not stock_df.empty and stock_df["quantity"].sum() > 0:
        st.write("### 📊 Stock Distribution by Category")
        cat_summary = stock_df.groupby("category")["quantity"].sum().reset_index()
        fig = px.pie(cat_summary, values="quantity", names="category", hole=0.55,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)",
                           font=dict(color="#FAFAFA"),
                           legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig, use_container_width=True)

    if not low_stock_df.empty:
        st.write("---")
        st.error(f"⚠️ {low_stock_count} product(s) are low or out of stock!")
        styled_stock_table(low_stock_df, key="low_stock_table")


def build_operations_view(doc_type, status_filter, wh_filter, cat_filter):
    rows = []

    if doc_type in ("All", "Receipts"):
        df = run("""SELECT r.id, 'Receipt' as doc_type, r.supplier as party, w.name as warehouse, r.status, r.created_at
                    FROM receipts r LEFT JOIN warehouses w ON w.id=r.warehouse_id""", fetch=True)
        if not df.empty:
            df = _apply_category_filter(df, "receipt_items", cat_filter)
            rows.append(df)

    if doc_type in ("All", "Delivery"):
        df = run("""SELECT d.id, 'Delivery' as doc_type, d.customer as party, w.name as warehouse, d.status, d.created_at
                    FROM deliveries d LEFT JOIN warehouses w ON w.id=d.warehouse_id""", fetch=True)
        if not df.empty:
            df = _apply_category_filter(df, "delivery_items", cat_filter)
            rows.append(df)

    if doc_type in ("All", "Internal"):
        df = run("""SELECT t.id, 'Internal Transfer' as doc_type,
                    (fw.name || ' -> ' || tw.name) as party,
                    fw.name as warehouse, t.status, t.created_at, p.category
                    FROM transfers t
                    LEFT JOIN warehouses fw ON fw.id=t.from_warehouse_id
                    LEFT JOIN warehouses tw ON tw.id=t.to_warehouse_id
                    LEFT JOIN products p ON p.id=t.product_id""", fetch=True)
        if not df.empty:
            if cat_filter != "All":
                df = df[df["category"] == cat_filter]
            df = df.drop(columns=["category"], errors="ignore")
            rows.append(df)

    if doc_type in ("All", "Adjustments"):
        df = run("""SELECT a.id, 'Adjustment' as doc_type, 'Stock Count' as party,
                    w.name as warehouse, 'Done' as status, a.created_at, p.category
                    FROM adjustments a
                    LEFT JOIN warehouses w ON w.id=a.warehouse_id
                    LEFT JOIN products p ON p.id=a.product_id""", fetch=True)
        if not df.empty:
            if cat_filter != "All":
                df = df[df["category"] == cat_filter]
            df = df.drop(columns=["category"], errors="ignore")
            rows.append(df)

    if not rows:
        return pd.DataFrame()

    combined = pd.concat(rows, ignore_index=True)
    if wh_filter != "All":
        combined = combined[combined["warehouse"] == wh_filter]
    if status_filter != "All":
        combined = combined[combined["status"] == status_filter]
    return combined.sort_values("created_at", ascending=False)


def _apply_category_filter(df, items_table, cat_filter):
    if cat_filter == "All":
        return df
    keep_ids = run(f"""SELECT DISTINCT {items_table[:-6] if items_table.endswith('_items') else items_table}_id
                       FROM {items_table} i JOIN products p ON p.id=i.product_id
                       WHERE p.category=?""", (cat_filter,), fetch=True)
    if keep_ids.empty:
        return df.iloc[0:0]
    id_col = keep_ids.columns[0]
    return df[df["id"].isin(keep_ids[id_col])]


# ----------------------------------------------------------------------------------
# PRODUCTS PAGE
# ----------------------------------------------------------------------------------
def page_products():
    st.subheader("🧾 Product Management")
    warehouses = get_warehouses_df()

    if warehouses.empty:
        st.warning("Add at least one warehouse in Settings before creating products.")
        return

    with st.expander("➕ Add New Product", expanded=False):
        with st.form("add_product_form", clear_on_submit=True):
            name = st.text_input("Product Name*")
            sku = st.text_input("SKU / Code*")
            category = st.selectbox("Category", CATEGORIES)
            uom = st.selectbox("Unit of Measure", UOM_OPTIONS)
            wh_map = warehouse_label_map(warehouses)
            init_wh = st.selectbox("Initial Warehouse", list(wh_map.keys()))
            init_qty = st.number_input("Initial Stock", min_value=0, step=1, value=0)
            reorder_point = st.number_input("Reorder Point (low-stock alert threshold)", min_value=0, step=1, value=5)
            reorder_qty = st.number_input("Reorder Quantity", min_value=0, step=1, value=20)
            submitted = st.form_submit_button("Save Product", use_container_width=True)

            if submitted:
                if name.strip() and sku.strip():
                    try:
                        run("""INSERT INTO products (name, sku, category, uom, reorder_point, reorder_qty)
                               VALUES (?,?,?,?,?,?)""",
                            (name.strip(), sku.strip(), category, uom, reorder_point, reorder_qty))
                        new_id = run("SELECT id FROM products WHERE sku=?", (sku.strip(),), fetch=True).iloc[0]["id"]
                        if init_qty > 0:
                            set_stock_qty(int(new_id), wh_map[init_wh], int(init_qty))
                            log_move(int(new_id), wh_map[init_wh], int(init_qty), "Initial Stock", f"Product #{new_id}")
                        st.success(f"Product '{name}' added successfully!")
                    except sqlite3.IntegrityError:
                        st.error("A product with this SKU already exists.")
                else:
                    st.warning("Please fill in both Name and SKU.")

    st.write("---")
    st.write("### 📦 Current Inventory (per warehouse)")
    stock_df = get_stock_df()
    if stock_df.empty:
        st.info("No products registered yet.")
        return

    fc1, fc2, fc3 = st.columns(3)
    search_query = fc1.text_input("🔍 Search by Name or SKU")
    cat_options = ["All"] + sorted(stock_df["category"].dropna().unique().tolist())
    selected_category = fc2.selectbox("Filter by Category", cat_options)
    wh_options = ["All"] + list(warehouses["name"])
    selected_wh = fc3.selectbox("Filter by Warehouse", wh_options)

    view = stock_df.copy()
    if selected_category != "All":
        view = view[view["category"] == selected_category]
    if selected_wh != "All":
        view = view[view["warehouse"] == selected_wh]
    if search_query.strip():
        view = view[
            view["name"].str.contains(search_query, case=False, na=False)
            | view["sku"].str.contains(search_query, case=False, na=False)
        ]
    view["Status"] = view.apply(lambda r: "⚠️ Low Stock" if r["quantity"] < r["reorder_point"] else "✅ In Stock", axis=1)
    styled_stock_table(view, key="products_table")

    with st.expander("🛠️ Edit or Delete a Product"):
        products = get_products_df()
        pmap = product_label_map(products)
        if pmap:
            selected_label = st.selectbox("Select a product", list(pmap.keys()))
            pid = pmap[selected_label]
            prow = products[products["id"] == pid].iloc[0]

            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("Name", value=prow["name"], key="edit_name")
                edit_category = st.selectbox("Category", CATEGORIES,
                                              index=CATEGORIES.index(prow["category"]) if prow["category"] in CATEGORIES else 0,
                                              key="edit_cat")
                edit_uom = st.selectbox("UOM", UOM_OPTIONS,
                                         index=UOM_OPTIONS.index(prow["uom"]) if prow["uom"] in UOM_OPTIONS else 0,
                                         key="edit_uom")
            with col2:
                edit_reorder_point = st.number_input("Reorder Point", min_value=0, step=1,
                                                       value=int(prow["reorder_point"]), key="edit_rp")
                edit_reorder_qty = st.number_input("Reorder Quantity", min_value=0, step=1,
                                                     value=int(prow["reorder_qty"]), key="edit_rq")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Update Product", use_container_width=True):
                    run("""UPDATE products SET name=?, category=?, uom=?, reorder_point=?, reorder_qty=?
                           WHERE id=?""",
                        (edit_name, edit_category, edit_uom, edit_reorder_point, edit_reorder_qty, int(pid)))
                    st.success("Product updated!")
                    st.rerun()
            with b2:
                if st.button("🗑️ Delete Product", use_container_width=True):
                    run("DELETE FROM products WHERE id=?", (int(pid),))
                    run("DELETE FROM stock WHERE product_id=?", (int(pid),))
                    st.warning("Product deleted!")
                    st.rerun()


# ----------------------------------------------------------------------------------
# RECEIPTS
# ----------------------------------------------------------------------------------
def page_receipts():
    st.subheader("📥 Receipts (Incoming Stock)")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or warehouses.empty:
        st.info("Add products and warehouses first.")
        return

    with st.expander("➕ New Receipt", expanded=False):
        with st.form("new_receipt_form", clear_on_submit=True):
            supplier = st.text_input("Supplier")
            wh_map = warehouse_label_map(warehouses)
            wh_choice = st.selectbox("Warehouse", list(wh_map.keys()))
            submitted = st.form_submit_button("Create Draft Receipt", use_container_width=True)
            if submitted:
                run("INSERT INTO receipts (supplier, warehouse_id, status, created_at) VALUES (?,?,?,?)",
                    (supplier, wh_map[wh_choice], "Draft", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                st.success("Draft receipt created below — add product lines to it.")

    st.write("---")
    receipts = run("""SELECT r.*, w.name as warehouse_name FROM receipts r
                       LEFT JOIN warehouses w ON w.id=r.warehouse_id ORDER BY r.id DESC""", fetch=True)
    if receipts.empty:
        st.info("No receipts yet.")
        return

    for _, r in receipts.iterrows():
        with st.container(border=True):
            top = st.columns([3, 2, 2, 2])
            top[0].markdown(f"**Receipt #{r['id']} — {r['supplier'] or 'No supplier'}**")
            top[1].markdown(f"Warehouse: {r['warehouse_name']}")
            top[2].markdown(badge(r["status"]), unsafe_allow_html=True)
            top[3].caption(r["created_at"])

            items = run("""SELECT ri.id, p.name, p.sku, ri.quantity, ri.product_id FROM receipt_items ri
                           JOIN products p ON p.id=ri.product_id WHERE ri.receipt_id=?""", (r["id"],), fetch=True)
            if not items.empty:
                st.dataframe(items[["name", "sku", "quantity"]], use_container_width=True, hide_index=True)

            if r["status"] == "Draft":
                pmap = product_label_map(products)
                ac1, ac2, ac3 = st.columns([3, 1, 1])
                prod_choice = ac1.selectbox("Add product", list(pmap.keys()), key=f"rp_{r['id']}")
                qty_choice = ac2.number_input("Qty", min_value=1, step=1, value=1, key=f"rq_{r['id']}")
                if ac3.button("Add Line", key=f"radd_{r['id']}", use_container_width=True):
                    run("INSERT INTO receipt_items (receipt_id, product_id, quantity) VALUES (?,?,?)",
                        (int(r["id"]), pmap[prod_choice], int(qty_choice)))
                    st.rerun()

                bc1, bc2 = st.columns(2)
                if bc1.button("✅ Validate Receipt", key=f"rval_{r['id']}", use_container_width=True):
                    if items.empty:
                        st.warning("Add at least one product line first.")
                    else:
                        for _, it in items.iterrows():
                            adjust_stock(int(it["product_id"]), int(r["warehouse_id"]), int(it["quantity"]))
                            log_move(int(it["product_id"]), int(r["warehouse_id"]), int(it["quantity"]),
                                      "Receipt", f"Receipt #{r['id']}")
                        run("UPDATE receipts SET status='Done' WHERE id=?", (int(r["id"]),))
                        st.success("Receipt validated — stock increased.")
                        st.rerun()
                if bc2.button("🚫 Cancel Receipt", key=f"rcancel_{r['id']}", use_container_width=True):
                    run("UPDATE receipts SET status='Cancelled' WHERE id=?", (int(r["id"]),))
                    st.rerun()


# ----------------------------------------------------------------------------------
# DELIVERIES
# ----------------------------------------------------------------------------------
def page_deliveries():
    st.subheader("📤 Delivery Orders (Outgoing Stock)")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or warehouses.empty:
        st.info("Add products and warehouses first.")
        return

    with st.expander("➕ New Delivery Order", expanded=False):
        with st.form("new_delivery_form", clear_on_submit=True):
            customer = st.text_input("Customer")
            wh_map = warehouse_label_map(warehouses)
            wh_choice = st.selectbox("Warehouse", list(wh_map.keys()))
            submitted = st.form_submit_button("Create Draft Delivery", use_container_width=True)
            if submitted:
                run("INSERT INTO deliveries (customer, warehouse_id, status, created_at) VALUES (?,?,?,?)",
                    (customer, wh_map[wh_choice], "Draft", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                st.success("Draft delivery created below — add product lines to it.")

    st.write("---")
    deliveries = run("""SELECT d.*, w.name as warehouse_name FROM deliveries d
                         LEFT JOIN warehouses w ON w.id=d.warehouse_id ORDER BY d.id DESC""", fetch=True)
    if deliveries.empty:
        st.info("No delivery orders yet.")
        return

    for _, d in deliveries.iterrows():
        with st.container(border=True):
            top = st.columns([3, 2, 2, 2])
            top[0].markdown(f"**Delivery #{d['id']} — {d['customer'] or 'No customer'}**")
            top[1].markdown(f"Warehouse: {d['warehouse_name']}")
            top[2].markdown(badge(d["status"]), unsafe_allow_html=True)
            top[3].caption(d["created_at"])

            items = run("""SELECT di.id, p.name, p.sku, di.quantity, di.product_id FROM delivery_items di
                           JOIN products p ON p.id=di.product_id WHERE di.delivery_id=?""", (d["id"],), fetch=True)
            if not items.empty:
                st.dataframe(items[["name", "sku", "quantity"]], use_container_width=True, hide_index=True)

            if d["status"] == "Draft":
                pmap = product_label_map(products)
                ac1, ac2, ac3 = st.columns([3, 1, 1])
                prod_choice = ac1.selectbox("Pick product", list(pmap.keys()), key=f"dp_{d['id']}")
                qty_choice = ac2.number_input("Qty", min_value=1, step=1, value=1, key=f"dq_{d['id']}")
                if ac3.button("Add Line", key=f"dadd_{d['id']}", use_container_width=True):
                    run("INSERT INTO delivery_items (delivery_id, product_id, quantity) VALUES (?,?,?)",
                        (int(d["id"]), pmap[prod_choice], int(qty_choice)))
                    st.rerun()

                bc1, bc2 = st.columns(2)
                if bc1.button("✅ Validate & Ship", key=f"dval_{d['id']}", use_container_width=True):
                    if items.empty:
                        st.warning("Add at least one product line first.")
                    else:
                        shortage = [it for _, it in items.iterrows()
                                    if get_stock_qty(int(it["product_id"]), int(d["warehouse_id"])) < it["quantity"]]
                        if shortage:
                            st.error("Not enough stock for one or more items — cannot validate.")
                        else:
                            for _, it in items.iterrows():
                                adjust_stock(int(it["product_id"]), int(d["warehouse_id"]), -int(it["quantity"]))
                                log_move(int(it["product_id"]), int(d["warehouse_id"]), -int(it["quantity"]),
                                          "Delivery", f"Delivery #{d['id']}")
                            run("UPDATE deliveries SET status='Done' WHERE id=?", (int(d["id"]),))
                            st.success("Delivery validated — stock decreased.")
                            st.rerun()
                if bc2.button("🚫 Cancel Delivery", key=f"dcancel_{d['id']}", use_container_width=True):
                    run("UPDATE deliveries SET status='Cancelled' WHERE id=?", (int(d["id"]),))
                    st.rerun()


# ----------------------------------------------------------------------------------
# INTERNAL TRANSFERS
# ----------------------------------------------------------------------------------
def page_transfers():
    st.subheader("🔁 Internal Transfers")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or len(warehouses) < 2:
        st.info("You need at least 2 warehouses and 1 product to create a transfer.")
        return

    with st.form("transfer_form", clear_on_submit=True):
        pmap = product_label_map(products)
        wh_map = warehouse_label_map(warehouses)
        prod_choice = st.selectbox("Product", list(pmap.keys()))
        c1, c2, c3 = st.columns(3)
        from_wh = c1.selectbox("From Warehouse / Location", list(wh_map.keys()))
        to_wh = c2.selectbox("To Warehouse / Location", list(wh_map.keys()), index=min(1, len(wh_map) - 1))
        qty = c3.number_input("Quantity", min_value=1, step=1, value=1)
        submitted = st.form_submit_button("Transfer Stock", use_container_width=True)

        if submitted:
            if from_wh == to_wh:
                st.warning("Source and destination must be different.")
            else:
                pid = pmap[prod_choice]
                available = get_stock_qty(pid, wh_map[from_wh])
                if available < qty:
                    st.error(f"Not enough stock in {from_wh} (available: {available}).")
                else:
                    adjust_stock(pid, wh_map[from_wh], -int(qty))
                    adjust_stock(pid, wh_map[to_wh], int(qty))
                    run("""INSERT INTO transfers (product_id, from_warehouse_id, to_warehouse_id, quantity, status, created_at)
                           VALUES (?,?,?,?,?,?)""",
                        (pid, wh_map[from_wh], wh_map[to_wh], int(qty), "Done",
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    log_move(pid, wh_map[from_wh], -int(qty), "Internal Transfer", f"To {to_wh}")
                    log_move(pid, wh_map[to_wh], int(qty), "Internal Transfer", f"From {from_wh}")
                    st.success(f"Moved {qty} unit(s) from {from_wh} to {to_wh}.")
                    st.rerun()

    st.write("---")
    st.write("### 📜 Transfer History")
    hist = run("""SELECT t.id, p.name, p.sku, fw.name as from_wh, tw.name as to_wh,
                  t.quantity, t.status, t.created_at
                  FROM transfers t
                  JOIN products p ON p.id=t.product_id
                  JOIN warehouses fw ON fw.id=t.from_warehouse_id
                  JOIN warehouses tw ON tw.id=t.to_warehouse_id
                  ORDER BY t.id DESC""", fetch=True)
    if hist.empty:
        st.info("No transfers recorded yet.")
    else:
        st.dataframe(hist, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------------
# ADJUSTMENTS
# ----------------------------------------------------------------------------------
def page_adjustments():
    st.subheader("🧮 Stock Adjustments")
    products = get_products_df()
    warehouses = get_warehouses_df()
    if products.empty or warehouses.empty:
        st.info("Add products and warehouses first.")
        return

    with st.form("adjustment_form", clear_on_submit=True):
        pmap = product_label_map(products)
        wh_map = warehouse_label_map(warehouses)
        prod_choice = st.selectbox("Product", list(pmap.keys()))
        wh_choice = st.selectbox("Warehouse / Location", list(wh_map.keys()))
        pid, wid = pmap[prod_choice], wh_map[wh_choice]
        current_qty = get_stock_qty(pid, wid)
        st.caption(f"System recorded stock: **{current_qty}**")
        counted_qty = st.number_input("Physical Counted Quantity", min_value=0, step=1, value=current_qty)
        submitted = st.form_submit_button("Apply Adjustment", use_container_width=True)

        if submitted:
            diff = int(counted_qty) - current_qty
            set_stock_qty(pid, wid, int(counted_qty))
            run("""INSERT INTO adjustments (product_id, warehouse_id, counted_qty, diff, created_at)
                   VALUES (?,?,?,?,?)""",
                (pid, wid, int(counted_qty), diff, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            log_move(pid, wid, diff, "Adjustment", "Physical count")
            st.success(f"Stock adjusted by {diff:+d}. New quantity: {counted_qty}.")
            st.rerun()

    st.write("---")
    st.write("### 📜 Adjustment History")
    hist = run("""SELECT a.id, p.name, p.sku, w.name as warehouse, a.counted_qty, a.diff, a.created_at
                  FROM adjustments a JOIN products p ON p.id=a.product_id
                  JOIN warehouses w ON w.id=a.warehouse_id ORDER BY a.id DESC""", fetch=True)
    if hist.empty:
        st.info("No adjustments recorded yet.")
    else:
        st.dataframe(hist, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------------
# MOVE HISTORY (LEDGER)
# ----------------------------------------------------------------------------------
def page_move_history():
    st.subheader("📜 Move History (Stock Ledger)")
    products = get_products_df()
    warehouses = get_warehouses_df()

    c1, c2, c3 = st.columns(3)
    prod_filter = c1.selectbox("Product", ["All"] + list(products["name"]) if not products.empty else ["All"])
    wh_filter = c2.selectbox("Warehouse", ["All"] + list(warehouses["name"]) if not warehouses.empty else ["All"])
    type_filter = c3.selectbox("Move Type", ["All", "Receipt", "Delivery", "Internal Transfer", "Adjustment", "Initial Stock"])

    ledger = run("""SELECT m.timestamp, p.name as product, w.name as warehouse,
                    m.change_qty, m.move_type, m.reference
                    FROM move_history m
                    JOIN products p ON p.id=m.product_id
                    JOIN warehouses w ON w.id=m.warehouse_id
                    ORDER BY m.id DESC""", fetch=True)

    if ledger.empty:
        st.info("No stock movements recorded yet.")
        return

    if prod_filter != "All":
        ledger = ledger[ledger["product"] == prod_filter]
    if wh_filter != "All":
        ledger = ledger[ledger["warehouse"] == wh_filter]
    if type_filter != "All":
        ledger = ledger[ledger["move_type"] == type_filter]

    st.dataframe(ledger, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------------
# SETTINGS (WAREHOUSES)
# ----------------------------------------------------------------------------------
def page_settings():
    st.subheader("⚙️ Settings — Warehouses")

    with st.form("add_warehouse_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        wh_name = c1.text_input("Warehouse / Location Name")
        wh_location = c2.text_input("Address / Notes")
        submitted = st.form_submit_button("Add Warehouse", use_container_width=True)
        if submitted:
            if not wh_name.strip():
                st.warning("Name is required.")
            else:
                try:
                    run("INSERT INTO warehouses (name, location) VALUES (?,?)", (wh_name.strip(), wh_location.strip()))
                    st.success(f"Warehouse '{wh_name}' added.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("A warehouse with that name already exists.")

    st.write("---")
    warehouses = get_warehouses_df()
    if warehouses.empty:
        st.info("No warehouses yet.")
        return
    st.dataframe(warehouses, use_container_width=True, hide_index=True)

    with st.expander("🗑️ Delete a Warehouse"):
        wmap = warehouse_label_map(warehouses)
        wh_choice = st.selectbox("Select warehouse to delete", list(wmap.keys()))
        if st.button("Delete Warehouse", use_container_width=True):
            wid = wmap[wh_choice]
            in_use = run("SELECT COUNT(*) c FROM stock WHERE warehouse_id=? AND quantity>0", (wid,), fetch=True).iloc[0]["c"]
            if in_use > 0:
                st.error("This warehouse still has stock in it — move or clear stock before deleting.")
            else:
                run("DELETE FROM warehouses WHERE id=?", (wid,))
                st.warning("Warehouse deleted.")
                st.rerun()


# ----------------------------------------------------------------------------------
# PROFILE
# ----------------------------------------------------------------------------------
def page_profile():
    st.subheader("👤 My Profile")
    user = run("SELECT * FROM users WHERE username=?", (st.session_state.username,), fetch=True).iloc[0]

    with st.form("profile_form"):
        full_name = st.text_input("Full Name", value=user["full_name"] or "")
        email = st.text_input("Email", value=user["email"] or "")
        submitted = st.form_submit_button("Save Changes", use_container_width=True)
        if submitted:
            run("UPDATE users SET full_name=?, email=? WHERE username=?",
                (full_name, email, st.session_state.username))
            st.success("Profile updated.")

    st.write("---")
    st.write("### 🔑 Change Password")
    with st.form("change_pw_form", clear_on_submit=True):
        old_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        submitted_pw = st.form_submit_button("Update Password", use_container_width=True)
        if submitted_pw:
            if not check_login(st.session_state.username, old_pw):
                st.error("Current password is incorrect.")
            elif new_pw != confirm_pw:
                st.error("New passwords do not match.")
            elif not new_pw.strip():
                st.warning("New password cannot be empty.")
            else:
                reset_password(st.session_state.username, new_pw)
                st.success("Password updated.")


# ----------------------------------------------------------------------------------
# MAIN APP
# ----------------------------------------------------------------------------------
def main():
    init_db()
    seed_defaults()
    migrate_schema()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        auth_screen()
        return

    user_row = run("SELECT * FROM users WHERE username=?", (st.session_state.username,), fetch=True)
    display_name = st.session_state.username
    if not user_row.empty and user_row.iloc[0]["full_name"]:
        display_name = user_row.iloc[0]["full_name"]
    initial = display_name.strip()[0].upper() if display_name.strip() else "U"

    with st.sidebar:
        render_html(
            f"""
            <div class="sidebar-brand">{LOGO_SVG}
                <div>
                    <div class="sidebar-brand-text">StockSense</div>
                    <div class="sidebar-brand-sub">Inventory Management</div>
                </div>
            </div>
            <div class="user-chip">
                <div class="user-avatar">{initial}</div>
                <div>
                    <div class="user-name">{display_name}</div>
                    <div class="user-role">Logged in</div>
                </div>
            </div>
            """
        )

        page_names = ["Dashboard", "Products", "Receipts", "Delivery Orders", "Internal Transfers",
                      "Stock Adjustments", "Move History", "Settings", "My Profile"]

        if HAS_OPTION_MENU:
            menu = option_menu(
                menu_title=None,
                options=page_names,
                icons=["speedometer2", "box-seam", "box-arrow-in-down", "box-arrow-up-right",
                       "arrow-left-right", "sliders", "clock-history", "gear", "person-circle"],
                default_index=0,
                styles={
                    "container": {"padding": "0", "background-color": "transparent"},
                    "icon": {"color": "#22d3ee", "font-size": "16px"},
                    "nav-link": {
                        "font-size": "14px", "font-weight": "600", "color": "#c3c8e0",
                        "border-radius": "10px", "margin": "3px 0", "padding": "9px 12px",
                    },
                    "nav-link-selected": {
                        "background": "linear-gradient(135deg, #7c5cff, #22d3ee)",
                        "color": "#0d0e17",
                    },
                },
            )
        else:
            menu = st.radio("Navigation", page_names, label_visibility="collapsed")

        st.write("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

    render_html(
        f"""<div style="display:flex;align-items:center;gap:12px;">{LOGO_SVG}
        <span class="app-title">StockSense</span></div>"""
    )
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