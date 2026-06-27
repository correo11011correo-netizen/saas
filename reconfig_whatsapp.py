import requests
import json
import os

BASE_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")


def main():
    print("--- Re-configurando Credenciales de WhatsApp ---")

    # 1. Login
    login_data = {"email": "asd", "password": "asd"}
    login_res = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if login_res.status_code != 200:
        print("Login failed")
        return
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
    res = requests.post(f"{BASE_URL}/api/execute", json=meta_creds, headers=headers)
    print(f"Respuesta set_credential: {res.json()}")

    # 3. Verify
    res_get = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.get_credential", "params": {"service": "whatsapp"}},
        headers=headers,
    )
    print(f"Respuesta get_credential: {res_get.json()}")


if __name__ == "__main__":
    main()
