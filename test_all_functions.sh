#!/bin/bash
# Script de auditoría para probar todas las funciones de la UI mediante CURL

echo "--- Iniciando Test de Integración Frontend-Backend (CURL) ---"

# 1. Registrar Negocio
echo "[1/7] Registrando Negocio..."
REG_RESP=$(curl -s -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test_curl@test.com","password":"pass","business_name":"TestStore"}')
TOKEN=$(echo $REG_RESP | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
echo "  [OK] Token obtenido: $TOKEN"

# 2. Agregar Stock
echo "[2/7] Agregando Stock..."
curl -s -X POST http://localhost:8000/api/execute \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"command":"stock.add","params":{"code":"P1","name":"ProdCurl","price":10.0,"quantity":100}}' | jq .

# 3. Invitar Empleado
echo "[3/7] Invitando Empleado..."
curl -s -X POST http://localhost:8000/api/execute \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"command":"user.invite_employee","params":{"username":"emp_curl@test.com","password":"p","role":"employee"}}' | jq .

# 4. Abrir Caja
echo "[4/7] Abriendo Caja..."
curl -s -X POST http://localhost:8000/api/execute \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"command":"cash.open","params":{"efectivo_inicial":0}}' | jq .

# 5. Realizar Venta
echo "[5/7] Realizando Venta..."
curl -s -X POST http://localhost:8000/api/execute \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"command":"venta.cobrar","params":{"cliente":"c1","items":[{"product_code":"P1","quantity":5}],"metodo_pago":"Efectivo","paga_con":100}}' | jq .

# 6. Listar Usuarios
echo "[6/7] Listando Usuarios..."
curl -s -X POST http://localhost:8000/api/execute \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"command":"user.list","params":{}}' | jq .

# 7. Cerrar Caja
echo "[7/7] Cerrando Caja..."
curl -s -X POST http://localhost:8000/api/execute \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"command":"cash.close","params":{}}' | jq .

echo "--- Auditoría Finalizada ---"
