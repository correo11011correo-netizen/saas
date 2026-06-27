# 🗺️ FRONTEND_MAP - OmniCore Industrial Standard

## 📌 Propósito
Este archivo es el índice maestro para cualquier agente de IA que mantenga este proyecto. Define la arquitectura, las responsabilidades de cada archivo y los flujos de datos.

## 🏗️ Arquitectura de Archivos

### 📁 Raíz (`/frontend`)
- `index.html`: Punto de entrada único. Contenedor dinámico donde se montan los motores (Raíz y App).
- `FRONTEND_MAP.md`: Este archivo.

### 📁 Estilos (`/frontend/css`)
- `global.css`: Design System. Contiene variables CSS (`:root`), reseteo de estilos y layouts base (Mobile-First). **Cualquier cambio visual debe nacer aquí.**

### 📁 Core Logic (`/frontend/js/core`)
- `api.js`: **Único punto de contacto con el backend.** Maneja el token Bearer, el endpoint `/api/execute` y la normalización de respuestas.
- `session.js`: Gestión de ciclo de vida del token (localStorage), login, registro y guardias de acceso.
- `ui.js`: Biblioteca de componentes globales (Toasts, Spinners, Dock de navegación).
- `app.js`: Orquestador del Motor App. Gestiona la carga dinámica de módulos y el estado del Hub.

### 📁 Root Engine (`/frontend/js/root`)
- `welcome.js`: Lógica de la pantalla de aterrizaje y branding.
- `plans.js`: Gestión de vistas de planes y suscripciones.

### 📁 Business Modules (`/frontend/js/modules`)
- `profile.js`: Gestión de perfil de negocio, datos del tenant y administración de empleados (Usa: `core.get_profile`, `user.list`, `user.invite_employee`).
- `stock.js`: Catálogo de productos y control de inventario (Usa: `products.list`).
- `sales.js`: Punto de Venta (POS). Gestión de caja y cobros (Usa: `venta.cobrar`, `cash.open`, `cash.close`, `cash.report`).
- `whatsapp.js`: Gestión de mensajería y bots (Usa: `whatsapp.send_text`).
- `mercadopago.js`: Configuración y monitoreo de pagos automáticos.

## 🔄 Flujo de Datos Principal
`Acción Usuario` $ightarrow$ `Módulo/Core` $ightarrow$ `api.js` $ightarrow$ `Backend /api/execute` $ightarrow$ `Respuesta JSON` $ightarrow$ `api.js` $ightarrow$ `UI Component (Toast/Render)`.

## 🎨 Guía de Estilo Rápida
- **Mobile First**: Todo se diseña para 390px - 430px de ancho.
- **Coherencia**: No usar estilos inline. Usar clases definidas en `global.css`.
- **Feedback**: Toda acción asíncrona DEBE mostrar un loader y terminar en un toast.
