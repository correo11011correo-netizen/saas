/**
 * OMNICORE SALES & POS MODULE
 * Gestión de ventas, punto de venta y cobros.
 */

window.Sales = {
    defaultPanel: 'pos',
    config: {
        dock: [
            { id: 'pos', icon: 'cart', label: 'Ventas' },
            { id: 'reports', icon: 'chart', label: 'Reportes' }
        ]
    },
    cart: [],

    async render(panelId) {
        UI.render('app-content', `
            <div id="sales-panel" class="module-panel">
                ${panelId === 'pos' ? await this.renderPOS() : '<p>Panel en desarrollo...</p>'}
            </div>
        `);
        if (panelId === 'pos') await this.loadProducts();
    },

    async renderPOS() {
        return `
            <div class="pos-layout" style="display: flex; flex-direction: column; gap: var(--spacing-md);">
                <div class="products-section">
                    <h3>Productos</h3>
                    <div id="products-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--spacing-sm);">Cargando...</div>
                </div>
                <div class="cart-section" style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-border);">
                    <h3>Carrito</h3>
                    <div id="cart-list" style="max-height: 200px; overflow-y: auto;">Vacio</div>
                    <div id="cart-total" style="font-weight: 700; margin-top: var(--spacing-md); font-size: 1.2em;">Total: $0</div>
                    <button class="btn btn-primary" style="width: 100%; margin-top: var(--spacing-md);" onclick="Sales.checkout()">Generar Cobro</button>
                </div>
            </div>
            <style>
                @media (min-width: 768px) {
                    .pos-layout { flex-direction: row !important; }
                    .products-section { flex: 2; }
                    .cart-section { flex: 1; height: fit-content; position: sticky; top: 10px; }
                }
            </style>
        `;
    },

    async loadProducts() {
        try {
            const res = await API.execute('products.list', {});
            const products = res.data || [];
            UI.render('products-list', products.map(p => `
                <div style="padding: 10px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); cursor: pointer;" onclick="Sales.addToCart(${JSON.stringify(p).replace(/"/g, '&quot;')})">
                    <div style="font-weight: 600;">${p.name}</div>
                    <div style="font-size: 12px;">$${p.price}</div>
                </div>
            `).join(''));
        } catch (e) {
            UI.toast('Error cargando stock', 'error');
        }
    },

    addToCart(product) {
        this.cart.push(product);
        this.updateCartUI();
    },

    updateCartUI() {
        UI.render('cart-list', this.cart.map(c => `<div>${c.name} - $${c.price}</div>`).join(''));
        const total = this.cart.reduce((sum, p) => sum + parseFloat(p.price), 0);
        UI.render('cart-total', `Total: $${total.toFixed(2)}`);
    },

    async checkout() {
        if (this.cart.length === 0) return UI.toast('Carrito vacío', 'error');

        const total = this.cart.reduce((sum, p) => sum + parseFloat(p.price), 0);

        try {
            UI.showLoading();
            const res = await API.execute('sales.create', {
                items: this.cart,
                total: total,
                account_alias: 'Principal'
            });

            const link = res.data.payment_link;

            // Mostrar modal de cobro en lugar de abrir el link
            this.showPaymentModal(link, total);

            this.cart = [];
            this.updateCartUI();
            UI.toast('Cobro generado exitosamente', 'success');
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    showPaymentModal(link, total) {
        const modalHtml = `
            <div id="payment-modal" class="modal-overlay" style="position: fixed; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: var(--spacing-lg);">
                <div style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); width: 100%; max-width: 350px; text-align: center; border: 1px solid var(--color-border);">
                    <div style="font-size: 40px; margin-bottom: 10px;">💳</div>
                    <h3>Cobro Generado</h3>
                    <p class="text-muted" style="margin-bottom: 20px;">Monto a cobrar: <strong>$${total.toFixed(2)}</strong></p>

                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <button class="btn btn-primary" onclick="navigator.clipboard.writeText('${link}'); UI.toast('Link copiado al portapapeles', 'success');">
                            📋 Copiar Link de Pago
                        </button>
                        <button class="btn" style="background: var(--color-bg); color: var(--color-text-main);" onclick="window.open('${link}', '_blank')">
                            👁️ Ver Link de Pago
                        </button>
                        <button class="btn" style="background: var(--color-border); color: var(--color-text-main);" onclick="document.getElementById('payment-modal').remove()">
                            Cerrar
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
};

window.Sales = Sales;
