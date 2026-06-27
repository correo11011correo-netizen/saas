/**
 * OMNICORE BOT MANAGER MODULE
 * Gestión de perfiles y capacidades de bots especializados.
 */

window.BotManager = {
    async render() {
        UI.render('app-content', `
            <div class="module-panel">
                <h3>🤖 Gestión de Bots Especializados</h3>
                <div id="bots-list">Cargando bots...</div>
                <hr>
                <h4>Crear Nuevo Bot</h4>
                <input type="text" id="new-bot-name" class="input-field" placeholder="Nombre">
                <input type="text" id="new-bot-alias" class="input-field" placeholder="Alias">
                <button class="btn btn-primary" onclick="BotManager.createBot()">Crear</button>
            </div>
        `);
        await this.loadBots();
    },

    async loadBots() {
        const res = await API.execute('bot.list', {});
        const bots = res.data || [];
        UI.render('bots-list', bots.map(b => `
            <div>${b.name} (${b.account_alias}) - Caps: ${JSON.stringify(b.capabilities)}</div>
        `).join(''));
    },

    async createBot() {
        const name = document.getElementById('new-bot-name').value;
        const alias = document.getElementById('new-bot-alias').value;
        await API.execute('bot.create', { name, account_alias: alias });
        this.loadBots();
    }
};
