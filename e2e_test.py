import requests
import json

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def run_e2e_test():
    print("--- Iniciando Test End-to-End ---")

    # 1. Login
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "delpianoadrian@gmail.com", "password": "1234"},
    )
    if login_res.status_code != 200:
        print(f"Error login: {login_res.text}")
        return
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Cargar Stock
    requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "stock.add",
            "params": {
                "code": "GAS-001",
                "name": "Coca Cola 2L",
                "price": 2500,
                "quantity": 50,
                "category": "Gaseosas",
            },
        },
        headers=headers,
    )
    print("  [OK] Producto cargado.")

    # 3. Crear Flujo de Bot
    flow_data = {
        "menu": "main",
        "options": [
            {"label": "Comprar Coca Cola", "action": "buy", "product": "GAS-001"}
        ],
    }
    requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "bot.flow.save",
            "params": {"name": "main", "flow_data": json.dumps(flow_data)},
        },
        headers=headers,
    )
    print("  [OK] Flujo de bot creado.")

    # 4. Simular Venta (a través del flujo de bot)
    # En un caso real, esto sería disparado por un Webhook de WhatsApp
    print("--- Iniciando Venta simulada ---")

    # El bot detecta interés y crea la orden
    sale_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "sales.create",
            "params": {
                "items": [{"code": "GAS-001", "price": 2500}],
                "total": 2500,
                "account_alias": "Principal",
            },
        },
        headers=headers,
    )

    print(f"Respuesta venta: {sale_res.json()}")


if __name__ == "__main__":
    run_e2e_test()
