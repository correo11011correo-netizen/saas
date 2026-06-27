import asyncio
import aiohttp
import uuid

BASE_URL = "https://saas-production-2dd6.up.railway.app"


async def simulate_tenant(tenant_id):
    async with aiohttp.ClientSession() as session:
        # 1. Register
        reg = await session.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": f"test_{tenant_id}@empresa.com",
                "password": "pass",
                "business_name": f"Tienda_{tenant_id}",
            },
        )
        data = await reg.json()
        token = data["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Add Stock (Simulating variety/prices)
        products = [
            {"code": "P1", "name": "Producto A", "price": 10.0, "quantity": 100},
            {"code": "P2", "name": "Producto B", "price": 20.0, "quantity": 50},
        ]
        for p in products:
            await session.post(
                f"{BASE_URL}/api/execute",
                json={"command": "stock.add_product", "params": p},
                headers=headers,
            )

        # 3. Open Cash Box
        await session.post(
            f"{BASE_URL}/api/execute",
            json={"command": "cash.open", "params": {"efectivo_inicial": 0}},
            headers=headers,
        )

        # 4. Sell (Reduce stock)
        await session.post(
            f"{BASE_URL}/api/execute",
            json={
                "command": "sales.cobrar",
                "params": {"cliente": "c1", "items": [{"code": "P1", "quantity": 10}]},
            },
            headers=headers,
        )

        # 5. Close Cash Box
        await session.post(
            f"{BASE_URL}/api/execute",
            json={"command": "cash.close", "params": {}},
            headers=headers,
        )

        return f"Tienda_{tenant_id} completada."


async def main():
    tasks = [simulate_tenant(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    for res in results:
        print(res)


if __name__ == "__main__":
    asyncio.run(main())
