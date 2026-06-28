from sqlalchemy import create_engine, text

# Configuration
DB_URL = (
    "postgresql://postgres:TFralZyHIJnjyZrNMtoDqqtUlPTsttvT@thomas.proxy.rlwy.net:24031/railway"
)
engine = create_engine(DB_URL)


def clean_db():
    tables_to_clean = [
        "sale_items",
        "sales",
        "stock_movements",
        "products",
        "whatsapp_conversations",
        "whatsapp_menus",
        "cash_box",
        "aliases",
        "credentials",
        "audit_log",
        "frontend_manifest",
        "users",
        "tenants",
    ]

    with engine.connect() as conn:
        # Disable foreign key checks
        conn.execute(text("SET session_replication_role = 'replica';"))

        for table in tables_to_clean:
            try:
                conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                print(f"Truncated table: {table}")
            except Exception as e:
                print(f"Error truncating {table}: {e}")

        # Re-enable foreign key checks
        conn.execute(text("SET session_replication_role = 'origin';"))
        conn.commit()
        print("Database cleaned successfully.")


if __name__ == "__main__":
    try:
        clean_db()
    except Exception as e:
        print(f"Critical error: {e}")
