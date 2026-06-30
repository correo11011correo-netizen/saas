import logging

from sqlalchemy.orm import Session

from stock.models import Product, ProductVariant

logger = logging.getLogger("OmniStockMigrator")


class OmniStockMigrator:
    """
    Migrador de Stock Simple a OmniStock (Variantes).
    Convierte la tabla 'products' antigua en una estructura de
    Product (Padre) -> ProductVariant (Hijo) sin pérdida de datos.
    """

    def __init__(self, session: Session):
        self.session = session

    def migrate_existing_data(self):
        """
        Ejecuta la migración de datos.
        Este script debe correrse una sola vez después de actualizar los modelos.
        """
        logger.info("Starting migration to OmniStock Universal...")

        try:
            # Obtenemos los datos de la tabla 'products' actual utilizando SQL puro
            # para evitar conflictos con el nuevo modelo de SQLAlchemy durante la migración.
            from sqlalchemy import text

            result = self.session.execute(
                text(
                    "SELECT id, tenant_id, name, code, price, quantity, category, is_weight FROM products"
                )
            )

            rows = result.all()
            processed_count = 0

            for row in rows:
                # row = (id, tenant_id, name, code, price, quantity, category, is_weight)

                # A. Crear el Producto Padre
                new_product = Product(id=row[0], tenant_id=row[1], name=row[2], category=row[6])
                self.session.add(new_product)

                # Determinar el tipo de producto basado en is_weight
                from stock.models import ProductType

                new_product.product_type = ProductType.WEIGHTED if row[7] else ProductType.PHYSICAL

                self.session.flush()

                # B. Crear la Variante Única (mantiene el stock y precio originales)
                variant = ProductVariant(
                    product_id=new_product.id,
                    tenant_id=row[1],
                    code=row[3],
                    name=f"Standard {row[2]}",
                    price=row[4],
                    quantity=row[5],
                )
                self.session.add(variant)

                processed_count += 1

            self.session.commit()
            logger.info(f"Successfully migrated {processed_count} products to OmniStock.")
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"Migration failed: {str(e)}")
            return False
