/**
 * OMNICORE SYNC ENGINE
 * Gestor de cola de comandos y sincronización de datos.
 * Implementa el patrón 'Outbox' para garantizar la continuidad del negocio offline.
 */

window.SyncEngine = {
    isOnline: navigator.onLine,
    isSyncing: false,
    retryInterval: 5000, // 5 segundos

    async init() {
        window.addEventListener('online', () => this.handleOnlineStatus(true));
        window.addEventListener('offline', () => this.handleOnlineStatus(false));
        this.isOnline = navigator.onLine;

        // Iniciar ciclo de verificación de cola
        this.startSyncLoop();
        console.log('🚀 SyncEngine Initialized');
    },

    async handleOnlineStatus(online) {
        this.isOnline = online;
        UI.toast(online ? 'Conexión restablecida. Sincronizando...' : 'Modo offline activado', online ? 'success' : 'warning');
        if (online) {
            await this.processQueue();
        }
    },

    async enqueue(command, params) {
        const entry = {
            command,
            params,
            timestamp: Date.now(),
            attempts: 0,
            status: 'pending'
        };
        await LocalStore.save('sync_queue', entry);
        console.log(`📥 Command queued: ${command}`);
        return { queued: true, id: entry.id };
    },

    async processQueue() {
        if (!this.isOnline || this.isSyncing) return;

        const queue = await LocalStore.getAll('sync_queue');
        if (queue.length === 0) return;

        this.isSyncing = true;
        console.log(`🔄 Syncing ${queue.length} pending commands...`);

        // Procesamos secuencialmente para mantener la integridad (ej. Venta -> Stock)
        for (const item of queue) {
            try {
                // Intentamos ejecutar el comando directamente via API
                // Usamos executeDirect para saltar el interceptor de cola y evitar bucles infinitos
                await API.executeDirect(item.command, item.params);

                // Si tiene éxito, eliminamos de la cola
                await LocalStore.delete('sync_queue', item.id);
                console.log(`✅ Synced: ${item.command}`);

                // Notificar al sistema de tiempo real si es necesario
                if (window.Realtime) {
                    await window.Realtime.notifySync(item.command);
                }
            } catch (e) {
                console.error(`❌ Sync failed for ${item.command}:`, e);
                // Incrementamos intentos. Si falla mucho, podemos marcarlo como 'error' para revisión manual
                item.attempts++;
                await LocalStore.save('sync_queue', item);

                if (item.attempts > 5) {
                    console.error(`🛑 Command ${item.command} failed too many times. Stopping queue.`);
                    break;
                }
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
