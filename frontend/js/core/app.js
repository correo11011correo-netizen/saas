/**
 * OMNICORE APP ORCHESTRATOR
 * Gestiona la carga del Motor App, el Hub Central y el Dock Dinámico.
 */

const App = {
    state: {
        activeModule: 'hub',
        activePanel: 'hub',
        moduleConfig: {
            hub: {
                dock: [
                    { id: 'stock', icon: 'box', label: 'Stock' },
                    { id: 'sales', icon: 'sales', label: 'Ventas' },
                    { id: 'whatsapp', icon: 'whatsapp', label: 'WhatsApp' }
                ],
                panels: [
                    { id: 'profile', icon: 'user', label: 'Perfil' }
                ]
            }
        }
    },

    init() {
        this.renderHub();
        this.bindEvents();
    },

    renderHub() {
        this.state.activeModule = 'hub';
        this.state.activePanel = 'hub';
        UI.toast('Cargando Hub Central...', 'info');

        const html = `
            <div class="app-container" style="display: flex; flex-direction: column; height: 100vh; padding-bottom: 80px;">
                <header style="padding: var(--spacing-lg); background: var(--color-surface); border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h2 style="font-size: 20px;">OmniHub</h2>
                        <p class="text-muted" style="font-size: 12px;">Bienvenido, ${Session.getUser()?.business_name || 'Usuario'}</p>
                    </div>
                    <button id="logout-btn" class="btn" style="padding: 8px 12px; font-size: 12px; background: var(--color-border); color: var(--color-text-main);">Salir</button>
                </header>

                <main id="app-content" style="flex: 1; padding: var(--spacing-lg); overflow-y: auto;">
                    <div class="modules-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md);">
                        <div class="module-card" onclick="App.loadModule('sales')" style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); text-align: center; cursor: pointer; border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                            <div style="margin-bottom: 8px; color: var(--color-primary);">${Icons.sales}</div>
                            <div style="font-weight: 600;">Ventas</div>
                        </div>
                        <div class="module-card" onclick="App.loadModule('stock')" style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); text-align: center; cursor: pointer; border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                            <div style="margin-bottom: 8px; color: var(--color-primary);">${Icons.box}</div>
                            <div style="font-weight: 600;">Stock</div>
                        </div>
                        <div class="module-card" onclick="App.loadModule('whatsapp')" style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); text-align: center; cursor: pointer; border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                            <div style="margin-bottom: 8px; color: var(--color-primary);">${Icons.whatsapp}</div>
                            <div style="font-weight: 600;">WhatsApp</div>
                        </div>
                        <div class="module-card" onclick="App.loadModule('profile')" style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); text-align: center; cursor: pointer; border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                            <div style="margin-bottom: 8px; color: var(--color-primary);">${Icons.user}</div>
                            <div style="font-weight: 600;">Perfil</div>
                        </div>
                    </div>
                </main>

                <nav id="app-dock" style="position: fixed; bottom: 0; left: 0; right: 0; height: 70px; display: flex; justify-content: space-around; align-items: center; padding: 0 var(--spacing-md); z-index: 100;">
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
        const activeModule = this.state.activeModule;
        const config = this.state.moduleConfig[activeModule] || this.state.moduleConfig['hub'];
        const dynamicIcons = config.dock || [];

        let dockHtml = `
            <div onclick="App.renderHub()" style="cursor: pointer; color: ${this.state.activePanel === 'hub' ? 'var(--color-primary)' : 'var(--color-text-muted)'}; font-size: 24px; transition: all 0.2s;">${Icons.home}</div>
        `;

        for (let i = 0; i < 3; i++) {
            const item = dynamicIcons[i];
            if (item) {
                dockHtml += `
                    <div onclick="App.loadModule('${activeModule}', '${item.id}')" style="cursor: pointer; color: ${this.state.activePanel === item.id ? 'var(--color-primary)' : 'var(--color-text-muted}'}; font-size: 24px; transition: all 0.2s;">${Icons[item.icon]}</div>
                `;
            } else {
                dockHtml += `<div style="width: 24px;"></div>`;
            }
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
    UI.showLoading();
    UI.toast(`Cargando ${moduleName}...`, 'info');

    try {
        await this.loadScript(`/js/modules/${moduleName}.js`);
        const module = window[moduleName.charAt(0).toUpperCase() + moduleName.slice(1)];

        if (module && typeof module.render === 'function') {
            if (module.config) {
                this.state.moduleConfig[moduleName] = module.config;
            }

            const targetPanel = panelId || module.defaultPanel || 'inventory';
            module.render(targetPanel);

            this.state.activeModule = moduleName; // CORRECTO: el módulo es 'stock'
            this.state.activePanel = targetPanel; // CORRECTO: el panel es 'pos'
            this.renderDock();
        } else {
            throw new Error(`El módulo ${moduleName} no implementa la función render().`);
        }
    } catch (e) {
        UI.toast(`Error al cargar módulo: ${e.message}`, 'error');
        this.renderHub();
    } finally {
        UI.hideLoading();
    }
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
