/**
 * App Orchestrator
 * Coordina la carga de datos y la actualización de la UI.
 */
const API_URL = 'http://localhost:8080/get_layout_manifest';

async function loadManifest(role) {
    try {
        const response = await fetch(`${API_URL}?role=${role}`);
        const manifest = await response.json();
        store.setState({ manifest });
    } catch (error) {
        console.error("Error cargando el manifiesto:", error);
        alert("Asegúrate de que el backend esté corriendo en http://localhost:8080");
    }
}

function selectModule(moduleId) {
    const { manifest } = store.getState();
    const moduleData = manifest.modules[moduleId];

    store.setState({
        activeModule: moduleId,
        activePanel: moduleData.dock[0]?.id || null
    });

    document.getElementById('hub-container').classList.add('hidden');
    document.getElementById('module-view').classList.remove('hidden');
    document.getElementById('dock-container').classList.remove('hidden');
    document.getElementById('active-module-title').innerText =
        manifest.hub.find(h => h.id === moduleId).label;
}

function selectPanel(panelId) {
    store.setState({ activePanel: panelId });
    document.getElementById('panel-content').innerHTML = `
        <div style="padding: 20px; background: white; border-radius: 8px; box-shadow: var(--shadow);">
            <h3>Panel: ${panelId}</h3>
            <p>Este contenido es generado dinámicamente. El usuario solo puede ver este panel porque el backend lo permitió en el manifiesto.</p>
        </div>
    `;
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    const roleSelector = document.getElementById('role-selector');
    const backBtn = document.getElementById('back-to-hub');

    // Suscribirse a cambios de estado para re-renderizar
    store.subscribe((state) => {
        if (!state.manifest) return;

        ui.renderUser(state.manifest.user);

        // Renderizar Hub si no hay módulo activo
        if (!state.activeModule) {
            ui.renderHub(state.manifest.hub, selectModule);
        }

        // Renderizar Dock si hay módulo activo
        if (state.activeModule) {
            const moduleConfig = state.manifest.modules[state.activeModule];
            ui.renderDock(moduleConfig.dock, state.activePanel, selectPanel);
            ui.renderMenu(moduleConfig.menu, (id) => alert(`Acción: ${id}`));
        }
    });

    // Cambio de rol manual
    roleSelector.onchange = (e) => {
        store.setState({ activeModule: null, activePanel: null });
        document.getElementById('hub-container').classList.remove('hidden');
        document.getElementById('module-view').classList.add('hidden');
        document.getElementById('dock-container').classList.add('hidden');
        loadManifest(e.target.value);
    };

    backBtn.onclick = () => {
        store.setState({ activeModule: null, activePanel: null });
        document.getElementById('hub-container').classList.remove('hidden');
        document.getElementById('module-view').classList.add('hidden');
        document.getElementById('dock-container').classList.add('hidden');
    };

    // Carga inicial
    loadManifest(roleSelector.value);
});
