# 🗺️ Plan: Sistema de Navegación Dinámica Basada en Roles

## 🎯 Objetivo
Implementar un sistema donde la interfaz de usuario (Hub, Dock y Menú) sea generada dinámicamente por el backend basándose en la identidad, el rol y los permisos específicos del usuario.

## 👥 Matriz de Acceso
El sistema debe soportar los siguientes niveles de jerarquía:

| Rol | Ámbito | Capacidad de Navegación |
| :--- | :--- | :--- |
| **SuperAdmin** | Global (SaaS) | Acceso total a gestión de planes, tenants, facturación global y configuración del sistema. |
| **Soporte** | Multi-Tenant | Acceso a herramientas de diagnóstico, logs de clientes y capacidad de "impersonate" (entrar como cliente). |
| **Dueño (Admin)** | Tenant propio | Gestión total de su negocio, configuración de bots, y **definición de permisos para sus empleados**. |
| **Empleado** | Tenant propio | Acceso limitado a los paneles que el Dueño haya habilitado explícitamente. |

---

## 🛠️ Implementación Técnica

### 1. Backend: Infraestructura de Permisos
Actualmente, el sistema usa `ModuleEntitlementService` para filtrar módulos por plan. Expandiremos esto para filtrar **Paneles** por rol.

#### Cambios en Base de Datos (Propuesto)
- Crear tabla `user_role_permissions`:
    - `id`, `tenant_id`, `role_name` (ej: 'employee'), `module_id`, `panel_id`, `is_enabled`.
    - Esto permite que el Dueño marque qué paneles ve el rol 'employee' en su empresa.
- Tabla `system_layouts`:
    - Definiciones predeterminadas para `superadmin` y `support`.

#### Nuevo Comando: `system.get_layout_manifest`
Este comando será el corazón de la navegación. Al ejecutarse, devolverá un JSON con la siguiente estructura:

```json
{
  "user": { "role": "employee", "name": "Juan" },
  "hub": [
    { "id": "stock", "icon": "box", "label": "Stock", "active": true },
    { "id": "whatsapp", "icon": "whatsapp", "label": "Chats", "active": true }
  ],
  "modules": {
    "stock": {
      "dock": [
        { "id": "inventory", "icon": "box", "label": "Inventario" },
        { "id": "pos", "icon": "sales", "label": "Cobrar" }
      ],
      "menu": [
        { "id": "profile", "icon": "user", "label": "Mi Perfil" }
      ]
    },
    "whatsapp": {
      "dock": [
        { "id": "messages", "icon": "whatsapp", "label": "Mensajes" }
      ],
      "menu": []
    }
  }
}
```

### 2. Frontend: Motor de Renderizado Dinámico
El frontend dejará de tener `config: { dock: [...] }` dentro de cada módulo.

#### Flujo de Carga:
1.  **Login** $ightarrow$ Recibe Token.
2.  **Boot** $ightarrow$ Llama a `API.execute('system.get_layout_manifest')`.
3.  **Store** $ightarrow$ Guarda el manifiesto en el estado global (`StateStore`).
4.  **UI Render** $ightarrow$
    - El `Hub` se dibuja usando `manifest.hub`.
    - El `Dock` se dibuja usando `manifest.modules[activeModule].dock`.
    - El `Menu` se dibuja usando `manifest.modules[activeModule].menu`.

---

## 📅 Fases de Implementación

### Fase 1: Definición y Backend (Cerebro)
- [ ] Crear migración para `user_role_permissions`.
- [ ] Implementar el comando `system.get_layout_manifest` en el backend.
- [ ] Crear la lógica de filtrado: `Plan` $ightarrow$ `Rol` $ightarrow$ `Permiso Manual`.

### Fase 2: Core del Frontend (Esqueleto)
- [ ] Implementar `StateStore` para almacenar el manifiesto.
- [ ] Refactorizar `App.renderHub` y `App.renderDock` para que lean del `StateStore`.
- [ ] Eliminar las configuraciones `config: { ... }` hardcodeadas en los módulos (`stock.js`, `whatsapp.js`, etc.).

### Fase 3: Gestión de Permisos (Control)
- [ ] Crear un panel de "Gestión de Empleados" donde el Dueño pueda activar/desactivar paneles para el rol de empleado.
- [ ] Implementar las vistas específicas para **Soporte** y **SuperAdmin**.

### Fase 4: Validación y Pruebas
- [ ] Test de login como Dueño $ightarrow$ Verificar vista total.
- [ ] Test de login como Empleado $ightarrow$ Verificar vista restringida.
- [ ] Test de cambio de permiso en tiempo real $ightarrow$ Verificar actualización de dock.

## ⚠️ Riesgos y Mitigaciones
- **Riesgo**: Latencia al cargar el manifiesto en cada inicio.
- **Mitigación**: Cachear el manifiesto en `localStorage` y refrescarlo solo mediante un evento de "Update Layout" desde el backend.
- **Riesgo**: Error en el manifiesto que deje al usuario sin navegación.
- **Mitigación**: Implementar un "Fallback Layout" básico en el frontend.
