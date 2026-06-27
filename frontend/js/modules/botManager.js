/**
 * OMNICORE BOT MANAGER MODULE
 * Gestión de perfiles y capacidades de bots especializados.
 */

window.BotManager = {
    async render() {
        UI.render('app-content', `
            <div class="module-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-lg);">
                    <h3>🤖 Gestión de Bots Especializados</h3>
                    <button class="btn btn-outline" onclick="BotManager.showCreateForm()">+ Nuevo Bot</button>
                </div>

                <div id="bots-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--spacing-md);">
                    Cargando bots...
                </div>

                <div id="create-bot-form" style="display: none; margin-top: var(--spacing-lg); padding: var(--spacing-md); background: var(--color-bg-alt); border: 1px solid var(--color-border); border-radius: var(--radius-md);">
                    <h4>Crear Nuevo Bot</h4>
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-sm); max-width: 400px;">
                        <input type="text" id="new-bot-name" class="input-field" placeholder="Nombre del Bot (ej: Asistente Ventas)">
                        <input type="text" id="new-bot-alias" class="input-field" placeholder="Alias único (ej: ventas_bot)">
                        <div style="display: flex; gap: 10px; margin-top: 10px;">
                            <button class="btn btn-primary" onclick="BotManager.createBot()">Crear Bot</button>
                            <button class="btn" onclick="BotManager.hideCreateForm()">Cancelar</button>
                        </div>
                    </div>
                </div>
            </div>
            <style>
                .bot-card {
                    background: white;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    padding: var(--spacing-md);
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-sm);
                    transition: transform 0.2s;
                }
                .bot-card:hover { transform: translateY(-2px); }
                .bot-card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    border-bottom: 1px solid var(--color-border);
                    padding-bottom: var(--spacing-sm);
                    margin-bottom: var(--spacing-sm);
                }
                .capability-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 0;
                    border-bottom: 1px dotted var(--color-border);
                }
                .capability-row:last-child { border-bottom: none; }
                .switch {
                    position: relative;
                    display: inline-block;
                    width: 40px;
                    height: 20px;
                }
                .switch input { opacity: 0; width: 0; height: 0; }
                .slider {
                    position: absolute;
                    cursor: pointer;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background-color: #ccc;
                    transition: .4s;
                    border-radius: 20px;
                }
                .slider:before {
                    position: absolute;
                    content: "";
                    height: 14px; width: 14px;
                    left: 3px; bottom: 3px;
                    background-color: white;
                    transition: .4s;
                    border-radius: 50%;
                }
                input:checked + .slider { background-color: var(--color-primary); }
                input:checked + .slider:before { transform: translateX(20px); }
            </style>
        `);
        await this.loadBots();
    },

    async loadBots() {
        try {
            const res = await API.execute('bot.list', {});
            const bots = res.data || [];
            
            if (bots.length === 0) {
                UI.render('bots-grid', '<p class="text-muted">No hay bots configurados. Crea uno para empezar.</p>');
                return;
            }

            const html = bots.map(bot => {
                const caps = bot.capabilities || {};
                return `
                    <div class="bot-card">
                        <div class="bot-card-header">
                            <div>
                                <strong style="display: block;">${bot.name}</strong>
                                <small class="text-muted">${bot.account_alias}</small>
                            </div>
                            <span style="font-size: 12px; padding: 2px 6px; border-radius: 10px; background: ${bot.is_active ? '#dcfce7' : '#fee2e2'}; color: ${bot.is_active ? '#166534' : '#991b1b'};">
                                ${bot.is_active ? 'Activo' : 'Inactivo'}
                            </span>
                        </div>
                        
                        <div class="capabilities-list">
                            <div class="capability-row">
                                <span>📦 Acceso a Stock</span>
                                <label class="switch">
                                    <input type="checkbox" ${caps.can_manage_stock ? 'checked' : ''} 
                                           onchange="BotManager.toggleCapability('${bot.account_alias}', 'can_manage_stock', this.checked)">
                                    <span class="slider"></span>
                                </label>
                            </div>
                            <div class="capability-row">
                                <span>🛒 Gestión de Ventas</span>
                                <label class="switch">
                                    <input type="checkbox" ${caps.can_sell ? 'checked' : ''} 
                                           onchange="BotManager.toggleCapability('${bot.account_alias}', 'can_sell', this.checked)">
                                    <span class="slider"></span>
                                </label>
                            </div>
                            <div class="capability-row">
                                <span>💳 Pagos (Link / QR / MP)</span>
                                <label class="switch">
                                    <input type="checkbox" ${caps.can_process_payments ? 'checked' : ''} 
                                           onchange="BotManager.toggleCapability('${bot.account_alias}', 'can_process_payments', this.checked)">
                                    <span class="slider"></span>
                                </label>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            UI.render('bots-grid', html);
        } catch (e) {
            UI.toast(`Error cargando bots: ${e.message}`, 'error');
        }
    },

    async toggleCapability(alias, capKey, value) {
        try {
            UI.showLoading();
            // Primero obtenemos el estado actual para no sobrescribir otras capacidades
            const res = await API.execute('bot.list', {});
            const bot = (res.data || []).find(b => b.account_alias === alias);
            
            if (!bot) throw new Error('Bot no encontrado');

            const updatedCaps = { ...bot.capabilities, [capKey]: value };
            
            await API.execute('bot.update_capabilities', { 
                account_alias: alias, 
                capabilities: updatedCaps 
            });

            UI.toast(`Capacidad ${capKey} actualizada`, 'success');
        } catch (e) {
            UI.toast(`Error actualizando capacidad: ${e.message}`, 'error');
            await this.loadBots(); // Reset switches to previous state
        } finally {
            UI.hideLoading();
        }
    },

    showCreateForm() {
        document.getElementById('create-bot-form').style.display = 'block';
    },

    hideCreateForm() {
        document.getElementById('create-bot-form').style.display = 'none';
    },

    async createBot() {
        const name = document.getElementById('new-bot-name').value;
        const alias = document.getElementById('new-bot-alias').value;
        
        if (!name || !alias) return UI.toast('Nombre y Alias son requeridos', 'error');

        try {
            UI.showLoading();
            await API.execute('bot.create', { name, account_alias: alias });
            UI.toast('Bot creado exitosamente', 'success');
            this.hideCreateForm();
            await this.loadBots();
        } catch (e) {
            UI.toast(`Error al crear bot: ${e.message}`, 'error');
        } finally {
            UI.hideLoading();
        }
    }
};
