import requests
import json

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def setup_mp():
    print("--- Configurando Mercado Pago ---")

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

    # 2. Set MP Credentials
    mp_creds = {
        "command": "system.set_credential",
        "params": {
            "service": "mercadopago",
            "account_alias": "Principal",
            "api_key": "APP_USR-2514995626304784-122221-6a3c84e075d64479c1dba9c802ed2801-174114989",
            "secret": "kHZvonblcXSmi9pAe8K5j0asAXY8CH4L",
            "metadata": json.dumps(
                {
                    "public_key": "APP_USR-b5fa17a6-cc25-4f2d-8b96-07ee8758768a",
                    "client_id": "2514995626304784",
                }
            ),
        },
    }
    res = requests.post(f"{BASE_URL}/api/execute", json=mp_creds, headers=headers)
    print(f"Respuesta: {res.json()}")
    print("--- Mercado Pago configurado ---")


if __name__ == "__main__":
    setup_mp()
