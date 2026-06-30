/**
 * OMNICORE PROFILE MODULE
 * Gestión de perfil de negocio y administración de empleados.
 */

const Profile = {
    config: {
        dock: [
            { id: 'profile', icon: 'user', label: 'Perfil' },
            { id: 'hub', icon: 'home', label: 'Volver al Hub' },
            { id: 'settings', icon: 'settings', label: 'Ajustes' }
        ],
        panels: [
            { id: 'security', icon: 'settings', label: 'Seguridad' },
            { id: 'billing', icon: 'sales', label: 'Facturación' }
        ]
    },

    async render() {
        UI.render('app-content', `
            <div class="profile-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <section class="profile-card" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <h3 style="margin-bottom: var(--spacing-md); display: flex; align-items: center; gap: 10px;">${Icons.user} Datos del Negocio</h3>
                    <div id="profile-info" style="display: flex; flex-direction: column; gap: var(--spacing-sm);">
                        <p class="text-muted">Cargando información...</p>
                    </div>
                </section>

                <section class="integrations-section" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <h3 style="margin-bottom: var(--spacing-md); display: flex; align-items: center; gap: 10px;">${Icons.settings} Integraciones API</h3>
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                        ${this.renderIntegrationSection('whatsapp', 'WhatsApp Business')}
                        ${this.renderIntegrationSection('mercadopago', 'Mercado Pago')}
                    </div>
                </section>

                <section class="employees-section" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-md);">
                        <h3 style="margin: 0; display: flex; align-items: center; gap: 10px;">${Icons.user} Empleados</h3>
                        <button class="btn btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="Profile.showInviteForm()">+ Invitar</button>
                    </div>
                    <div id="employees-list" style="display: flex; flex-direction: column; gap: var(--spacing-sm);">
                        <p class="text-muted">Cargando empleados...</p>
                    </div>
                </section>
            </div>
        `);

        await this.loadProfileData();
        await this.loadEmployees();
        await this.loadAllCredentials();
    },

    renderIntegrationSection(service, label) {
        let fields = '';
        if (service === 'whatsapp') {
            fields = `
                <input type="text" id="new-${service}-key" class="input-field" placeholder="Access Token">
                <input type="text" id="new-${service}-phone" class="input-field" placeholder="Phone Number ID">
                <input type="password" id="new-${service}-secret" class="input-field" placeholder="App Secret (Opcional)">
            `;
        } else if (service === 'mercadopago') {
            fields = `
                <input type="text" id="new-${service}-key" class="input-field" placeholder="Access Token">
                <input type="text" id="new-${service}-public" class="input-field" placeholder="Public Key">
                <input type="text" id="new-${service}-client" class="input-field" placeholder="Client ID">
                <input type="password" id="new-${service}-secret" class="input-field" placeholder="Client Secret">
            `;
        }

        return `
            <div class="integration-section" id="section-${service}" style="border-bottom: 1px solid var(--color-border); padding-bottom: var(--spacing-md);">
                <div style="font-weight: 600; margin-bottom: var(--spacing-sm);">${label}</div>

                <div style="margin-bottom: var(--spacing-sm); background: var(--color-bg); padding: var(--spacing-sm); border-radius: var(--radius-sm);">
                    <label style="font-size: 11px; color: var(--color-text-muted);">Configuración Webhook:</label>
                    <div style="display: flex; flex-direction: column; gap: 5px; margin-top: 5px;">
                        <input type="text" id="url-${service}" class="input-field" readonly style="margin-bottom: 0; font-size: 11px; background: white;" placeholder="URL Webhook">
                        <input type="text" id="token-${service}" class="input-field" readonly style="margin-bottom: 0; font-size: 11px; background: white;" placeholder="Verify Token">
                        <button class="btn" style="padding: 4px; font-size: 11px; background: white; border: 1px solid var(--color-border);" onclick="Profile.copyWebhookDetails('${service}')">Copiar URL y Token</button>
                    </div>
                </div>

                <div id="list-${service}" style="display: flex; flex-direction: column; gap: var(--spacing-sm);">
                    <p class="text-muted">Cargando cuentas...</p>
                </div>

                <div style="margin-top: var(--spacing-sm); border: 1px dashed var(--color-border); padding: var(--spacing-md); border-radius: var(--radius-sm);">
                    <div style="font-weight: 600; font-size: 13px; margin-bottom: var(--spacing-sm);">Añadir nueva cuenta</div>
                    <input type="text" id="new-${service}-alias" class="input-field" placeholder="Nombre (ej: Principal)">
                    ${fields}
                    <button class="btn btn-primary" style="font-size: 12px; padding: 8px; width: 100%;" onclick="Profile.submitCredential('${service}')">Añadir Cuenta</button>
                </div>
            </div>
        `;
    },

    async loadAllCredentials() {
        try {
            const res = await API.execute('system.list_credentials', {});
            const creds = res.data || [];
            const services = ['whatsapp', 'mercadopago'];

            for (const s of services) {
                // 1. Cargar URL y Token
                try {
                    const hookRes = await API.execute('system.get_webhook_url', { service: s });
                    document.getElementById(`url-${s}`).value = hookRes.data.url;
                    document.getElementById(`token-${s}`).value = hookRes.data.verify_token;
                } catch(e) { console.error(e); }

                // 2. Cargar Cuentas
                const listEl = document.getElementById(`list-${s}`);
                const sCreds = creds.filter(c => c.service_name === s);

                listEl.innerHTML = sCreds.map(c => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: white; border: 1px solid var(--color-border); border-radius: var(--radius-sm);">
                        <span style="font-weight: 600; font-size: 13px;">${c.account_alias}</span>
                        <button class="btn" style="padding: 2px 6px; font-size: 10px; background: var(--color-error); color: white;" onclick="Profile.deleteCredential('${s}', '${c.account_alias}')">✕</button>
                    </div>
                `).join('') || '<p class="text-muted" style="font-size: 12px;">No hay cuentas configuradas.</p>';
            }
        } catch (e) {
            UI.toast('Error cargando cuentas', 'error');
        }
    },

    async submitCredential(service) {
        const alias = document.getElementById(`new-${service}-alias`).value;
        const apiKey = document.getElementById(`new-${service}-key`).value;
        const secret = document.getElementById(`new-${service}-secret`).value;

        if (!alias || !apiKey) return UI.toast('Alias y API Key/Token son obligatorios', 'error');

        let metadata = {};
        if (service === 'whatsapp') {
            metadata = { phone_number_id: document.getElementById(`new-${service}-phone`).value };
        } else if (service === 'mercadopago') {
            metadata = {
                public_key: document.getElementById(`new-${service}-public`).value,
                client_id: document.getElementById(`new-${service}-client`).value
            };
        }

        UI.showLoading();
        try {
            await API.execute('system.set_credential', {
                service,
                account_alias: alias,
                api_key: apiKey,
                secret,
                metadata: JSON.stringify(metadata)
            });
            UI.toast('Cuenta añadida', 'success');
            await this.loadAllCredentials();
            // Clear inputs
            document.getElementById(`new-${service}-alias`).value = '';
            document.getElementById(`new-${service}-key`).value = '';
            document.getElementById(`new-${service}-secret`).value = '';
            if(service === 'whatsapp') document.getElementById(`new-${service}-phone`).value = '';
            if(service === 'mercadopago') {
                document.getElementById(`new-${service}-public`).value = '';
                document.getElementById(`new-${service}-client`).value = '';
            }
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async deleteCredential(service, account_alias) {
        if (!confirm(`¿Estás seguro de eliminar la cuenta ${account_alias} de ${service}?`)) return;

        UI.showLoading();
        try {
            await API.execute('system.delete_credential', { service, account_alias });
            UI.toast('Cuenta eliminada', 'success');
            await this.loadAllCredentials();
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async copyWebhookDetails(service) {
        const url = document.getElementById(`url-${service}`).value;
        const token = document.getElementById(`token-${service}`).value;
        await navigator.clipboard.writeText(`URL: ${url}\nVerify Token: ${token}`);
        UI.toast(`Detalles de ${service} copiados`, 'success');
    },

    async loadProfileData() {
        try {
            const data = await API.execute('core.get_profile', {});
            const info = data.data;

            UI.render('profile-info', `
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span class="text-muted">Negocio:</span>
                    <span style="font-weight: 600;">${info.business_name}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span class="text-muted">Usuario:</span>
                    <span style="font-weight: 600;">${info.username}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span class="text-muted">Plan:</span>
                    <span style="color: var(--color-primary); font-weight: 700; text-transform: uppercase;">${info.plan}</span>
                </div>
            `);
        } catch (e) {
            UI.render('profile-info', `<p class="text-error" style="color: var(--color-error);">Error cargando perfil: ${e.message}</p>`);
        }
    },

    async loadEmployees() {
        try {
            const res = await API.execute('user.list', {});
            const users = res.data;

            if (users.length === 0) {
                UI.render('employees-list', `<p class="text-muted">No hay empleados registrados.</p>`);
                return;
            }

            const listHtml = users.map(u => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: var(--color-bg); border-radius: var(--radius-sm); border: 1px solid var(--color-border);">
                    <div>
                        <div style="font-size: 14px; font-weight: 600;">${u.email}</div>
                        <div style="font-size: 11px; color: var(--color-text-muted);">${u.role}</div>
                    </div>
                    <button class="btn" style="padding: 4px 8px; font-size: 10px; background: white; border: 1px solid var(--color-border); color: var(--color-text-main);" onclick="Profile.removeUser('${u.id}')">Quitar</button>
                </div>
            `).join('');

            UI.render('employees-list', listHtml);
        } catch (e) {
            UI.render('employees-list', `<p class="text-error" style="color: var(--color-error);">Error cargando empleados: ${e.message}</p>`);
        }
    },

    showInviteForm() {
        const html = `
            <div class="modal-overlay" style="position: fixed; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: var(--spacing-lg);">
                <div style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); width: 100%; max-width: 350px; border: 1px solid var(--color-border);">
                    <h3>Invitar Empleado</h3>
                    <input type="email" id="inv-email" class="input-field" placeholder="Email">
                    <input type="password" id="inv-pass" class="input-field" placeholder="Contraseña Temporal">
                    <select id="inv-role" class="input-field">
                        <option value="employee">Empleado</option>
                        <option value="admin">Administrador</option>
                    </select>
                    <div style="display: flex; gap: var(--spacing-sm); margin-top: var(--spacing-md);">
                        <button class="btn" style="flex: 1; background: var(--color-border); color: var(--color-text-main);" onclick="Profile.closeInviteForm()">Cancelar</button>
                        <button class="btn btn-primary" style="flex: 1;" onclick="Profile.submitInvite()">Invitar</button>
                    </div>
                </div>
            </div>
        `;
        UI.render('app-root', document.getElementById('app-root').innerHTML + html);
    },

    closeInviteForm() {
        const modal = document.querySelector('.modal-overlay');
        if (modal) modal.remove();
    },

    async submitInvite() {
        const email = document.getElementById('inv-email').value;
        const pass = document.getElementById('inv-pass').value;
        const role = document.getElementById('inv-role').value;

        if (!email || !pass) return UI.toast('Completa los datos', 'error');

        UI.showLoading();
        try {
            await API.execute('user.invite_employee', { username: email, password: pass, role: role });
            UI.toast('Empleado invitado con éxito', 'success');
            this.closeInviteForm();
            await this.loadEmployees();
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async removeUser(userId) {
        UI.toast('Esta función requiere el comando user.delete en el backend', 'warning');
    }
};

window.Profile = Profile;
