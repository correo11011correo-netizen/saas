/**
 * OMNICORE WHATSAPP MODULE
 * Gestión de mensajería y bots de ventas.
 */

window.Whatsapp = {
    defaultPanel: 'messages',
    pollingInterval: null,
    listPollingInterval: null,
    currentChat: null,
    messageQueue: [], // Queue for pending messages
    config: {
        dock: [
            { id: 'messages', icon: 'whatsapp', label: 'Mensajes' },
            { id: 'bot_studio', icon: 'settings', label: 'Bot Studio' },
            { id: 'api_keys', icon: 'key', label: 'API Keys' }
        ]
    },

    formatTime(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    getStatusIcon(status, senderType) {
        // Messages sent by the app user (agent) are marked as 'bot' in the DB
        if (!status) return ''; // Manejar ausencia de status
        if (senderType === 'bot') {
            switch (status) {
                case 'sent': return '<span style="font-size: 12px; margin-left: 4px; opacity: 0.6;">✓</span>';
                case 'delivered': return '<span style="font-size: 12px; margin-left: 4px; opacity: 0.6;">✓✓</span>';
                case 'read': return '<span style="font-size: 12px; margin-left: 4px; color: var(--color-primary);">✓✓</span>';
                default: return '<span style="font-size: 12px; margin-left: 4px; opacity: 0.5;">🕒</span>';
            }
        }
        return '';
    },

    async render(panelId) {
        this.stopPolling();
        let content = '';
        if (panelId === 'bot_studio') {
            content = await this.renderBotStudio();
        } else if (panelId === 'messages') {
            content = await this.renderMessages();
        } else if (panelId === 'api_keys') {
            content = `<div style="padding: var(--spacing-md);"><p>Gestión de API Keys (Ver Perfil)</p></div>`;
        } else {
            content = `<p>Panel ${panelId} en desarrollo...</p>`;
        }

        UI.render('app-content', `
            <div id="whatsapp-panel" class="module-panel">
                ${content}
            </div>
        `);

        if (panelId === 'bot_studio') {
            await this.loadNodes();
            await this.loadSettings();
        } else if (panelId === 'messages') {
            await this.loadConversations();
            this.startListPolling();
        }
    },

    async renderMessages() {
        return `
            <div style="height: 100%; display: flex; flex-direction: column;">
                <div style="padding: 10px; border-bottom: 1px solid var(--color-border); font-weight: bold; display: flex; justify-content: space-between; align-items: center;">
                    <span>Chats</span>
                    <small id="chat-sync-status" style="font-weight: normal; opacity: 0.7;">Sincronizado</small>
                </div>
                <div id="chats-list" style="flex: 1; overflow-y: auto;">Cargando chats...</div>
            </div>
        `;
    },

    async loadConversations() {
        const list = document.getElementById('chats-list');
        if (!list) return;

        try {
            const res = await API.execute('whatsapp.list_conversations', {});
            if (!res.success) {
                throw new Error(res.error || 'Error al cargar conversaciones');
            }
            const chats = res.data || [];

            const html = chats.map(c => `
                <div class="chat-item" style="padding: 15px; border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center;">
                    <div style="cursor: pointer; flex: 1;" onclick="Whatsapp.openChat('${c.phone_number}')">
                        <div style="font-weight: 600;">${c.phone_number || 'Desconocido'}</div>
                        <div style="font-size: 12px; color: var(--color-text-muted);">${c.last_message || 'Sin mensajes'}</div>
                    </div>
                    <button class="btn-icon delete-chat-btn"
                            style="color: var(--color-error); background: none; border: none; cursor: pointer; padding: 8px; z-index: 10;"
                            onclick="event.stopPropagation(); Whatsapp.deleteChat('${c.phone_number}')">
                        ${Icons.logout}
                    </button>
                </div>
            `).join('') || '<p style="padding: 15px;">No hay chats recientes.</p>';

            list.innerHTML = html;
        } catch (e) {
            console.error('Error loading conversations:', e);
            if (list) list.innerHTML = `<p style="padding: 15px; color: var(--color-error);">Error: ${e.message}</p>`;
        }
    },

    async openChat(phoneNumber) {
        this.stopPolling();
        this.currentChat = phoneNumber;
        UI.showLoading();
        try {
            await this.refreshChatMessages(phoneNumber);
            this.startPolling(phoneNumber);
        } catch (e) {
            console.error('Open chat error:', e);
            UI.toast(`Error cargando chat: ${e.message}`, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async refreshChatMessages(phoneNumber) {
        try {
            const res = await API.execute('whatsapp.get_messages', { phone_number: phoneNumber });

            if (!res.success) {
                throw new Error(res.error || 'Error al obtener mensajes');
            }

            const { messages = [], is_bot_active } = res.data || {};

            if (!document.getElementById('messages-container')) {
                UI.render('app-content', `
                    <div style="height: 100vh; display: flex; flex-direction: column;">
                        <div style="padding: 10px; border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center;">
                            <button class="btn" onclick="Whatsapp.render('messages')">← Volver</button>
                            <strong>${phoneNumber}</strong>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 12px;">Bot:</span>
                                <input type="checkbox" id="bot-status-check" ${is_bot_active ? 'checked' : ''} onchange="Whatsapp.toggleBotStatus('${phoneNumber}', this.checked)">
                            </div>
                        </div>
                        <div id="messages-container" style="flex: 1; overflow-y: auto; padding: 10px; background: var(--color-bg);">
                        </div>
                        <div style="padding: 10px; border-top: 1px solid var(--color-border); display: flex; gap: 5px;">
                            <input type="text" id="msg-input" class="input-field" placeholder="Escribe un mensaje..." style="margin-bottom: 0;">
                            <button class="btn btn-primary" onclick="Whatsapp.sendMessage('${phoneNumber}')">Enviar</button>
                        </div>
                    </div>
                `);
            }

            const container = document.getElementById('messages-container');
            if (container) {
                const allMessages = Array.isArray(messages) ? [...messages] : [];
                this.messageQueue
                    .filter(m => m.to === phoneNumber)
                    .forEach(m => allMessages.push({
                        sender_type: 'bot',
                        message: m.body,
                        status: m.status,
                        created_at: m.timestamp
                    }));

                const html = allMessages.map(m => `
                    <div style="margin-bottom: 10px; text-align: ${m.sender_type === 'bot' ? 'right' : 'left'};">
                        <div style="display: inline-block; padding: 8px 12px; border-radius: 10px; background: ${m.sender_type === 'bot' ? 'var(--color-primary)' : 'white'}; color: ${m.sender_type === 'bot' ? 'white' : 'black'}; box-shadow: 0 1px 2px rgba(0,0,0,0.1); position: relative; max-width: 80%;">
                            <div style="font-size: 14px; margin-bottom: 4px;">${m.message}</div>
                            <div style="display: flex; justify-content: flex-end; align-items: center; gap: 4px; font-size: 10px; opacity: 0.8; margin-top: 4px;">
                                <span>${this.formatTime(m.created_at)}</span>
                                ${this.getStatusIcon(m.status, m.sender_type)}
                            </div>
                        </div>
                    </div>
                `).join('');

                if (container.innerHTML !== html) {
                    container.innerHTML = html;
                    container.scrollTop = container.scrollHeight;
                }
            }

            const check = document.getElementById('bot-status-check');
            if (check) check.checked = is_bot_active;

        } catch (e) {
            console.error('Chat refresh error:', e);
            // Only throw if we are in the initial openChat call to show the toast
            if (this.currentChat === phoneNumber && !document.getElementById('messages-container')) {
                throw e;
            }
        }
    },

    startPolling(phoneNumber) {
        this.pollingInterval = setInterval(() => {
            this.refreshChatMessages(phoneNumber);
        }, 3000);
    },

    startListPolling() {
        this.listPollingInterval = setInterval(() => {
            this.loadConversations();
        }, 5000);
    },

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        if (this.listPollingInterval) {
            clearInterval(this.listPollingInterval);
            this.listPollingInterval = null;
        }
    },

    async toggleBotStatus(phoneNumber, isActive) {
        try {
            await API.execute('whatsapp.toggle_bot', { phone_number: phoneNumber, is_active: isActive });
            UI.toast(`Bot ${isActive ? 'activado' : 'desactivado'}`, 'success');
        } catch (e) {
            UI.toast(e.message, 'error');
        }
    },

    async sendMessage(phoneNumber) {
        const input = document.getElementById('msg-input');
        const body = input.value.trim();
        if (!body) return;

        const msgId = Date.now().toString();
        const message = {
            id: msgId,
            to: phoneNumber,
            body: body,
            timestamp: new Date().toISOString(),
            status: 'pending'
        };

        this.messageQueue.push(message);
        input.value = '';
        await this.refreshChatMessages(phoneNumber);
        this.processQueue();
    },

    async processQueue() {
        if (this.messageQueue.length === 0) return;

        for (let i = 0; i < this.messageQueue.length; i++) {
            const msg = this.messageQueue[i];
            if (msg.status === 'sending' || msg.status === 'error') continue;

            msg.status = 'sending';
            try {
                await API.execute('whatsapp.send_text', {
                    to: msg.to,
                    body: msg.body,
                    account_alias: 'Principal'
                });
                this.messageQueue = this.messageQueue.filter(m => m.id !== msg.id);
                if (this.currentChat === msg.to) {
                    await this.refreshChatMessages(msg.to);
                }
            } catch (e) {
                console.error(`Failed to send message ${msg.id}:`, e);
                msg.status = 'error';
                UI.toast(`Error enviando mensaje. Reintentando...`, 'error');
            }
        }
    },

    async deleteChat(phoneNumber) {
        if (!confirm(`¿Eliminar conversación con ${phoneNumber}?`)) return;
        try {
            await API.execute('whatsapp.delete_conversation', { phone_number: phoneNumber });
            UI.toast('Chat eliminado', 'success');
            this.loadConversations();
        } catch (e) {
            UI.toast('El chat no puede ser eliminado automáticamente, contácte a soporte', 'info');
        }
    },

    async renderBotStudio() {
        return `
            <div style="padding: var(--spacing-md); display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <section>
                    <h3>⚙️ Configuración Global (Sectores)</h3>
                    <div style="background: var(--color-bg-alt); padding: var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-border); display: grid; gap: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <strong>Estado del Bot</strong>
                            <input type="checkbox" id="bot-global-active" onchange="Whatsapp.updateSettings({is_global_active: this.checked})">
                        </div>
                        <label>Nombre del Bot</label>
                        <input type="text" id="bot-name" class="input-field" onblur="Whatsapp.updateSettings({bot_name: this.value})">

                        <label>Mensaje de Bienvenida (Sector Bienvenida)</label>
                        <textarea id="bot-welcome" class="input-field" rows="3" onblur="Whatsapp.updateSettings({welcome_message: this.value})"></textarea>

                        <label>Mensaje de Despedida (Sector Despedida)</label>
                        <textarea id="bot-farewell" class="input-field" rows="2" onblur="Whatsapp.updateSettings({farewell_message: this.value})"></textarea>

                        <label>Mensaje de Derivación (Sector Humano)</label>
                        <textarea id="bot-handoff" class="input-field" rows="2" onblur="Whatsapp.updateSettings({handoff_message: this.value})"></textarea>

                        <label>Email de Soporte</label>
                        <input type="email" id="bot-email" class="input-field" onblur="Whatsapp.updateSettings({support_email: this.value})"></textarea>
                    </div>
                </section>

                <section>
                    <h3>🛠️ Flujo de Nodos</h3>
                    <div id="nodes-list" style="margin-bottom: var(--spacing-md);">Cargando nodos...</div>
                    <div style="border: 1px solid var(--color-border); padding: var(--spacing-md); border-radius: var(--radius-md); background: var(--color-bg-alt);">
                        <h4>Nuevo Nodo Interactivo</h4>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            <input type="text" id="new-node-name" class="input-field" placeholder="Nombre del nodo (ej: productos)">
                            <textarea id="new-node-prompt" class="input-field" placeholder="Mensaje que verá el cliente"></textarea>
                            <button class="btn btn-primary" onclick="Whatsapp.saveNode()">Guardar Nodo</button>
                        </div>
                    </div>
                </section>
            </div>
        `;
    },

    async loadSettings() {
        try {
            const res = await API.execute('bot.settings.get', {});
            const s = res.data;
            document.getElementById('bot-global-active').checked = s.is_global_active;
            document.getElementById('bot-name').value = s.bot_name || '';
            document.getElementById('bot-welcome').value = s.welcome_message || '';
            document.getElementById('bot-farewell').value = s.farewell_message || '';
            document.getElementById('bot-handoff').value = s.handoff_message || '';
            document.getElementById('bot-email').value = s.support_email || '';
        } catch (e) {
            UI.toast('Error cargando configuración', 'error');
        }
    },

    async updateSettings(params) {
        try {
            await API.execute('bot.settings.update', params);
            UI.toast('Configuración actualizada', 'success');
        } catch (e) {
            UI.toast(e.message, 'error');
        }
    },

    async loadNodes() {
        try {
            const res = await API.execute('bot.node.list', {});
            const nodes = res.data || [];
            UI.render('nodes-list', nodes.map(n => `
                <div style="padding: 15px; border: 1px solid var(--color-border); margin-bottom: 10px; border-radius: var(--radius-sm); background: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <strong style="color: var(--color-primary);">${n.name}</strong>
                        <span style="font-size: 10px; opacity: 0.5;">${n.id}</span>
                    </div>
                    <div style="font-size: 13px; margin-bottom: 10px; color: var(--color-text);">${n.prompt}</div>
                    <div id="options-${n.id}" style="margin-bottom: 10px; border-left: 2px solid var(--color-border); padding-left: 10px;">Cargando opciones...</div>
                    <div style="display: flex; gap: 5px;">
                        <input type="text" id="opt-label-${n.id}" class="input-field" style="margin: 0;" placeholder="Ej: 1">
                        <button class="btn btn-sm" onclick="Whatsapp.addOption('${n.id}')">+ Opción</button>
                    </div>
                </div>
            `).join('') || '<p>No hay nodos creados.</p>');

            for (const n of nodes) {
                await this.loadOptions(n.id);
            }
        } catch (e) {
            UI.toast('Error cargando nodos', 'error');
        }
    },

    async loadOptions(nodeId) {
        try {
            const res = await API.execute('bot.option.list', { node_id: nodeId });
            const options = res.data || [];
            UI.render(`options-${nodeId}`, options.map(o => `
                <div style="font-size: 12px; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;">
                    <span style="color: var(--color-primary);">➔</span> ${o.label} <small style="opacity: 0.6;">(${o.next_node_id || o.action})</small>
                </div>
            `).join('') || '<div style="font-size: 11px; opacity: 0.5;">Sin opciones configuradas</div>');
        } catch (e) {
            UI.render(`options-${nodeId}`, 'Error cargando opciones');
        }
    },

    async saveNode() {
        const name = document.getElementById('new-node-name').value;
        const prompt = document.getElementById('new-node-prompt').value;
        if (!name || !prompt) return UI.toast('Nombre y prompt requeridos', 'error');

        try {
            await API.execute('bot.node.save', { name, prompt });
            UI.toast('Nodo guardado', 'success');
            this.loadNodes();
            document.getElementById('new-node-name').value = '';
            document.getElementById('new-node-prompt').value = '';
        } catch (e) {
            UI.toast(e.message, 'error');
        }
    },

    async addOption(nodeId) {
        const label = document.getElementById(`opt-label-${nodeId}`).value;
        if (!label) return UI.toast('Label requerido', 'error');

        try {
            await API.execute('bot.option.add', { node_id: nodeId, label });
            UI.toast('Opción añadida', 'success');
            this.loadOptions(nodeId);
            document.getElementById(`opt-label-${nodeId}`).value = '';
        } catch (e) {
            UI.toast(e.message, 'error');
        }
    }
};

window.Whatsapp = Whatsapp;
