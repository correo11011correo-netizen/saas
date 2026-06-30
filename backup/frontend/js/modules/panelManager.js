/**
 * OMNICORE PANEL MANAGER
 * Interfaz de administración para la gestión de la UI dinámica.
 * Permite crear, editar y organizar paneles para roles y clientes.
 */

const PanelManager = {
    state: {
        panels: [],
        editingPanel: null,
        filterRole: 'all'
    },

    async render(panelId = 'list') {
        if (panelId === 'list') {
            await this.renderList();
        } else {
            await this.renderEditor(panelId);
        }
    },

    async renderList() {
        UI.showLoading();
        try {
            const res = await API.execute('panel.list');
            this.state.panels = res.data;
            this.renderUI();
        } catch (e) {
            UI.toast('Error cargando paneles', 'error');
        } finally {
            UI.hideLoading();
        }
    },

    renderUI() {
        const filtered = this.state.panels.filter(p =>
            this.state.filterRole === 'all' || p.required_role === this.state.filterRole
        );

        const rows = filtered.map(p => `
            <div class="panel-item" onclick="PanelManager.editPanel('${p.panel_id}')">
                <div class="panel-info">
                    <span class="panel-name">${p.name}</span>
                    <span class="panel-id">${p.panel_id}</span>
                    <span class="role-badge ${p.required_role || 'global'}">${p.required_role || 'Global'}</span>
                </div>
                <div class="panel-actions">
                    <button onclick="event.stopPropagation(); PanelManager.deletePanel('${p.panel_id}')" class="btn-icon btn-danger">✕</button>
                </div>
            </div>
        `).join('');

        const html = `
            <div class="admin-container">
                <header class="admin-header">
                    <div>
                        <h2>Gestor de Paneles</h2>
                        <p class="text-muted">Configuración de la UI Dinámica del Sistema</p>
                    </div>
                    <button onclick="PanelManager.openEditor()" class="btn btn-primary">＋ Nuevo Panel</button>
                </header>

                <div class="admin-filters">
                    <select onchange="PanelManager.setFilter(this.value)" class="form-select">
                        <option value="all" ${this.state.filterRole === 'all' ? 'selected' : ''}>Todos los Roles</option>
                        <option value="admin" ${this.state.filterRole === 'admin' ? 'selected' : ''}>Administradores</option>
                        <option value="employee" ${this.state.filterRole === 'employee' ? 'selected' : ''}>Empleados</option>
                        <option value="support" ${this.state.filterRole === 'support' ? 'selected' : ''}>Soporte</option>
                        <option value="superadmin" ${this.state.filterRole === 'superadmin' ? 'selected' : ''}>SuperAdmin</option>
                    </select>
                </div>

                <div class="admin-list">
                    ${rows || '<p class="text-center text-muted">No se encontraron paneles</p>'}
                </div>
            </div>
        `;
        UI.render('app-content', html);
    },

    setFilter(role) {
        this.state.filterRole = role;
        this.renderUI();
    },

    openEditor() {
        this.state.editingPanel = null;
        this.renderEditor();
    },

    async editPanel(panelId) {
        const panel = this.state.panels.find(p => p.panel_id === panelId);
        if (!panel) return;
        this.state.editingPanel = panel;
        this.renderEditor();
    },

    renderEditor(panelId = null) {
        const p = this.state.editingPanel;
        const isEdit = !!p;

        const html = `
            <div class="admin-container">
                <header class="admin-header">
                    <div>
                        <h2>${isEdit ? 'Editar Panel' : 'Nuevo Panel'}</h2>
                        <p class="text-muted">Define la visibilidad y configuración del panel</p>
                    </div>
                    <button onclick="PanelManager.renderList()" class="btn btn-outline">Volver</button>
                </header>

                <div class="admin-form">
                    <div class="form-group">
                        <label>ID del Panel (Técnico)</label>
                        <input type="text" id="p-id" value="${p?.panel_id || ''}" placeholder="ej: sales.pos" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Nombre Visible</label>
                        <input type="text" id="p-name" value="${p?.name || ''}" placeholder="ej: Punto de Venta" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Icono (Key de Icons.js)</label>
                        <input type="text" id="p-icon" value="${p?.config_json?.icon || ''}" placeholder="ej: shopping_cart" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Rol Requerido</label>
                        <select id="p-role" class="form-select">
                            <option value="">Global (Todos)</option>
                            <option value="admin" ${p?.required_role === 'admin' ? 'selected' : ''}>Admin</option>
                            <option value="employee" ${p?.required_role === 'employee' ? 'selected' : '' },
                            <option value="support" ${p?.required_role === 'support' ? 'selected' : ''}>Soporte</option>
                            <option value="superadmin" ${p?.required_role === 'superadmin' ? 'selected' : ''}>SuperAdmin</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Prioridad (Orden en el Dock)</label>
                        <input type="text" id="p-priority" value="${p?.priority || '0'}" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>ID de Cliente (Opcional - Personalización)</label>
                        <input type="text" id="p-tenant" value="${p?.tenant_id || ''}" placeholder="UUID del Cliente" class="form-input">
                    </div>
                    <div class="form-actions">
                        <button onclick="PanelManager.savePanel()" class="btn btn-primary">${isEdit ? 'Guardar Cambios' : 'Crear Panel'}</button>
                    </div>
                </div>
            </div>
        `;
        UI.render('app-content', html);
    },

    async savePanel() {
        const data = {
            panel_id: document.getElementById('p-id').value,
            name: document.getElementById('p-name').value,
            config_json: { icon: document.getElementById('p-icon').value },
            required_role: document.getElementById('p-role').value || null,
            priority: document.getElementById('p-priority').value,
            tenant_id: document.getElementById('p-tenant').value || null
        };

        if (!data.panel_id || !data.name) {
            UI.toast('El ID y el Nombre son obligatorios', 'error');
            return;
        }

        try {
            const cmd = this.state.editingPanel ? 'panel.update' : 'panel.create';
            await API.execute(cmd, data);
            UI.toast('Panel guardado exitosamente', 'success');
            this.renderList();
        } catch (e) {
            UI.toast('Error al guardar el panel', 'error');
        }
    },

    async deletePanel(panelId) {
        if (!confirm('¿Estás seguro de borrar este panel?')) return;
        try {
            await API.execute('panel.delete', { panel_id: panelId });
            UI.toast('Panel eliminado', 'success');
            this.renderList();
        } catch (e) {
            UI.toast('Error al eliminar', 'error');
        }
    }
};

window.PanelManager = PanelManager;
