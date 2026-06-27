from sqlalchemy import create_engine, text

# Configuration
DB_URL = "postgresql://postgres:TFralZyHIJnjyZrNMtoDqqtUlPTsttvT@thomas.proxy.rlwy.net:24031/railway"
engine = create_engine(DB_URL)


def add_constraint():
    with engine.connect() as conn:
        conn.execute(
            text(
                """
            ALTER TABLE bot_nodes
            ADD CONSTRAINT unique_node_per_tenant UNIQUE (tenant_id, name);
        """
            )
        )
        conn.commit()
        print("Constraint added successfully.")


if __name__ == "__main__":
    try:
        add_constraint()
    except Exception as e:
        print(f"Error: {e}")
