import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse


class DataCommandHandler:
    """
    Motor de Operaciones Genéricas sobre Datos.
    Provee primitivas atómicas para que los módulos de negocio
    gestionen su estado sin escribir SQL hardcodeado.
    """

    def _sanitize_identifier(self, identifier: str) -> str:
        """Saneamiento estricto para identificadores (llaves JSON, nombres de tabla)."""
        return re.sub(r"[^a-zA-Z0-9_]", "", identifier)

    @command(
        name="data.query",
        description="Retrieves records from an entity using dynamic filters, sorting and pagination.",
        params_model={
            "entity": "string",
            "filters": "dict",
            "limit": "int",
            "offset": "int",
            "sort_by": "string",
            "sort_order": "string",
        },
    )
    def query_data(
        self,
        session: Session,
        context: TenantContext,
        entity: str,
        filters: dict | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str = "ASC",
    ) -> ServiceResponse:
        try:
            # 1. Sanitizar nombre de tabla
            table_name = self._sanitize_identifier(entity.lower().replace(" ", "_"))
            safe_table = f'"{table_name}"'

            # 2. Construir cláusula WHERE dinámica
            where_clauses = []
            params: dict[str, Any] = {"tid": context.tenant_id}

            if filters:
                for i, (key, value) in enumerate(filters.items()):
                    param_name = f"f{i}"
                    safe_key = self._sanitize_identifier(key)
                    # Intentamos primero columna regular, luego JSONB
                    # En PostgreSQL, podemos usar COALESCE o simplemente intentar la columna
                    # Para simplicidad y compatibilidad, usaremos: (columna = :val OR data->>'col' = :val)
                    where_clauses.append(f'("{safe_key}" = :{param_name} OR data->>\'{safe_key}\' = :{param_name})')
                    params[param_name] = value

            where_stmt = "WHERE tenant_id = :tid"
            if where_clauses:
                where_stmt += " AND " + " AND ".join(where_clauses)

            # 3. Ordenamiento
            order_stmt = ""
            if sort_by:
                direction = "DESC" if sort_order.upper() == "DESC" else "ASC"
                safe_sort = self._sanitize_identifier(sort_by)
                order_stmt = f"ORDER BY {safe_sort} {direction}"

            # 4. Query Final
            query = f"SELECT * FROM {safe_table} {where_stmt} {order_stmt} LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            result = session.execute(text(query), params).mappings().all()
            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message=f"Retrieved {len(result)} records."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Query error: {str(e)}", "QUERY_ERROR")

    @command(
        name="data.get_modified_products",
        description="Retrieves products modified since a specific date using stock movements.",
        params_model={"last_sync": "string"},
    )
    def get_modified_products(
        self,
        session: Session,
        context: TenantContext,
        last_sync: str,
    ) -> ServiceResponse:
        try:
            query = """
                SELECT p.code, p.name, p.price, p.quantity, p.category, p.is_weight
                FROM products p
                JOIN stock_movements sm ON p.code = sm.product_code AND p.tenant_id = sm.tenant_id
                WHERE p.tenant_id = :tid AND sm.created_at > :last_sync
            """
            result = session.execute(
                text(query), 
                {"tid": context.tenant_id, "last_sync": last_sync}
            ).mappings().all()
            
            return ServiceResponse.success_res(
                data=[dict(row) for row in result], 
                message=f"Retrieved {len(result)} modified products."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Sync query error: {str(e)}", "SYNC_QUERY_ERROR")

    @command(
        name="data.upsert",
        description="Inserts a record or updates it if a conflict occurs on specified keys.",
        params_model={
            "entity": "string",
            "conflict_keys": "list",
            "data": "dict",
            "update_columns": "list",
        },
    )
    def upsert_data(
        self,
        session: Session,
        context: TenantContext,
        entity: str,
        conflict_keys: list[str],
        data: dict,
        update_columns: list[str],
    ) -> ServiceResponse:
        try:
            table_name = self._sanitize_identifier(entity.lower().replace(" ", "_"))
            safe_table = f'"{table_name}"'

            # Aseguramos que el tenant_id esté presente
            full_data = {**data, "tenant_id": context.tenant_id}
            
            columns = full_data.keys()
            col_names = ", ".join([f'"{c}"' for c in columns])
            col_values = ", ".join([f":{c}" for c in columns])
            
            # Claves de conflicto
            conflict_stmt = ", ".join([f'"{k}"' for k in conflict_keys])
            
            # Columnas a actualizar
            update_stmt = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in update_columns])
            
            query = f"""
                INSERT INTO {safe_table} ({col_names}) 
                VALUES ({col_values}) 
                ON CONFLICT ({conflict_stmt}) 
                DO UPDATE SET {update_stmt}
                RETURNING id
            """
            
            result = session.execute(text(query), full_data).scalar()
            session.commit()
            return ServiceResponse.success_res(data={"id": result}, message="Record upserted successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Upsert error: {str(e)}", "UPSERT_ERROR")

    @command(
        name="data.insert",

        description="Inserts a new record into a specified entity.",
        params_model={
            "entity": "string",
            "data": "dict",
        },
    )
    def insert_data(
        self,
        session: Session,
        context: TenantContext,
        entity: str,
        data: dict,
    ) -> ServiceResponse:
        try:
            table_name = self._sanitize_identifier(entity.lower().replace(" ", "_"))
            safe_table = f'"{table_name}"'
            
            # Extraemos las llaves y valores
            columns = data.keys()
            col_names = ", ".join([f'"{c}"' for c in columns])
            col_values = ", ".join([f":{c}" for c in columns])
            
            # Aseguramos que el tenant_id esté presente
            full_data = {**data, "tenant_id": context.tenant_id}
            
            query = f"INSERT INTO {safe_table} ({col_names}, tenant_id) VALUES ({col_values}, :tenant_id) RETURNING id"
            result = session.execute(text(query), full_data).scalar()
            
            session.commit()
            return ServiceResponse.success_res(data={"id": result}, message="Record inserted successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Insert error: {str(e)}", "INSERT_ERROR")

    @command(
        name="data.patch",
        description="Partially updates a JSON record without overwriting the entire object.",
        params_model={
            "entity": "string",
            "record_id": "string",
            "updates": "dict",
        },
    )
    def patch_data(
        self,
        session: Session,
        context: TenantContext,
        entity: str,
        record_id: str,
        updates: dict,
    ) -> ServiceResponse:
        try:
            table_name = self._sanitize_identifier(entity.lower().replace(" ", "_"))
            safe_table = f'"{table_name}"'

            # Usamos el operador || de PostgreSQL para fusionar JSONB
            session.execute(
                text(f"UPDATE {safe_table} SET data = data || :updates WHERE id = :id AND tenant_id = :tid"),
                {"updates": json.dumps(updates), "id": record_id, "tid": context.tenant_id},
            )

            session.commit()
            return ServiceResponse.success_res(message="Record patched successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Patch error: {str(e)}", "PATCH_ERROR")

    @command(
        name="data.increment",
        description="Atomicsally increments or decrements a numerical field in a JSON record.",
        params_model={
            "entity": "string",
            "record_id": "string",
            "field": "string",
            "value": "float",
        },
    )
    def increment_data(
        self,
        session: Session,
        context: TenantContext,
        entity: str,
        record_id: str,
        field: str,
        value: float,
    ) -> ServiceResponse:
        try:
            table_name = self._sanitize_identifier(entity.lower().replace(" ", "_"))
            safe_table = f'"{table_name}"'
            safe_field = self._sanitize_identifier(field)

            query = f"""
                UPDATE {safe_table} 
                SET data = jsonb_set(
                    data, 
                    '{{{safe_field}}}', 
                    to_jsonb((COALESCE((data->>'{safe_field}')::numeric, 0) + :val)::text)
                ) 
                WHERE id = :id AND tenant_id = :tid
            """

            session.execute(
                text(query),
                {"val": value, "id": record_id, "tid": context.tenant_id},
            )

            session.commit()
            return ServiceResponse.success_res(message=f"Field {field} updated by {value}.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Increment error: {str(e)}", "INCREMENT_ERROR")

    @command(
        name="data.delete",
        description="Deletes a record from a specified entity.",
        params_model={
            "entity": "string",
            "record_id": "string",
        },
    )
    def delete_data(
        self,
        session: Session,
        context: TenantContext,
        entity: str,
        record_id: str,
    ) -> ServiceResponse:
        try:
            table_name = self._sanitize_identifier(entity.lower().replace(" ", "_"))
            safe_table = f'"{table_name}"'

            session.execute(
                text(f"DELETE FROM {safe_table} WHERE id = :id AND tenant_id = :tid"),
                {"id": record_id, "tid": context.tenant_id},
            )

            session.commit()
            return ServiceResponse.success_res(message="Record deleted successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Delete error: {str(e)}", "DELETE_ERROR")


data_commands = DataCommandHandler()
