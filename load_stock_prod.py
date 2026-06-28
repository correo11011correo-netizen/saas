import os

import requests

BASE_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")


def main():
    print("--- Iniciando Proceso de Carga de Stock en Producción ---")

    # 1. Login
    print("[1/2] Autenticando usuario asd / asd...")
    login_data = {"email": "asd", "password": "asd"}

    try:
        login_res = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        login_res.raise_for_status()
        token = login_res.json().get("token")
        print("  [OK] Autenticación exitosa. Token obtenido.")
    except Exception as e:
        print(f"  [ERROR] Fallo al autenticar: {e}")
        return

    # 2. Cargar Stock
    print("[2/2] Cargando producto de prueba en el stock...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Usamos el comando stock.add identificado en stock/commands.py
    stock_data = {
        "command": "stock.add",
        "params": {
            "code": "PROD-001",
            "name": "Producto de Prueba Gemini",
            "price": 10.50,
            "quantity": 100,
            "category": "General",
            "is_weight": False,
        },
    }

    try:
        stock_res = requests.post(f"{BASE_URL}/api/execute", json=stock_data, headers=headers)
        stock_res.raise_for_status()
        print(f"  [OK] Respuesta del servidor: {stock_res.json()}")
    except Exception as e:
        print(f"  [ERROR] Fallo al cargar stock: {e}")
        if "stock_res" in locals():
            print(f"  Detalle: {stock_res.text}")

    print("--- Proceso Finalizado ---")


if __name__ == "__main__":
    main()
