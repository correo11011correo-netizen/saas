# 🛠️ PoC: Sistema de Navegación Dinámica

## 🎯 Objetivo
Este prototipo sirve como prueba de concepto (PoC) para demostrar cómo migrar la navegación de una estructura estática (hardcoded en JS) a una estructura dinámica controlada por el servidor.

## 📂 Estructura del Proyecto
El proyecto está dividido en dos capas independientes para facilitar el estudio:

### 1. Backend (`/backend`)
Simula la lógica del servidor que decide qué ve el usuario.
- **`permissions_mock.py`**: Define los roles (`superadmin`, `owner`, `employee`) y la matriz de permisos.
- **`manifest_generator.py`**: El "motor" que filtra los módulos y paneles según el rol y genera el JSON final.
- **`api_endpoint_mock.py`**: Un servidor minimalista que expone el endpoint `/get_layout_manifest`.

### 2. Frontend (`/frontend`)
Un entorno simplificado que consume el manifiesto y construye la interfaz.
- **`state_store.js`**: Almacena el manifiesto recibido del backend para que sea accesible desde cualquier parte de la app.
- **`ui_engine.js`**: Contiene la lógica de renderizado. No sabe qué botones existen, solo dibuja lo que el manifiesto le indica.
- **`app.js`**: Coordina el flujo: `Carga Manifiesto` $ightarrow$ `Actualiza Store` $ightarrow$ `Renderiza UI`.

---

## 🚀 Guía de Ejecución para Desarrolladores

### Paso 1: Iniciar el Backend
Abre una terminal y ejecuta el servidor de manifiestos:
```bash
cd poc-navegacion-dinamica/backend
python api_endpoint_mock.py
```
*El servidor correrá en `http://localhost:8080`.*

### Paso 2: Abrir el Frontend
Simplemente abre el archivo `frontend/index.html` en cualquier navegador moderno.

### Paso 3: Experimentar
1. Usa el **Simulador de Rol** en la parte superior de la página.
2. Cambia entre **Empleado**, **Dueño** y **SuperAdmin**.
3. Observa cómo:
    - Los iconos del **Hub** cambian.
    - Los botones del **Dock** inferior aparecen o desaparecen según el módulo y el rol.
    - El nombre del usuario se actualiza.

## 🧐 Puntos de Análisis Técnico
Los desarrolladores deben fijarse en:
1. **Cero Lógica de Permisos en JS**: El frontend no tiene `if (user.role === 'admin')`. Simplemente renderiza lo que llega en el JSON.
2. **Single Source of Truth**: El backend es la única fuente de verdad sobre la estructura de la interfaz.
3. **Agilidad de Cambios**: Intenta cambiar un permiso en `backend/permissions_mock.py`, reinicia el servidor y recarga la página. La UI cambia sin tocar el frontend.
