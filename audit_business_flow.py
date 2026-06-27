import requests
import sys
import os

BASE_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")


def audit_flow():
    print("--- Iniciando Auditoría Integral de Negocio ---")

    # 1. Registro de Negocio (Tenant)
    print("[1/4] Registrando nuevo negocio...")
    reg_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": "test-admin@empresa.com",
            "password": "securepassword123",
            "business_name": "Negocio de Prueba",
        },
    )

    if reg_response.status_code != 200:
        print(f"  [ERROR] Fallo en registro: {reg_response.text}")
        return

    data = reg_response.json()
    token = data.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Negocio creado. Token obtenido.")

    # 2. Gestión de Empleados
    print("[2/4] Invitando empleado...")
    emp_response = requests.post(
        f"{BASE_URL}/api/execute",
        json={
            "command": "user.invite_employee",
            "params": {
                "username": "empleado@empresa.com",
                "password": "emp1",
                "role": "employee",
            },
        },
        headers=headers,
    )

    if emp_response.json().get("success"):
        print("  [OK] Empleado invitado correctamente.")
    else:
        print(f"  [ERROR] Fallo al invitar empleado: {emp_response.json()}")

    # 3. Auditoría de Salud tras operaciones
    print("[3/4] Verificando salud del sistema...")
    health = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "system.get_health", "params": {}},
        headers=headers,
    )
    print(f"  [OK] Salud: {health.json().get('message')}")

    # 4. Auditoría Final (Listado)
    print("[4/4] Listando usuarios...")
    list_res = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": "user.list", "params": {}},
        headers=headers,
    )
    print(f"  [OK] Usuarios registrados: {len(list_res.json().get('data', []))}")

    print("--- Auditoría de Negocio Finalizada ---")


if __name__ == "__main__":
    audit_flow()
