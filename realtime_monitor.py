import asyncio
import aiohttp
import time
import random

BASE_URL = "https://saas-production-2dd6.up.railway.app"


async def monitor_tenant_flow(tenant_id):
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # 1. Registro
                reg = await session.post(
                    f"{BASE_URL}/auth/register",
                    json={
                        "email": f"m_{tenant_id}_{time.time()}@test.com",
                        "password": "p",
                        "business_name": f"T_{tenant_id}",
                    },
                )
                data = await reg.json()
                token = data["token"]
                h = {"Authorization": f"Bearer {token}"}

                # 2. Agregar empleado
                await session.post(
                    f"{BASE_URL}/api/execute",
                    json={
                        "command": "user.invite_employee",
                        "params": {
                            "username": f"e_{time.time()}@t.com",
                            "password": "p",
                            "role": "employee",
                        },
                    },
                    headers=h,
                )

                # 3. Stock y Venta
                await session.post(
                    f"{BASE_URL}/api/execute",
                    json={
                        "command": "stock.add",
                        "params": {
                            "code": "P1",
                            "name": "Prod",
                            "price": 10.0,
                            "quantity": 100,
                        },
                    },
                    headers=h,
                )

                await session.post(
                    f"{BASE_URL}/api/execute",
                    json={
                        "command": "venta.cobrar",
                        "params": {
                            "cliente": "c1",
                            "items": [{"product_code": "P1", "quantity": 1}],
                            "metodo_pago": "Efectivo",
                            "paga_con": 10.0,
                        },
                    },
                    headers=h,
                )

                print(f"Tienda {tenant_id} ciclo completado.")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Error en {tenant_id}: {e}")
                await asyncio.sleep(10)


async def main():
    print("--- Iniciando Monitoreo de Tiempo Real ---")
    await asyncio.gather(*(monitor_tenant_flow(i) for i in range(3)))


if __name__ == "__main__":
    asyncio.run(main())
