/**
 * OMNICORE LOCAL STORAGE ENGINE
 * Capa de persistencia local utilizando IndexedDB para soporte de grandes volúmenes de datos
 * y persistencia offline real.
 */

window.LocalStore = {
    dbName: 'OmniCore_LocalDB',
    version: 1,
    db: null,

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                // Cola de comandos pendientes de sincronización
                if (!db.objectStoreNames.contains('sync_queue')) {
                    db.createObjectStore('sync_queue', { keyPath: 'id', autoIncrement: true });
                }
                // Caché de productos para ventas offline
                if (!db.objectStoreNames.contains('products_cache')) {
                    db.createObjectStore('products_cache', { keyPath: 'id' });
                }
                // Caché de configuración y manifiesto SDUI
                if (!db.objectStoreNames.contains('app_config')) {
                    db.createObjectStore('app_config', { keyPath: 'key' });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };

            request.onerror = (event) => reject('IndexedDB error: ' + event.target.errorCode);
        });
    },

    async save(storeName, data) {
        const tx = this.db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        return new Promise((resolve) => {
            const request = store.put(data);
            request.onsuccess = () => resolve(true);
        });
    },

    async getAll(storeName) {
        const tx = this.db.transaction(storeName, 'readonly');
        const store = tx.objectStore(storeName);
        return new Promise((resolve) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
        });
    },

    async get(storeName, key) {
        const tx = this.db.transaction(storeName, 'readonly');
        const store = tx.objectStore(storeName);
        return new Promise((resolve) => {
            const request = store.get(key);
            request.onsuccess = () => resolve(request.result);
        });
    },

    async delete(storeName, key) {
        const tx = this.db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        return new Promise((resolve) => {
            const request = store.delete(key);
            request.onsuccess = () => resolve(true);
        });
    },

    async clear(storeName) {
        const tx = this.db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        return new Promise((resolve) => {
            const request = store.clear();
            request.onsuccess = () => resolve(true);
        });
    }
};
