import requests
import json

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def verify_full_flow():
    print("--- Verificando Flujo de WhatsApp ---")

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

    # 2. Verificar Credenciales y obtener Alias
    creds = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.list_credentials", "params": {}},
        headers=headers,
    ).json()
    whatsapp_creds = [c for c in creds["data"] if c["service_name"] == "whatsapp"]

    if not whatsapp_creds:
        print("No hay cuentas de WhatsApp configuradas.")
        return

    alias = whatsapp_creds[0]["account_alias"]
    print(f"Cuenta encontrada: {alias}")

    # 3. Prueba de envío real (a un número de prueba si es posible, o al menos validar que la petición no da error crítico)
    # IMPORTANTE: En Meta, para enviar a números no registrados, debes usar el número del sandbox o verificar el tuyo.
    # Usaré un número dummy para validar que el sistema intenta procesar el alias correctamente.
    send_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "whatsapp.send_text",
            "params": {
                "to": "5491100000000",
                "body": "Test de sistema desde BotEngine",
                "account_alias": alias,
            },
        },
        headers=headers,
    )

    print(f"Resultado envío: {send_res.json()}")

    # 4. Verificar listado de conversaciones
    conv_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "whatsapp.list_conversations", "params": {}},
        headers=headers,
    )
    print(f"Conversaciones registradas: {conv_res.json()}")


if __name__ == "__main__":
    verify_full_flow()
