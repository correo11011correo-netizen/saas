/**
 * OMNICORE APP ORCHESTRATOR
 * Gestiona la carga del Motor App, el Hub Central y el Dock Dinámico.
 */

const App = {
    state: {
        activeModule: 'hub',
        activePanel: 'hub',
        manifest: null // Stores the dynamic config from /api/boot
    },

    async init() {
        try {
            // 1. Inicializar Capas de Datos y Sincronización
            await LocalStore.init();
            await SyncEngine.init();

            await this.syncManifest();
            this.renderHub();
            this.bindEvents();

            // Auto-sync offline queue on startup
            window.addEventListener('online', () => SyncEngine.processQueue());
            SyncEngine.processQueue();

            // Hot Update: Verificar cambios en el manifiesto cada 60 segundos
            setInterval(() => this.checkHotUpdate(), 60000);
        } catch (e) {
            console.error('Init Error:', e);
            UI.toast('Error al iniciar la aplicación', 'error');
        }
    },

    async checkHotUpdate() {
        try {
            const newManifest = await API.execute('core.get_boot_manifest'); // O endpoint /api/boot
            if (newManifest && newManifest.version !== this.state.manifest?.version) {
                console.log('Nueva configuración de UI detectada. Actualizando...');
                this.state.manifest = newManifest;
                this.renderHub();
                this.renderDock();
                UI.toast('Interfaz actualizada dinámicamente', 'success');
            }
        } catch (e) {
            console.error('Hot update check failed:', e);
        }
    },

    async syncManifest() {
        try {
            // Boot manifest is called via the app's boot flow, but we ensure it's here
            const bootData = await API.execute('core.get_boot_manifest'); // Assuming this command is mapped or using /api/boot
            this.state.manifest = bootData;
        } catch (e) {
            console.error('Failed to sync manifest:', e);
            // Fallback to a minimal manifest to avoid crash
            this.state.manifest = { dock: [], layout: { home: [] } };
        }
    },

    renderHub() {
        this.state.activeModule = 'hub';
        this.state.activePanel = 'hub';
        UI.toast('Cargando Hub Central...', 'info');

        const manifest = this.state.manifest || { dock: [], layout: { home: [] } };

        // Generar la grilla de módulos dinámicamente desde el dock del manifiesto
        const modulesHtml = manifest.dock.map(module => `
            <div class="module-card" onclick="App.loadModule('${module.id}')">
                <div class="module-card-icon">${Icons[module.icon] || Icons.default}</div>
                <div class="module-card-label">${module.label}</div>
            </div>
        `).join('');

        const html = `
            <div class="app-container">
                <header class="app-header">
                    <div>
                        <h2 style="font-size: 20px;">OmniHub</h2>
                        <p class="text-muted" style="font-size: 12px;">Bienvenido, ${Session.getUser()?.business_name || 'Usuario'}</p>
                    </div>
                    <button id="logout-btn" class="btn btn-outline">Salir</button>
                </header>

                <main id="app-content" class="app-main">
                    <div class="modules-grid">
                        ${modulesHtml}
                    </div>
                </main>

                <nav id="app-dock">
                    <!-- El dock se renderiza dinámicamente via renderDock() -->
                </nav>

                <div id="menu-panel" class="menu-panel">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-lg);">
                        <h3 style="font-size: 18px;">Configuración</h3>
                        <div onclick="App.toggleMenu()" style="cursor: pointer; color: var(--color-text-muted);">✕</div>
                    </div>
                    <div id="menu-items" style="flex: 1; display: flex; flex-direction: column; gap: var(--spacing-sm);">
                        <!-- Dinámico -->
                    </div>
                    <div style="border-top: 1px solid var(--color-border); padding-top: var(--spacing-md);">
                        <div onclick="Session.clearSession()" class="menu-item" style="color: var(--color-error);">
                            ${Icons.logout} <span>Cerrar Sesión</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        UI.render('app-root', html);
        this.renderDock();
    },

    renderDock() {
        const manifest = this.state.manifest || { dock: [] };
        const dockItems = manifest.dock || [];

        let dockHtml = `
            <div onclick="App.renderHub()" style="cursor: pointer; color: ${this.state.activePanel === 'hub' ? 'var(--color-primary)' : 'var(--color-text-muted)'}; font-size: 24px; transition: all 0.2s;">${Icons.home}</div>
        `;

        // Renderizar hasta 3 elementos del dock dinámico
        dockItems.slice(0, 3).forEach(item => {
            dockHtml += `
                <div onclick="App.loadModule('${item.id}')" style="cursor: pointer; color: ${this.state.activePanel === item.id ? 'var(--color-primary)' : 'var(--color-text-muted)'}; font-size: 24px; transition: all 0.2s;">${Icons[item.icon] || Icons.default}</div>
            `;
        });

        // Si hay menos de 3, rellenar con espacios
        for (let i = dockItems.length; i < 3; i++) {
            dockHtml += `<div style="width: 24px;"></div>`;
        }

        dockHtml += `
            <div onclick="App.toggleMenu()" style="cursor: pointer; color: ${this.state.activePanel === 'menu' ? 'var(--color-primary)' : 'var(--color-text-muted)'}; font-size: 24px; transition: all 0.2s;">${Icons.menu}</div>
        `;

        document.getElementById('app-dock').innerHTML = dockHtml;
    },

    updateMenu() {
        const config = this.state.moduleConfig[this.state.activeModule] || this.state.moduleConfig['hub'];
        const panels = config.panels || [];

        let itemsHtml = '';
        panels.forEach(panel => {
            itemsHtml += `
                <div onclick="App.loadModule('${panel.id}')" class="menu-item">
                    ${Icons[panel.icon]} <span>${panel.label}</span>
                </div>
            `;
        });

        document.getElementById('menu-items').innerHTML = itemsHtml || '<p class="text-muted" style="text-align: center; font-size: 12px;">No hay paneles adicionales</p>';
    },

    toggleMenu() {
        const panel = document.getElementById('menu-panel');
        if (panel.classList.contains('open')) {
            panel.classList.remove('open');
        } else {
            this.updateMenu();
            panel.classList.add('open');
        }
    },
async loadModule(moduleName, panelId = null) {
    if (this.state.activeModule === moduleName && this.state.activePanel === panelId) return;

    // 1. Limpieza del módulo anterior (Ciclo de Vida: Destroy)
    if (this.state.activeModule && window[this.state.activeModule.charAt(0).toUpperCase() + this.state.activeModule.slice(1)]) {
        const prevModule = window[this.state.activeModule.charAt(0).toUpperCase() + this.state.activeModule.slice(1)];
        if (typeof prevModule.destroy === 'function') {
            prevModule.destroy();
        }
    }

    UI.showLoading();
    UI.toast(`Cargando ${moduleName}...`, 'info');

    try {
        // 2. Carga del Script
        await this.loadScript(`/js/modules/${moduleName}.js`);
        const module = window[moduleName.charAt(0).toUpperCase() + moduleName.slice(1)];

        if (!module) throw new Error(`Módulo ${moduleName} no encontrado.`);

        // 3. Inicialización (Ciclo de Vida: Setup)
        if (typeof module.setup === 'function') {
            await module.setup();
        }

        // 4. Renderizado con Props del Manifiesto (Ciclo de Vida: Render)
        const panelConfig = this.state.manifest?.dock.find(p => p.id === panelId) || {};
        const targetPanel = panelId || module.defaultPanel || 'default';

        if (typeof module.render === 'function') {
            module.render(targetPanel, panelConfig);
            this.state.activeModule = moduleName;
            this.state.activePanel = targetPanel;
            this.renderDock();
        } else {
            throw new Error(`El módulo ${moduleName} no implementa render().`);
        }
    } catch (e) {
        UI.toast(`Error al cargar módulo: ${e.message}`, 'error');
        this.renderHub();
    } finally {
        UI.hideLoading();
    }
},

},
    async loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`No se pudo cargar el script: ${src}`));
            document.head.appendChild(script);
        });
    },

    bindEvents() {
        document.addEventListener('click', (e) => {
            // 1. Logout button
            if (e.target && e.target.id === 'logout-btn') {
                Session.clearSession();
            }

            // 2. Close menu when clicking outside
            const menu = document.getElementById('menu-panel');
            if (menu && menu.classList.contains('open')) {
                // If the click is NOT inside the menu AND NOT on the menu toggle icon in the dock
                const isClickInsideMenu = menu.contains(e.target);
                const isClickOnToggle = e.target.closest('[onclick="App.toggleMenu()"]');

                if (!isClickInsideMenu && !isClickOnToggle) {
                    this.toggleMenu();
                }
            }
        });
    }
};

window.App = App;
