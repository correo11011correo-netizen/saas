/**
 * OMNICORE BOOTSTRAP
 * Controla el inicio de la aplicación y el guardia de seguridad.
 */

window.onload = () => {
    const path = window.location.pathname;
    const isAuthenticated = Session.isAuthenticated();

    // Guardia de Seguridad:
    // Si intenta acceder a /app (o cualquier ruta protegida) sin sesión -> Welcome
    if ((path === '/app' || path !== '/') && !isAuthenticated) {
        console.log('Acceso denegado. Redirigiendo a Welcome...');
        Welcome.init();
        return;
    }

    // Flujo Normal
    Session.checkAuth(
        (user) => {
            console.log('Autenticado como:', user.email);
            App.init();
        },
        () => {
            console.log('No autenticado. Cargando pantalla de bienvenida...');
            Welcome.init();
        }
    );
};
