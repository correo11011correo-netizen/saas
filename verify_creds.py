import requests
import json

BASE_URL = "https://saas-production-2dd6.up.railway.app"


def verify():
    # 1. Login
    login_data = {"email": "asd", "password": "asd"}
    login_res = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if login_res.status_code != 200:
        print("Login failed")
        return
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Get Credential
    res = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.get_credential", "params": {"service": "whatsapp"}},
        headers=headers,
    )

    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}")


if __name__ == "__main__":
    verify()
