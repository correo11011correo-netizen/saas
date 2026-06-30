/**
 * OMNICORE MERCADO PAGO MODULE
 * Configuración y monitoreo de pagos automáticos.
 */

const Mercadopago = {
    config: {
        dock: [
            { id: 'mercadopago', icon: 'sales', label: 'Pagos' },
            { id: 'sales', icon: 'sales', label: 'Ventas' },
            { id: 'hub', icon: 'home', label: 'Hub' }
        ],
        panels: [
            { id: 'api_logs', icon: 'settings', label: 'Logs de API' },
            { id: 'refunds', icon: 'settings', label: 'Reembolsos' }
        ]
    },

    async render() {
        UI.render('app-content', `
            <div class="payments-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <header style="display: flex; align-items: center; gap: 10px;">
                    <h3>${Icons.sales} Mercado Pago</h3>
                </header>

                <section class="config-card" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <h4 style="margin-bottom: var(--spacing-md);">Configuración de API</h4>
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-sm);">
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: var(--color-bg); border-radius: var(--radius-sm);">
                            <span>AccessToken</span>
                            <button class="btn" style="padding: 4px 8px; font-size: 10px; background: var(--color-primary); color: white;" onclick="Mercadopago.updateKey()">Actualizar</button>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: var(--color-bg); border-radius: var(--radius-sm);">
                            <span>Webhook URL</span>
                            <span class="text-muted" style="font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 150px;">https://api.../hooks</span>
                        </div>
                    </div>
                </section>

                <section class="status-card" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <h4 style="margin-bottom: var(--spacing-md);">Estado del Servicio</h4>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 10px; height: 10px; background: var(--color-success); border-radius: 50%;"></div>
                        <span style="font-weight: 600;">Conectado</span>
                    </div>
                    <p class="text-muted" style="font-size: 12px; margin-top: 8px;">Sincronización de pagos en tiempo real activa.</p>
                </section>
            </div>
        `);
    },

    updateKey() {
        UI.toast('Funcionalidad de actualización de keys en desarrollo...', 'info');
    }
};

window.Mercadopago = Mercadopago;
