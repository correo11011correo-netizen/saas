import requests
import json

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def setup():
    print("--- Configurando Entorno para Adrian ---")

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

    # 2. Cargar Stock (Gaseosas)
    products = [
        {
            "code": "GAS-001",
            "name": "Coca Cola 2L",
            "price": 2500,
            "quantity": 50,
            "category": "Gaseosas",
        },
        {
            "code": "GAS-002",
            "name": "Pepsi 2L",
            "price": 2400,
            "quantity": 40,
            "category": "Gaseosas",
        },
        {
            "code": "GAS-003",
            "name": "Sprite 2L",
            "price": 2450,
            "quantity": 30,
            "category": "Gaseosas",
        },
    ]
    for p in products:
        requests.post(
            f"{BASE_URL}/api/execute",
            json={"command": "stock.add", "params": p},
            headers=headers,
        )
    print("  [OK] Stock cargado.")

    # 3. Crear Nodos del Bot (Relacional)
    # Nodo Inicio
    requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "bot.node.save",
            "params": {
                "name": "inicio",
                "prompt": "¡Hola! Bienvenido a Gaseosas S.A.\n\n¿Qué deseas hacer?\n1. Ver Productos\n2. Contacto",
            },
        },
        headers=headers,
    )

    # Nodo Productos
    requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "bot.node.save",
            "params": {
                "name": "productos",
                "prompt": "Aquí tienes nuestros productos disponibles:\n(Consulta nuestro stock actualizado en la app)",
            },
        },
        headers=headers,
    )

    # 4. Vincular Nodos (Añadir Opción)
    nodes = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "bot.node.list", "params": {}},
        headers=headers,
    ).json()["data"]
    start_node = next(n for n in nodes if n["name"] == "inicio")
    prod_node = next(n for n in nodes if n["name"] == "productos")

    requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "bot.option.add",
            "params": {
                "node_id": start_node["id"],
                "label": "1",
                "next_node_id": prod_node["id"],
            },
        },
        headers=headers,
    )

    print("  [OK] Flujo del bot configurado (Inicio -> Productos).")
    print("--- ¡Configuración lista! Ya puedes probar el bot por WhatsApp ---")


if __name__ == "__main__":
    setup()
