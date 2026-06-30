# 🛠️ Guía Técnica para el Desarrollador de la APK (OmniCore Native)

Bienvenido al desarrollo de la APK de OmniCore. Esta aplicación no es una vista web, sino un **Renderizador Nativo de Componentes** dirigido por el servidor (Server-Driven UI).

## 🚀 1. El Ciclo de Vida de la App

### A. Inicio y Autenticación
1. El usuario hace Login $ightarrow$ Recibe un `access_token`.
2. La APK llama inmediatamente a `GET /api/boot` enviando el token.
3. El servidor devuelve el **Manifiesto de Arranque** (JSON).

### B. El Manifiesto de Arranque (`/api/boot`)
Este JSON es la "Biblia" de la app. Debes leerlo para construir la interfaz:
- **`theme`**: Aplica los colores primarios y secundarios a todo el app.
- **`layout`**: Contiene la estructura de la Home. Es una lista de componentes.
  - *Ejemplo:* `[{ "id": "BtnPrimary", "props": { "label": "Cobrar", "action": "sales.create" } }]`.
- **`permissions`**: Lista de comandos que el usuario puede ejecutar. Si un comando no está aquí, el botón debe estar deshabilitado.

## 📦 2. Gestión de Datos y Offline-First

### A. Sincronización de Stock (Edge Cache)
Para que el escaneo sea instantáneo y funcione sin internet:
1. **Sincronización Inicial**: Descarga la lista completa de productos al iniciar.
2. **Sync Incremental**: Llama a `/api/stock/sync?last_sync=TIMESTAMP`. Actualiza solo los productos que cambiaron.
3. **Búsqueda Local**: El escáner debe buscar primero en la base de datos local (SQLite/Room) antes de intentar llamar al servidor.

### B. Cola de Ventas Offline
Cuando el usuario realiza una venta y **no hay conexión**:
1. Genera un `client_request_id` (UUID v4).
2. Guarda la venta en una cola local (SQLite).
3. Intenta enviar la venta al servidor.
4. Si falla $ightarrow$ Mantén la venta en la cola y marca como "Pendiente".
5. Al detectar internet $ightarrow$ Envía todas las ventas pendientes en orden cronológico. El servidor usará el `client_request_id` para evitar duplicados.

## 📷 3. Implementación del Escáner
- Usa la cámara para leer códigos de barras/QR.
- Al leer un código $ightarrow$ Busca en el stock local $ightarrow$ Agrega al carrito.
- Si el producto no existe localmente $ightarrow$ Llama al servidor para verificar si es un producto nuevo.

## 🛠️ 4. Reglas de Oro del Desarrollador
1. **No hardcodees vistas**: Si quieres cambiar un botón de lugar, pídelo al backend o cámbialo en `ui_layouts`.
2. **Componentes Atómicos**: Crea una librería de componentes nativos (Button, Input, Card, List) que acepten propiedades dinámicas.
3. **Sincronización en Segundo Plano**: El proceso de vaciado de la cola de ventas debe ocurrir en un `WorkManager` o servicio de fondo para no bloquear al usuario.
