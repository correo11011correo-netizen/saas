import requests
import json

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def test_user_session():
    print("--- Testeando sesión de adrian ---")

    # 1. Login
    login_res = requests.post(
        f"{BASE_URL}/auth/login", json={"email": "adrian@gmail.com", "password": "1234"}
    )
    if login_res.status_code != 200:
        print(f"Error login: {login_res.status_code} - {login_res.text}")
        return
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Listar credenciales (debería estar vacío inicialmente)
    res = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.list_credentials", "params": {}},
        headers=headers,
    )
    print(f"Cuentas actuales: {res.json()}")

    # 3. Añadir una cuenta de prueba
    add_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "system.set_credential",
            "params": {
                "service": "whatsapp",
                "account_alias": "Prueba Adrian",
                "api_key": "test_key_123",
                "secret": "test_secret_123",
                "metadata": "{}",
            },
        },
        headers=headers,
    )
    print(f"Añadir cuenta: {add_res.json()}")

    # 4. Listar de nuevo
    res_list = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.list_credentials", "params": {}},
        headers=headers,
    )
    print(f"Cuentas tras añadir: {res_list.json()}")


if __name__ == "__main__":
    test_user_session()
