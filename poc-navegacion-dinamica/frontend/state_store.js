/**
 * StateStore
 * Almacena el manifiesto de navegación dinámicamente.
 */
class StateStore {
    constructor() {
        this.state = {
            manifest: null,
            activeModule: null,
            activePanel: null
        };
        this.listeners = [];
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    getState() {
        return this.state;
    }

    subscribe(listener) {
        this.listeners.push(listener);
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }
}

const store = new StateStore();
