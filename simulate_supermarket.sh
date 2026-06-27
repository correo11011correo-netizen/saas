#!/bin/bash

# Config
API_URL="http://localhost:8000"
EMAIL="supermercado_final_v5@test.com"
PASSWORD="password123"
BUSINESS="Supermercado Central"

echo "🚀 Iniciando Simulación de Supermercado..."

# 1. Registro
echo "📝 Registrando negocio..."
REG_DATA=$(printf '{"email": "%s", "password": "%s", "business_name": "%s"}' "$EMAIL" "$PASSWORD" "$BUSINESS")
REG_RES=$(curl -s -X POST "$API_URL/auth/register" -H "Content-Type: application/json" -d "$REG_DATA")

TOKEN=$(echo $REG_RES | grep -oP '(?<="token":")[^"]*')
TID=$(echo $REG_RES | grep -oP '(?<="tenant_id":")[^"]*')

if [ -z "$TOKEN" ]; then echo "❌ Error en registro: $REG_RES"; exit 1; fi
echo "✅ Registrado. Token: ${TOKEN:0:20}... TenantID: $TID"

# 2. Carga de Stock (Catálogo)
echo "📦 Cargando inventario..."
PRODUCTS=(
    '{"code": "LECHE01", "name": "Leche Entera 1L", "price": 1.20, "quantity": 100, "category": "Lácteos", "is_weight": false}'
    '{"code": "PAN01", "name": "Pan Integral", "price": 0.80, "quantity": 50, "category": "Panadería", "is_weight": false}'
    '{"code": "MANZ01", "name": "Manzanas Rojas (kg)", "price": 2.50, "quantity": 200, "category": "Frutas", "is_weight": true}'
    '{"code": "CARN01", "name": "Pollo Entero (kg)", "price": 5.00, "quantity": 40, "category": "Carnicería", "is_weight": true}'
    '{"code": "SODA01", "name": "Coca Cola 2L", "price": 2.10, "quantity": 80, "category": "Bebidas", "is_weight": false}'
)

for p in "${PRODUCTS[@]}"; do
    PAYLOAD=$(printf '{"command": "stock.add", "params": %s}' "$p")
    curl -s -X POST "$API_URL/api/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD" > /dev/null
done
echo "✅ Inventario cargado."

# 3. Gestión de Empleados
echo "👥 Creando personal..."
EMPLOYEES=("cajero1@test.com" "cajero2@test.com")
for emp in "${EMPLOYEES[@]}"; do
    PAYLOAD=$(printf '{"command": "user.invite_employee", "params": {"username": "%s", "password": "emp123", "role": "employee"}}' "$emp")
    curl -s -X POST "$API_URL/api/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD" > /dev/null
done
echo "✅ Personal creado."

# 4. Configuración de Alias para Transferencias
echo "💳 Configurando Alias de Pago..."
curl -s -X POST "$API_URL/api/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"
-d '{"command": "sales.create_alias", "params": {"nombre": "AliasSúper", "limite": 1000.0}}' > /dev/null
echo "✅ Alias 'AliasSúper' registrado."

# 5. Flujo Operativo Diario
echo "⏰ Iniciando Jornada..."
curl -s -X POST "$API_URL/api/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"command": "cash.open", "params": {"monto_inicial": 100.0}}'
echo -e "
✅ Caja abierta con \$100.00"

# Ventas simuladas
echo "🛒 Procesando Ventas..."
SALES=(
    '{"cliente": "Juan", "items": [{"product_code": "LECHE01", "quantity": 2}, {"product_code": "PAN01", "quantity": 1}], "metodo_pago": "Efectivo", "paga_con": 10.0}'
    '{"cliente": "Maria", "items": [{"product_code": "MANZ01", "quantity": 3}], "metodo_pago": "Transferencia", "alias": "AliasSúper"}'
    '{"cliente": "Pedro", "items": [{"product_code": "SODA01", "quantity": 1}, {"product_code": "CARN01", "quantity": 2}], "metodo_pago": "Efectivo", "paga_con": 20.0}'
)

for s in "${SALES[@]}"; do
    PAYLOAD=$(printf '{"command": "venta.cobrar", "params": %s}' "$s")
    curl -s -X POST "$API_URL/api/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD"
    echo ""
done
echo "✅ Ventas procesadas."

# 6. Cierre y Reporte
echo "📊 Generando Reporte Final..."
curl -s -X POST "$API_URL/api/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"command": "cash.report", "params": {}}'
echo -e "
✅ Reporte generado."

echo "🔒 Cerrando Caja..."
curl -s -X POST "$API_URL/api/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"command": "cash.close", "params": {}}'
echo -e "
✅ Caja cerrada. Simulación finalizada."
