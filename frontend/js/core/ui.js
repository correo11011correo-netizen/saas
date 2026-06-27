/**
 * OMNICORE UI CORE
 * Componentes visuales globales y reutilizables.
 */

const UI = {
    /**
     * Muestra una notificación flotante (Toast).
     * @param {string} message - Mensaje a mostrar.
     * @param {string} type - 'success', 'error', 'warning' o 'info'.
     */
    toast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerText = message;

        container.appendChild(toast);

        // Auto-eliminar después de 3 segundos
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-20px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /**
     * Muestra un indicador de carga pantalla completa.
     */
    showLoading() {
        if (document.querySelector('.loading-overlay')) return;

        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `<div class="spinner"></div>`;
        document.body.appendChild(overlay);
    },

    /**
     * Oculta el indicador de carga.
     */
    hideLoading() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) overlay.remove();
    },

    /**
     * Renderiza un componente HTML simple en un contenedor.
     * @param {string} containerId - ID del elemento donde montar.
     * @param {string} html - String HTML a insertar.
     */
    render(containerId, html) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = html;
        }
    }
};

window.UI = UI;
