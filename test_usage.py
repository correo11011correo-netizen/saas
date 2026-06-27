import requests
import json

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def test_usage():
    print("--- Probando credenciales configuradas de adrian ---")

    # 1. Login
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "delpianoadrian@gmail.com", "password": "1234"},
    )
    if login_res.status_code != 200:
        print(f"Error login: {login_res.status_code} - {login_res.text}")
        return
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Listar credenciales existentes
    res = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.list_credentials", "params": {}},
        headers=headers,
    )
    creds = res.json()
    print(f"Cuentas configuradas: {creds}")

    if not creds.get("success") or not creds.get("data"):
        print("No se encontraron credenciales para testear.")
        return

    # 3. Testear uso de la primera cuenta encontrada
    account = creds["data"][0]
    print(f"Probando cuenta: {account['account_alias']} ({account['service_name']})")

    # Intentamos obtener credenciales específicas
    res_get = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "system.get_credential",
            "params": {
                "service": account["service_name"],
                "account_alias": account["account_alias"],
            },
        },
        headers=headers,
    )
    print(f"Resultado obtención: {res_get.json()}")


if __name__ == "__main__":
    test_usage()
