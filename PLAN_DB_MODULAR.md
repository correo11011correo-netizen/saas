# Plan Maestro: Arquitectura Modular y Evolutiva de Base de Datos

Este plan propone abandonar el script monolítico `core/init_db.py` en favor de una arquitectura de migraciones modular, escalable y profesional, basada en **Alembic** y un diseño orientado a módulos.

## 🎯 Objetivos
- **Desacoplamiento:** Cada módulo (`core`, `sales`, `stock`, `crm`, `whatsapp`) poseerá su propia definición de esquema.
- **Seguridad:** Eliminar las race conditions (el error de 'table not exists') mediante un sistema de gestión de migraciones que controle el estado de la DB.
- **Escalabilidad:** Permitir conectar múltiples bases de datos o migrar a servicios más complejos (ej: Sharding) en el futuro.
- **Mantenibilidad:** Un único desarrollador puede agregar una tabla nueva sin tocar el `init_db` central, simplemente añadiendo una migración en su módulo.

## 🛠️ Pasos de Implementación

### Fase 1: Adopción de Alembic (Orquestador)
- Instalar y configurar `Alembic` en la raíz del proyecto.
- Crear un entorno de migraciones que detecte automáticamente los modelos de `SQLAlchemy` definidos en cada módulo.

### Fase 2: Modularización de Esquemas
- Crear una carpeta `migrations/versions/` para el histórico.
- Reorganizar la lógica:
    - `core/models.py`: Definir tablas de usuarios, tenants, roles.
    - `sales/models.py`: Definir tablas de ventas, items.
    - `stock/models.py`: Definir tablas de productos, movimientos.
- Cada modelo debe usar `Base = declarative_base()` para que Alembic pueda autogenerar los cambios.

### Fase 3: Automatización de Provisionamiento por Tenant
- Crear una "Función de Setup de Tenant" dentro del `SaaSAdminCommandHandler`.
- Cuando se registra un nuevo tenant, el sistema ejecutará solo las "Vistas" o "Tablas específicas de datos" necesarias, asegurando que el tenant tenga sus recursos listos desde el inicio.

### Fase 4: Optimización y Mantenimiento
- Implementar scripts de mantenimiento diarios (vacuum, cleanup de logs de auditoría antiguos).
- Centralizar las conexiones de DB en un nuevo módulo `core/database.py` que gestione el pool de conexiones de manera eficiente.

## 📋 Criterios de Aceptación
- [ ] No existe `core/init_db.py` monolítico.
- [ ] Alembic controla todas las versiones de la base de datos.
- [ ] Cada módulo tiene sus propios modelos definidos.
- [ ] Los despliegues en Railway fallan si las migraciones no están sincronizadas.

---
*¿Estás de acuerdo con este plan de modularización? Si me das el visto bueno, procederé a instalar Alembic y a preparar la estructura de carpetas.*
