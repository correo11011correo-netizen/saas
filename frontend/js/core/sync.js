/**
 * OMNICORE SYNC MANAGER
 * Gestiona la cola de comandos offline y la sincronización automática.
 */

const SyncManager = {
    QUEUE_KEY: 'omnicore_sync_queue',

    /**
     * Añade un comando a la cola de espera.
     */
    enqueue(command, params) {
        const queue = this.getQueue();
        queue.push({
            id: crypto.randomUUID(),
            command,
            params,
            timestamp: Date.now()
        });
        this.saveQueue(queue);
        UI.toast('Modo offline: Acción en cola', 'warning');
    },

    getQueue() {
        const data = localStorage.getItem(this.QUEUE_KEY);
        return data ? JSON.parse(data) : [];
    },

    saveQueue(queue) {
        localStorage.setItem(this.QUEUE_KEY, JSON.stringify(queue));
    },

    /**
     * Intenta procesar todos los comandos en cola.
     */
    async processQueue() {
        const queue = this.getQueue();
        if (queue.length === 0) return;

        UI.toast(`Sincronizando ${queue.length} acciones...`, 'info');

        const remainingQueue = [];
        for (const item of queue) {
            try {
                // Ejecutamos el comando originalmente planeado
                await API.executeDirect(item.command, item.params);
            } catch (error) {
                console.error(`[Sync Error] Failed to sync ${item.command}:`, error);
                // Si falla por algo que no es conexión, podríamos decidir no re-intentarlo
                // Pero por defecto lo mantenemos en cola si el error es de red
                remainingQueue.push(item);
            }
        }

        this.saveQueue(remainingQueue);
        if (remainingQueue.length === 0) {
            UI.toast('Sincronización completada', 'success');
        } else {
            UI.toast('Algunas acciones no pudieron sincronizarse', 'error');
        }
    }
};

window.SyncManager = SyncManager;
