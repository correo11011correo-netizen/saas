/**
 * App Orchestrator
 * El cerebro que conecta la API, el Estado y la UI.
 */
const App = {
    state: {
        user: null,
        manifest: null,
        activeModule: null,
        activePanel: null
    },

    async init() {
        console.log("App initializing...");
        await this.loadLayout();
    },

    async loadLayout() {
        const role = Session.getUserRole();

        try {
            // Llamada al Dispatcher para obtener el manifiesto
            const manifest = await API.execute('system.get_layout_manifest', { role: role });

            this.state.manifest = manifest;
            this.state.user = manifest.user;

            UI.renderUser(this.state.user);
            this.renderCurrentView();
        } catch (e) {
            alert("Error cargando el manifiesto. ¿Está el servidor corriendo?");
        }
    },

    renderCurrentView() {
        const { manifest, activeModule, activePanel } = this.state;

        if (!activeModule) {
            UI.hideModule();
            UI.renderHub(manifest.hub, (id) => this.selectModule(id));
        } else {
            const moduleCfg = manifest.modules[activeModule];
            const moduleTitle = manifest.hub.find(h => h.id === activeModule).label;

            UI.showModule(moduleTitle, activePanel);
            UI.renderDock(moduleCfg.dock, activePanel, (id) => this.selectPanel(id));
        }
    },

    selectModule(moduleId) {
        const moduleCfg = this.state.manifest.modules[moduleId];
        this.state.activeModule = moduleId;
        this.state.activePanel = moduleCfg.dock[0]?.id || null;
        this.renderCurrentView();
    },

    selectPanel(panelId) {
        this.state.activePanel = panelId;
        this.renderCurrentView();
    },

    goBack() {
        this.state.activeModule = null;
        this.state.activePanel = null;
        this.renderCurrentView();
    }
};
