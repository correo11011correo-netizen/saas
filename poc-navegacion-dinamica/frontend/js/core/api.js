/**
 * API Client
 * Implementa el patrón Dispatcher (/api/execute)
 */
const API = {
    baseUrl: 'http://localhost:8080',

    async execute(command, params = {}) {
        try {
            const response = await fetch(`${this.baseUrl}/api/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command: command,
                    params: params
                })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Error en el servidor');
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${command}]:`, error);
            throw error;
        }
    }
};
