/**
 * OMNICORE API WRAPPER
 * Único punto de contacto con el Backend.
 * Estándar de Coherencia: Toda petición pasa por aquí.
 */

// Usamos rutas relativas para evitar problemas de CORS y dependencias de dominio en producción.
// Esto funciona porque el frontend es servido por el mismo servidor FastAPI.
const API_BASE_URL = '';

const API = {
const API = {
    /**
     * Ejecuta un comando universal con soporte para modo Offline.
     * Si no hay conexión, el comando se encola para sincronización posterior.
     */
    async execute(command, params = {}) {
        try {
            return await this.executeDirect(command, params);
        } catch (error) {
            // Si el error es de conexión (TypeError: Failed to fetch), encolamos la acción
            if (error.message.includes('Failed to fetch') || !navigator.onLine) {
                SyncManager.enqueue(command, params);
                return {
                    success: true,
                    offline: true,
                    message: 'Acción guardada localmente. Se sincronizará al recuperar la conexión.'
                };
            }
            throw error;
        }
    },

    /**
     * Versión directa de ejecución sin interceptor de cola.
     * Usado internamente por SyncManager.
     */
    async executeDirect(command, params = {}) {
        const token = localStorage.getItem('omnicore_token');

        if (!token) {
            throw new Error('No session found. Please login.');
        }

        const response = await fetch(`${API_BASE_URL}/api/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                command: command,
                params: params
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Execution error');
        }

        return await response.json();
    },

    /**
     * Autenticación: Login

    /**
     * Autenticación: Login
     */
    async login(email, password) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }

            return await response.json();
        } catch (error) {
            console.error('[API Login Error]:', error);
            throw error;
        }
    },

    /**
     * Autenticación: Registro
     */
    async register(email, password, businessName) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    password,
                    business_name: businessName
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Registration failed');
            }

            return await response.json();
        } catch (error) {
            console.error('[API Register Error]:', error);
            throw error;
        }
    }
};

// Exportar para usar en otros scripts
window.API = API;
