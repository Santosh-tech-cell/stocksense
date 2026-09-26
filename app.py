import sqlite3
import streamlit as st
import pandas as pd

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

    # Form to add a new product
    with st.form("add_product_form", clear_on_submit=True):
        st.write("### Add New Product")
        name = st.text_input("Product Name*")
        sku = st.text_input("SKU / Code*")
        category = st.selectbox(
            "Category", ["Raw Materials", "Finished Goods", "Office Supplies"]
        )
        quantity = st.number_input(
            "Initial Stock", min_value=0, step=1, value=0
        )

        submitted = st.form_submit_button("Save Product")

        if submitted:
            if name.strip() and sku.strip():
                try:
                    conn = sqlite3.connect("inventory.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO products (name, sku, category, quantity)
                        VALUES (?, ?, ?, ?)
                    """,
                        (name, sku, category, quantity),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Product '{name}' added successfully!")
                except sqlite3.IntegrityError:
                    st.error(
                        "Error: A product with this SKU already exists. SKUs must be unique."
                    )
            else:
                st.warning("Please fill in both Name and SKU.")
         # 2. Table to display all products
    st.write("---")
    st.write("### Current Inventory")

    conn = sqlite3.connect("inventory.db")
    df = pd.read_sql_query(
        "SELECT id, name, sku, category, quantity FROM products", conn
    )
    conn.close()

    if not df.empty:
        # Sidebar Filters 🎛️
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filter Products")
        search_query = st.sidebar.text_input("Search by Name or SKU")

        categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
        selected_category = st.sidebar.selectbox("Filter by Category", categories)

        # Apply Category Filter
        if selected_category != "All":
            df = df[df["category"] == selected_category]

        # Apply Search Filter
        if search_query.strip():
            df = df[
                df["name"].str.contains(search_query, case=False, na=False)
                | df["sku"].str.contains(search_query, case=False, na=False)
            ]

        # Add Low Stock Status indicator column ⚠️
        df["Status"] = df["quantity"].apply(
            lambda q: "⚠️ Low Stock" if q < 5 else "✅ In Stock"
        )

        st.dataframe(df, use_container_width=True)
    else:
        st.info("No products registered yet.")
    
     # 🛠️ Edit / Delete Product Section
        with st.expander("🛠️ Manage / Edit / Delete a Product"):
            product_options = {
                f"{row['name']} ({row['sku']})": row for _, row in df.iterrows()
            }
            selected_label = st.selectbox(
                "Select a product to modify:", list(product_options.keys())
            )

            if selected_label:
                selected_item = product_options[selected_label]

                col1, col2 = st.columns(2)
                with col1:
                    edit_name = st.text_input("Name", value=selected_item["name"])
                    edit_category = st.selectbox(
                        "Category",
                        ["Raw Materials", "Finished Goods", "Office Supplies"],
                        index=["Raw Materials", "Finished Goods", "Office Supplies"].index(
                            selected_item["category"]
                        )
                        if selected_item["category"] in ["Raw Materials", "Finished Goods", "Office Supplies"]
                        else 0,
                    )
                with col2:
                    edit_quantity = st.number_input(
                        "Quantity",
                        min_value=0,
                        step=1,
                        value=int(selected_item["quantity"]),
                    )

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("💾 Update Product"):
                        conn = sqlite3.connect("inventory.db")
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            UPDATE products
                            SET name = ?, category = ?, quantity = ?
                            WHERE id = ?
                        """,
                            (
                                edit_name,
                                edit_category,
                                edit_quantity,
                                int(selected_item["id"]),
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Product updated!")
                        st.rerun()

                with btn_col2:
                    if st.button("🗑️ Delete Product"):
                        conn = sqlite3.connect("inventory.db")
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM products WHERE id = ?",
                            (int(selected_item["id"]),),
                        )
                        conn.commit()
                        conn.close()
                        st.warning("Product deleted!")
                        st.rerun()

elif menu == "Operations":
    st.subheader("🔄 Stock Operations")
    st.write("Receipts and deliveries will be handled here.")