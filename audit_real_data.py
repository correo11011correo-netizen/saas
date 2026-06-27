import requests
import json
import uuid
import os

BASE_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")


def audit_real_data():
    print("--- Auditoría de Datos Reales ---")

    # 1. Registrar Negocio
    unique_id = uuid.uuid4().hex[:8]
    reg = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": f"audit_{unique_id}@test.com",
            "password": "pass",
            "business_name": f"AuditStore_{unique_id}",
        },
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Agregar Stock
    requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "stock.add",
            "params": {
                "code": "P1",
                "name": "ProductoTest",
                "price": 10.0,
                "quantity": 100,
            },
        },
        headers=headers,
    )

    # Verificación Inicial
    stock_init = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "stock.get", "params": {"code": "P1"}},
        headers=headers,
    ).json()["data"]
    print(f"Stock Inicial (P1): {stock_init['quantity']}")

    # 3. Abrir Caja
    requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "cash.open", "params": {"monto_inicial": 0}},
        headers=headers,
    )

    # 4. Realizar Venta (10 unidades)
    venta = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "venta.cobrar",
            "params": {
                "cliente": "c1",
                "items": [{"product_code": "P1", "quantity": 10}],
                "metodo_pago": "Efectivo",
                "paga_con": 100.0,
            },
        },
        headers=headers,
    ).json()
    print(f"Venta: {venta['data']['total']} procesada (ID: {venta['data']['sale_id']})")

    # 5. Verificación Final (Stock y Caja)
    stock_final = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "stock.get", "params": {"code": "P1"}},
        headers=headers,
    ).json()["data"]
    print(f"Stock Final (P1): {stock_final['quantity']}")

    reporte = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "cash.report", "params": {}},
        headers=headers,
    ).json()["data"]
    print(
        f"Caja - Ventas Efectivo: {reporte['ventas_efectivo']}, Total en Caja: {reporte['total_en_caja']}"
    )

    requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "cash.close", "params": {}},
        headers=headers,
    )
    print("--- Auditoría Finalizada ---")


if __name__ == "__main__":
    audit_real_data()
