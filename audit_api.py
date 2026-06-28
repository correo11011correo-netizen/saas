import os

import requests

BASE_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")


def audit():
    print("--- Iniciando Auditoría de OmniCore API ---")

    # 1. Auditoría de Salud
    try:
        # Probamos un endpoint público si existe, o el health check via execute
        print("[1/2] Verificando salud del sistema...")
        response = requests.post(
            f"{BASE_URL}/api/execute",
            json={"command": "system.get_health", "params": {}},
            headers={"Authorization": "Bearer mock-token"},
        )

        if response.status_code == 401:
            print("  [OK] Endpoint protegido correctamente (401 detectado)")
        else:
            print(f"  [ALERTA] Respuesta inesperada en health check: {response.status_code}")
    except Exception as e:
        print(f"  [ERROR] Fallo de conexión: {e}")

    # 2. Auditoría de Webhooks
    print("[2/2] Verificando estructura de Webhooks...")
    response = requests.get(f"{BASE_URL}/hooks/test-secret/whatsapp")
    if response.status_code == 404:
        print("  [OK] Endpoint de webhooks activo (404 esperado sin tenant configurado)")
    else:
        print(f"  [ALERTA] Estado de webhooks: {response.status_code}")

    print("--- Auditoría Finalizada ---")


if __name__ == "__main__":
    audit()
