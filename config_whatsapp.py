import json
import os

import requests

BASE_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")


def main():
    print("--- Configurando Credenciales de WhatsApp ---")

    # 1. Login
    login_data = {"email": "asd", "password": "asd"}
    login_res = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Set Credentials
    meta_creds = {
        "command": "system.set_credential",
        "params": {
            "service": "whatsapp",
            "api_key": "EAAWpnXQ6Y8UBR5oqXE7FMlwstX5CZBH6QFZA6jZAPbVBmM5FGuzGvQDyTjlEZAIMhZBmZBPaZCQzApqIZBnHsLAqtKz3N5XZByFchqTFzMcJAFzkdErRn82M42Xp1myXgxqv84Wl3PfqYdxK2wBnUP2LJn0O9rGK2anAZAW7MWPyKZABnWXZBo8wl2DZAZB14UPbKnCBlNwwQ604ZAe8PdtmL4q1wUhK4PbvgUsFP8sm0GTxa5GmjpZB9ixEwubD2hZCc7aPIem0yMjLrtZCsj2OdAZCCsdoGtP",
            "secret": "not_applicable_use_verify_token",
            "metadata": json.dumps(
                {"phone_number_id": "880275461842101", "waba_id": "2706891212982443"}
            ),
        },
    }
    requests.post(f"{BASE_URL}/api/execute", json=meta_creds, headers=headers)
    print("  [OK] Credenciales guardadas.")

    # 3. Get Webhook URL
    url_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.get_webhook_url", "params": {"service": "whatsapp"}},
        headers=headers,
    )
    data = url_res.json()
    print(f"  [URL] {data['data']['url']}")

    # Also get the secret for the verify token
    requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.get_credential", "params": {"service": "whatsapp"}},
        headers=headers,
    )
    # The secret for the webhook is usually the tenant's secret.
    # Let's derive it or ask the user to use the webhook URL secret part.
    print("--- Configuración Finalizada ---")


if __name__ == "__main__":
    main()
