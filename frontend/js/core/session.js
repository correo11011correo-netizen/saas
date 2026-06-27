/**
 * OMNICORE SESSION MANAGER
 * Gestión de tokens, autenticación y control de acceso.
 */

const Session = {
    TOKEN_KEY: 'omnicore_token',
    USER_DATA_KEY: 'omnicore_user',

    /**
     * Guarda la sesión en localStorage.
     */
    saveSession(token, userData) {
        localStorage.setItem(this.TOKEN_KEY, token);
        localStorage.setItem(this.USER_DATA_KEY, JSON.stringify(userData));
    },

    /**
     * Limpia la sesión y redirige al login.
     */
    clearSession() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_DATA_KEY);
        window.location.reload(); // Reiniciar app para limpiar estado
    },

    /**
     * Obtiene el token actual.
     */
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    /**
     * Obtiene los datos del usuario.
     */
    getUser() {
        const data = localStorage.getItem(this.USER_DATA_KEY);
        return data ? JSON.parse(data) : null;
    },

    /**
     * Verifica si hay una sesión activa.
     */
    isAuthenticated() {
        return !!this.getToken();
    },

    /**
     * Guarda el estado de autenticación y decide qué motor cargar.
     * @param {Function} onAuthSuccess - Callback si está autenticado.
     * @param {Function} onAuthFail - Callback si no lo está.
     */
    checkAuth(onAuthSuccess, onAuthFail) {
        if (this.isAuthenticated()) {
            onAuthSuccess(this.getUser());
        } else {
            onAuthFail();
        }
    }
};

window.Session = Session;
