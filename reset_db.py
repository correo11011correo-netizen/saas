from sqlalchemy import create_engine

from core.database import DB_URL, Base


def reset_all_tables():
    print(f"⚠️ ¡ADVERTENCIA! Estás a punto de ELIMINAR todas las tablas en: {DB_URL}")
    confirm = input("¿Estás seguro? (escribe 'SI'): ")
    if confirm != "SI":
        print("Operación cancelada.")
        return

    # Usamos la conexión configurada
    engine = create_engine(DB_URL)

    print("🧹 Eliminando todas las tablas...")
    Base.metadata.drop_all(engine)
    print("✅ Base de datos limpia.")


if __name__ == "__main__":
    reset_all_tables()
