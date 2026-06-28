/**
 * OMNICORE BOT MANAGER MODULE
 * Gestión profesional de Motores de Bot (Principal y Secundarios).
 */

window.BotManager = {
    // Definición de funciones disponibles para los bots
    FUNCTIONS: {
        manage_stock: "📦 Consultar Stock",
        process_sales: "🛒 Realizar Venta",
        generate_payments: "💳 Generar Cobro",
        customer_support: "🎧 Soporte y Ayuda",
        bot_orchestration: "🤖 Cambiar de Bot"
    },

    async render() {
        UI.render('app-content', `
            <div class="module-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-lg);">
                    <h3>🤖 Gestión de Motores de Bot</h3>
                    <button class="btn btn-outline" onclick="BotManager.showCreateBotForm()">+ Nuevo Bot</button>
                </div>

                <!-- Sección 1: Definición de Motores (Lógica y Permisos) -->
                <div class="section-container">
                    <h4>📦 Motores de Bot Disponibles</h4>
                    <div id="bots-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: var(--spacing-md); margin-bottom: var(--spacing-xl);">
                        Cargando motores...
                    </div>
                </div>

                <!-- Sección 2: Asignación a Números (Canales) -->
                <div class="section-container">
                    <h4>📱 Asignación a Números de WhatsApp</h4>
                    <div id="assignments-list" style="display: flex; flex-direction: column; gap: var(--spacing-md);">
                        Cargando asignaciones...
                    </div>
                </div>

                <!-- Formulario: Crear Bot -->
                <div id="create-bot-form" style="display: none; margin-top: var(--spacing-lg); padding: var(--spacing-md); background: var(--color-bg-alt); border: 1px solid var(--color-border); border-radius: var(--radius-md);">
                    <h4>Crear Nuevo Bot (Empleado Digital)</h4>
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-sm); max-width: 500px;">
                        <label>Nombre del Bot</label>
                        <input type="text" id="new-bot-name" class="input-field" placeholder="Ej: Asistente de Ventas, Bot de Stock...">
                        
                        <label style="margin-top: 10px; font-weight: bold;">Habilidades / Funciones:</label>
                        <div id="bot-functions-selector" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: white; padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--color-border);">
                            ${Object.entries(this.FUNCTIONS).map(([key, label]) => `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px;">
                                    <input type="checkbox" class="bot-func-checkbox" value="${key}"> ${label}
                                </label>
                            `).join('')}
                        </div>

                        <div style="display: flex; gap: 10px; margin-top: 15px;">
                            <button class="btn btn-primary" onclick="BotManager.createBot()">Crear Bot</button>
                            <button class="btn" onclick="BotManager.hideCreateBotForm()">Cancelar</button>
                        </div>
                    </div>
                </div>
            </div>
            <style>
                .section-container {
                    margin-bottom: var(--spacing-xl);
                    padding: var(--spacing-md);
                    background: var(--color-bg-alt);
                    border-radius: var(--radius-md);
                    border: 1px solid var(--color-border);
                }
                .bot-card {
                    background: white;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    padding: var(--spacing-md);
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-sm);
                }
                .bot-card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
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
                    font-size: 14px;
                }
                .capability-row:last-child { border-bottom: none; }
                .assignment-row {
                    background: white;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    padding: var(--spacing-md);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: var(--spacing-md);
                }
                .assignment-info {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
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
        await this.loadAssignments();
    },

    async loadBots() {
        try {
            const res = await API.execute('bot.list', {});
            const bots = res.data || [];
            
            if (bots.length === 0) {
                UI.render('bots-list', '<p class="text-muted">No hay motores de bot configurados.</p>');
                return;
            }

            const html = bots.map(bot => {
                const caps = bot.capabilities || {};
                const activeFuncs = caps.functions || [];
                
                return `
                    <div class="bot-card">
                        <div class="bot-card-header">
                            <div>
                                <strong>${bot.name}</strong>
                                <small class="text-muted">ID: ${bot.id}</small>
                            </div>
                        </div>
                        <div class="capabilities-list">
                            ${Object.entries(this.FUNCTIONS).map(([key, label]) => {
                                const isActive = activeFuncs.includes(key);
                                return `
                                    <div class="capability-row">
                                        <span>${label}</span>
                                        <label class="switch">
                                            <input type="checkbox" ${isActive ? 'checked' : ''} 
                                                   onchange="BotManager.toggleCapability('${bot.id}', '${key}', this.checked)">
                                            <span class="slider"></span>
                                        </label>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;
            }).join('');

            UI.render('bots-list', html);
        } catch (e) {
            UI.toast(`Error cargando bots: ${e.message}`, 'error');
        }
    },

    async toggleCapability(botId, funcKey, value) {
        try {
            UI.showLoading();
            // Obtenemos el bot actual para preservar otras capacidades
            const res = await API.execute('bot.list', {});
            const bot = (res.data || []).find(b => b.id === botId);
            
            if (!bot) throw new Error('Bot no encontrado');

            const caps = bot.capabilities || {};
            const functions = caps.functions || [];
            
            if (value && !functions.includes(funcKey)) {
                functions.push(funcKey);
            } else if (!value && functions.includes(funcKey)) {
                functions = functions.filter(f => f !== funcKey);
            }
            
            const updatedCaps = { ...caps, functions };
            
            await API.execute('bot.update_capabilities', { 
                bot_profile_id: botId, 
                capabilities: updatedCaps 
            });

            UI.toast(`Habilidad ${this.FUNCTIONS[funcKey] || funcKey} actualizada`, 'success');
        } catch (e) {
            UI.toast(`Error actualizando habilidad: ${e.message}`, 'error');
            await this.loadBots(); 
        } finally {
            UI.hideLoading();
        }
    },

    async loadAssignments() {
        try {
            const credRes = await API.execute('whatsapp.list_credentials', {});
            const credentials = credRes.data || [];
            
            const botRes = await API.execute('bot.list', {});
            const bots = botRes.data || [];

            if (credentials.length === 0) {
                UI.render('assignments-list', '<p class="text-muted">No hay credenciales de WhatsApp configuradas.</p>');
                return;
            }

            const html = credentials.map(cred => {
                const meta = typeof cred.metadata === 'string' ? JSON.parse(cred.metadata) : cred.metadata;
                const phoneId = meta.phone_number_id || 'S/N';
                
                return `
                    <div class="assignment-row">
                        <div class="assignment-info">
                            <strong>${cred.account_alias}</strong>
                            <small class="text-muted">Phone ID: ${phoneId}</small>
                        </div>
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <select class="input-field" style="width: 150px;" onchange="BotManager.assignBot('${cred.credential_id}', this.value)">
                                <option value="">Seleccionar Bot</option>
                                ${bots.map(b => `<option value="${b.id}" ${cred.bot_profile_id === b.id ? 'selected' : ''}>${b.name}</option>`).join('')}
                            </select>
                            <label class="switch">
                                <input type="checkbox" onchange="BotManager.toggleBotStatus('${cred.credential_id}', this.checked)">
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                `;
            }).join('');

            UI.render('assignments-list', html);
        } catch (e) {
            UI.toast(`Error cargando asignaciones: ${e.message}`, 'error');
        }
    },

    async assignBot(credentialId, botId) {
        try {
            UI.showLoading();
            await API.execute('bot.assign', { 
                credential_id: credentialId, 
                bot_profile_id: botId 
            });
            UI.toast(`Bot asignado correctamente`, 'success');
        } catch (e) {
            UI.toast(`Error asignando bot: ${e.message}`, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async toggleBotStatus(credentialId, isActive) {
        try {
            UI.showLoading();
            const res = await API.execute('whatsapp.list_credentials', {});
            const cred = (res.data || []).find(c => c.credential_id === credentialId);
            
            if (!cred) throw new Error('Credencial no encontrada');
            
            const meta = typeof cred.metadata === 'string' ? JSON.parse(cred.metadata) : cred.metadata;
            const phone = meta.phone_number || 'unknown'; 

            await API.execute('whatsapp.toggle_bot', { 
                phone_number: phone, 
                is_active: isActive 
            });
            UI.toast(`Estado del bot actualizado`, 'success');
        } catch (e) {
            UI.toast(`Error actualizando estado: ${e.message}`, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    showCreateBotForm() {
        document.getElementById('create-bot-form').style.display = 'block';
    },

    hideCreateBotForm() {
        document.getElementById('create-bot-form').style.display = 'none';
    },

    async createBot() {
        const name = document.getElementById('new-bot-name').value;
        if (!name) return UI.toast('El nombre es requerido', 'error');

        const functions = [];
        document.querySelectorAll('.bot-func-checkbox:checked').forEach(checkbox => {
            functions.push(checkbox.value);
        });

        try {
            UI.showLoading();
            await API.execute('bot.create', { name, functions });
            UI.toast('Empleado Digital creado exitosamente', 'success');
            this.hideCreateBotForm();
            await this.loadBots();
            await this.loadAssignments();
        } catch (e) {
            UI.toast(`Error al crear bot: ${e.message}`, 'error');
        } finally {
            UI.hideLoading();
        }
    }
};
