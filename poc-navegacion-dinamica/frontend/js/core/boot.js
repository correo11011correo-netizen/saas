/**
 * Boot Sequence
 * Punto de entrada de la aplicación.
 */
window.onload = async () => {
    console.log("Bootstrapping application...");

    // 1. Inicializar el orquestador
    await App.init();

    // 2. Configurar el botón de volver
    document.getElementById('btn-back').onclick = () => App.goBack();

    // 3. Configurar el simulador de roles (PoC Tool)
    const roleSelector = document.getElementById('role-selector');
    roleSelector.value = Session.getUserRole();

    roleSelector.onchange = async (e) => {
        const newRole = e.target.value;
        Session.setRole(newRole);

        // Reset state and reload
        App.state.activeModule = null;
        App.state.activePanel = null;
        await App.loadLayout();
    };
};
