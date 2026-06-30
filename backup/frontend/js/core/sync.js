/**
 * OMNICORE SYNC ENGINE
 * Gestor de cola de comandos y sincronización de datos.
 * Implementa el patrón 'Outbox' con priorización de comandos.
 */

window.SyncEngine = {
    isOnline: navigator.onLine,
    isSyncing: false,
    retryInterval: 5000,

    // Mapa de Prioridades: Menor número = Mayor prioridad
    // Asegura que la creación de entidades base ocurra antes que las transacciones
    PRIORITY_MAP: {
        'auth': 1,       // Login, tokens
        'crm': 2,        // Creación de clientes
        'stock': 3,      // Actualización de inventario
        'sales': 4,      // Ventas y cobros
        'whatsapp': 5,   // Configuración de bots
        'system': 6,     // Logs y auditoría
        'default': 10
    },

    async init() {
        window.addEventListener('online', () => this.handleOnlineStatus(true));
        window.addEventListener('offline', () => this.handleOnlineStatus(false));
        this.isOnline = navigator.onLine;
        this.startSyncLoop();
        console.log('🚀 SyncEngine Initialized with Priority System');
    },

    async handleOnlineStatus(online) {
        this.isOnline = online;
        UI.toast(online ? 'Conexión restablecida. Sincronizando...' : 'Modo offline activado', online ? 'success' : 'warning');
        if (online) await this.processQueue();
    },

    async enqueue(command, params) {
        // Determinar categoría basada en el prefijo del comando (ej: 'sales.create' -> 'sales')
        const category = command.split('.')[0];
        const priority = this.PRIORITY_MAP[category] || this.PRIORITY_MAP['default'];

        const entry = {
            command,
            params,
            category,
            priority,
            timestamp: Date.now(),
            attempts: 0,
            status: 'pending'
        };
        await LocalStore.save('sync_queue', entry);
        return { queued: true, id: entry.id };
    },

    async processQueue() {
        if (!this.isOnline || this.isSyncing) return;

        let queue = await LocalStore.getAll('sync_queue');
        if (queue.length === 0) return;

        // ORDENAMIENTO CRÍTICO:
        // 1. Por Prioridad (Ascendente: auth primero)
        // 2. Por Timestamp (Ascendente: el más antiguo primero)
        queue.sort((a, b) => a.priority - b.priority || a.timestamp - b.timestamp);

        this.isSyncing = true;
        console.log(`🔄 Syncing ${queue.length} commands in priority order...`);

        for (const item of queue) {
            try {
                await API.executeDirect(item.command, item.params);
                await LocalStore.delete('sync_queue', item.id);
            } catch (e) {
                console.error(`❌ Sync failed for ${item.command}:`, e);
                item.attempts++;
                await LocalStore.save('sync_queue', item);
                if (item.attempts > 5) break;
            }
        }
        this.isSyncing = false;
    },

    startSyncLoop() {
        setInterval(() => {
            if (this.isOnline) this.processQueue();
        }, this.retryInterval);
    }
};
