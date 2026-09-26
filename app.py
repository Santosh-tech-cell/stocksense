import sqlite3
import streamlit as st

# --- Page Setup ---
st.set_page_config(page_title="StockSense IMS", layout="wide")
st.title("📦 StockSense - Inventory Management System")


# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    # Create Products Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            category TEXT,
            quantity INTEGER DEFAULT 0
        )
    """
    )

    conn.commit()
    conn.close()


# Run database setup
init_db()

# --- Sidebar Navigation ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Products", "Operations"])

if menu == "Dashboard":
    st.subheader("📊 Inventory Dashboard")
    st.write("Welcome to StockSense! Real-time inventory tracking.")

elif menu == "Products":
    st.subheader("📦 Product Management")
    st.write("Product listing and creation will appear here.")

elif menu == "Operations":
    st.subheader("🔄 Stock Operations")
    st.write("Receipts and deliveries will be handled here.")