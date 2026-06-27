/**
 * OMNICORE API WRAPPER
 * Único punto de contacto con el Backend.
 * Estándar de Coherencia: Toda petición pasa por aquí.
 */

// Usamos rutas relativas para evitar problemas de CORS y dependencias de dominio en producción.
// Esto funciona porque el frontend es servido por el mismo servidor FastAPI.
const API_BASE_URL = '';

const API = {
    /**
     * Ejecuta un comando universal en el sistema OmniCore.
     * @param {string} command - Nombre del comando (ej: 'sales.cobrar')
     * @param {Object} params - Parámetros del comando
     * @returns {Promise<any>} Resultado del comando
     */
    async execute(command, params = {}) {
        const token = localStorage.getItem('omnicore_token');

        if (!token) {
            throw new Error('No session found. Please login.');
        }

        try {
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
        } catch (error) {
            console.error(`[API Error] ${command}:`, error);
            throw error;
        }
    },

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
