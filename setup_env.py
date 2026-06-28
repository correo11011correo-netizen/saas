import json

import requests

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def setup():
    print("--- Configurando Entorno desde Cero ---")

    # 1. Register User
    reg_data = {
        "email": "nuevo@ejemplo.com",
        "password": "password123",
        "business_name": "Gaseosas S.A.",
    }
    requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    print("  [OK] Usuario registrado.")

    # 2. Login
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "nuevo@ejemplo.com", "password": "password123"},
    )
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 3. Load Stock
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

    # 4. Set WhatsApp Creds
    creds = {
        "command": "system.set_credential",
        "params": {
            "service": "whatsapp",
            "api_key": "EAAWpnXQ6Y8UBR5oqXE7FMlwstX5CZBH6QFZA6jZAPbVBmM5FGuzGvQDyTjlEZAIMhZBmZBPaZCQzApqIZBnHsLAqtKz3N5XZByFchqTFzMcJAFzkdErRn82M42Xp1myXgxqv84Wl3PfqYdxK2wBnUP2LJn0O9rGK2anAZAW7MWPyKZABnWXZBo8wl2DZAZB14UPbKnCBlNwwQ604ZAe8PdtmL4q1wUhK4PbvgUsFP8sm0GTxa5GmjpZB9ixEwubD2hZCc7aPIem0yMjLrtZCsj2OdAZCCsdoGtP",
            "secret": "verify_token_123",
            "metadata": json.dumps({"phone_number_id": "880275461842101"}),
        },
    }
    requests.post(f"{BASE_URL}/api/execute", json=creds, headers=headers)
    print("  [OK] Credenciales WhatsApp cargadas.")
    print("--- Configuración completada ---")


if __name__ == "__main__":
    setup()
