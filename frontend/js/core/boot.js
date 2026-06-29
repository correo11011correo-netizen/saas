/**
 * OMNICORE BOOTSTRAP
 * Controla el inicio de la aplicación y el guardia de seguridad.
 */

window.onload = () => {
    const path = window.location.pathname;
    const isAuthenticated = Session.isAuthenticated();

    // Guardia de Seguridad:
    if ((path === '/app' || path !== '/') && !isAuthenticated) {
        console.log('Acceso denegado. Redirigiendo a Welcome...');
        Welcome.init();
        return;
    }

    // Flujo Normal
    Session.checkAuth(
        async (user) => {
            console.log('Autenticado como:', user.email);
            // Importante: App.init ahora es async y maneja el manifiesto y el SyncManager
            await App.init();
        },
        () => {
            console.log('No autenticado. Cargando pantalla de bienvenida...');
            Welcome.init();
        }
    );
};
