import os

import requests

BASE_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")


def activate_bot():
    print("--- Activando Bot de WhatsApp ---")

    # 1. Login
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "delpianoadrian@gmail.com", "password": "1234"},
    )
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Crear Nodo 'inicio'
    node_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "bot.node.save",
            "params": {
                "name": "inicio",
                "prompt": "¡Hola! Bienvenido a Gaseosas S.A. Responde con '1' para ver productos.",
            },
        },
        headers=headers,
    )
    print(f"Nodo inicio: {node_res.json()}")

    # 3. Necesitamos el ID del nodo 'inicio' para añadir la opción
    # Para simplificar, voy a listar los nodos y encontrar el ID
    list_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "bot.node.list", "params": {}},
        headers=headers,
    )
    nodes = list_res.json()["data"]
    start_node = next(n for n in nodes if n["name"] == "inicio")

    # 4. Añadir Opción
    opt_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "bot.option.add",
            "params": {
                "node_id": start_node["id"],
                "label": "1",
                "action": "products.list",
            },
        },
        headers=headers,
    )
    print(f"Opción añadida: {opt_res.json()}")
    print("--- Bot Activado. ¡Ya puedes hablarle por WhatsApp! ---")


if __name__ == "__main__":
    activate_bot()
