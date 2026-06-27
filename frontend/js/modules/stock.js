/**
 * OMNICORE STOCK & SALES MODULE
 * Gestión unificada de inventario, punto de venta (POS), preventas y administración de existencias.
 */

window.Stock = {
    defaultPanel: 'inventory',
    config: {
        dock: [
            { id: 'inventory', icon: 'box', label: 'Stock' },
            { id: 'pos', icon: 'sales', label: 'Cobrar' },
            { id: 'cash', icon: 'box', label: 'Caja' },
            { id: 'presale', icon: 'sales', label: 'Preventa' },
        ],
        panels: [
            { id: 'inventory', icon: 'box', label: 'Administración Stock' },
            { id: 'pos', icon: 'sales', label: 'Punto de Venta' },
            { id: 'cash', icon: 'box', label: 'Gestión de Caja' },
            { id: 'aliases', icon: 'settings', label: 'Alias de Pago' },
            { id: 'audit', icon: 'settings', label: 'Trazabilidad' },
            { id: 'presale', icon: 'sales', label: 'Sector Preventa' },
            { id: 'objectives', icon: 'settings', label: 'Objetivos de Stock' },
            { id: 'employee_tools', icon: 'user', label: 'Herramientas Empleado' },
            { id: 'profile', icon: 'user', label: 'Perfil' }
        ]
    },

    async render(panelId = 'inventory') {
        switch(panelId) {
            case 'inventory': this.renderInventory(); break;
            case 'pos': this.renderPOS(); break;
            case 'cash': this.renderCash(); break;
            case 'aliases': this.renderAliases(); break;
            case 'audit': this.renderAudit(); break;
            case 'presale': this.renderPresale(); break;
            case 'objectives': this.renderObjectives(); break;
            case 'employee_tools': this.renderEmployeeTools(); break;
            default: this.renderInventory();
        }
    },

    // =========================================================================
    // SECCIÓN: INVENTARIO (STOCK)
    // =========================================================================

    async renderInventory() {
        UI.render('app-content', `
            <div class="stock-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <header style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>${Icons.box} Administración de Stock</h3>
                    <button class="btn btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="Stock.showAddProduct()">+ Producto</button>
                </header>
                <div id="stock-list" style="display: flex; flex-direction: column; gap: var(--spacing-sm);">
                    <p class="text-muted">Cargando productos...</p>
                </div>
            </div>
        `);
        await this.loadProducts();
    },

    async loadProducts() {
        try {
            const res = await API.execute('products.list', {});
            const products = res.data;

            if (!products || products.length === 0) {
                UI.render('stock-list', `<p class="text-muted">No hay productos en stock.</p>`);
                return;
            }

            const listHtml = products.map(p => `
                <div style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm);">
                    <div>
                        <div style="font-weight: 600;">${p.name}</div>
                        <div class="text-muted" style="font-size: 12px;">Código: ${p.code} | Cat: ${p.category}</div>
                    </div>
                    <div style="text-align: right; display: flex; align-items: center; gap: 15px;">
                        <div style="font-weight: 700; color: var(--color-primary);">$${p.price}</div>
                        <div style="display: flex; align-items: center; gap: 5px;">
                            <button class="btn" style="padding: 2px 6px; font-size: 10px;" onclick="Stock.adjustStock('${p.code}', -1)">-</button>
                            <div style="font-size: 12px; min-width: 20px; text-align: center;">${p.quantity}</div>
                            <button class="btn" style="padding: 2px 6px; font-size: 10px;" onclick="Stock.adjustStock('${p.code}', 1)">+</button>
                        </div>
                    </div>
                </div>
            `).join('');

            UI.render('stock-list', listHtml);
        } catch (e) {
            UI.render('stock-list', `<p class="text-error" style="color: var(--color-error);">Error cargando stock: ${e.message}</p>`);
        }
    },

    async adjustStock(code, delta) {
        UI.showLoading();
        try {
            await API.execute('stock.update', { code, quantity: delta, reason: 'AJUSTE_RAPIDO' });
            UI.toast('Stock actualizado', 'success');
            await this.loadProducts();
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    showAddProduct() {
        const modalHtml = `
            <div id="modal-stock-add" class="modal-overlay" style="position: fixed; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: var(--spacing-lg);">
                <div style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); width: 100%; max-width: 350px; border: 1px solid var(--color-border);">
                    <h3>Nuevo Producto</h3>
                    <input type="text" id="add-code" class="input-field" placeholder="Código SKU">
                    <input type="text" id="add-name" class="input-field" placeholder="Nombre del Producto">
                    <input type="number" id="add-price" class="input-field" placeholder="Precio">
                    <input type="number" id="add-qty" class="input-field" placeholder="Cantidad Inicial">
                    <input type="text" id="add-cat" class="input-field" placeholder="Categoría">
                    <div style="display: flex; gap: var(--spacing-sm); margin-top: var(--spacing-md);">
                        <button class="btn" style="flex: 1; background: var(--color-border); color: var(--color-text-main);" onclick="Stock.closeModal()">Cancelar</button>
                        <button class="btn btn-primary" style="flex: 1;" onclick="Stock.submitAddProduct()">Guardar</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    async submitAddProduct() {
        const code = document.getElementById('add-code').value;
        const name = document.getElementById('add-name').value;
        const price = parseFloat(document.getElementById('add-price').value);
        const quantity = parseInt(document.getElementById('add-qty').value);
        const category = document.getElementById('add-cat').value;

        if (!code || !name || isNaN(price) || isNaN(quantity)) {
            return UI.toast('Completa todos los campos obligatorios (incluyendo cantidad)', 'error');
        }

        UI.showLoading();
        try {
            await API.execute('stock.add', {
                code,
                name,
                price,
                quantity,
                category,
                is_weight: false
            });
            UI.toast('Producto guardado', 'success');
            this.closeModal();
            await this.loadProducts();
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    // =========================================================================
    // SECCIÓN: VENTAS / POS (INTEGRADO)
    // =========================================================================

    async renderPOS() {
        UI.render('app-content', `
            <div class="sales-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <header style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>${Icons.sales} Punto de Venta</h3>
                    <div id="cash-status" style="font-size: 12px; font-weight: 600; padding: 4px 8px; border-radius: 4px; background: var(--color-error); color: white;">Caja Cerrada</div>
                </header>

                <div class="pos-main" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <h4>Procesar Cobro</h4>
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-sm); margin-top: var(--spacing-md);">
                        <input type="text" id="sale-cliente" class="input-field" placeholder="Nombre del Cliente">
                        <div id="sale-items-container" style="display: flex; flex-direction: column; gap: 8px;">
                            <div class="sale-item-row" style="display: flex; gap: 8px;">
                                <input type="text" class="input-field sale-code" placeholder="Código SKU" onchange="Stock.calculateSaleTotal()">
                                <input type="number" class="input-field sale-qty" placeholder="Cant" style="width: 80px;" onchange="Stock.calculateSaleTotal()">
                            </div>
                        </div>
                        <button class="btn" style="background: var(--color-border); color: var(--color-text-main); font-size: 12px;" onclick="Stock.addSaleRow()">+ Agregar Producto</button>

                        <div style="margin-top: 10px; padding: 10px; background: var(--color-bg); border-radius: var(--radius-sm);">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span class="text-muted">Total:</span>
                                <span id="sale-total" style="font-weight: 700; font-size: 18px; color: var(--color-primary);">$ 0.00</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; gap: 10px; margin-top: 10px;">
                                <select id="sale-method" class="input-field" style="flex: 1;" onchange="Stock.toggleAliasField()">
                                    <option value="Efectivo">Efectivo</option>
                                    <option value="Transferencia">Transferencia</option>
                                    <option value="Tarjeta">Tarjeta</option>
                                </select>
                                <input type="text" id="sale-alias" class="input-field" placeholder="Alias" style="flex: 1; display: none;">
                            </div>
                            <input type="number" id="sale-pay" class="input-field" style="margin-top: 10px;" placeholder="Monto pagado con" oninput="Stock.calculateChange()">
                            <div style="display: flex; justify-content: space-between; margin-top: 10px; font-weight: 600;">
                                <span>Vuelto:</span>
                                <span id="sale-change" style="color: var(--color-success);">$ 0.00</span>
                            </div>
                        </div>
                        <button class="btn btn-primary" style="width: 100%; margin-top: var(--spacing-md);" onclick="Stock.submitSale()">Confirmar Cobro</button>
                    </div>
                </div>
            </div>
        `);
        await this.updateCashStatus();
    },

    async renderCash() {
        UI.render('app-content', `
            <div class="cash-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <header style="display: flex; align-items: center; gap: 10px;">
                    <h3>${Icons.box} Gestión de Caja</h3>
                </header>
                <div class="cash-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md);">
                    <button class="btn ${this.isCashOpen() ? 'btn-error' : 'btn-primary'}" style="padding: 20px;" onclick="Stock.toggleCash()">
                        ${this.isCashOpen() ? 'Cerrar Caja' : 'Abrir Caja'}
                    </button>
                    <button class="btn" style="padding: 20px; background: white;" onclick="Stock.getCashReport()">
                        ${Icons.settings} Ver Reporte
                    </button>
                </div>
                <section id="cash-report-area" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm); display: none;">
                    <h4>Resumen de Caja Actual</h4>
                    <div id="cash-report-data" style="display: flex; flex-direction: column; gap: 8px; margin-top: var(--spacing-md);"></div>
                </section>
            </div>
        `);
    },

    async renderAliases() {
        UI.render('app-content', `
            <div class="aliases-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <header style="display: flex; align-items: center; gap: 10px;">
                    <h3>${Icons.settings} Alias de Pago</h3>
                </header>
                <section class="alias-card" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <h4>Registrar Nuevo Alias</h4>
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-sm); margin-top: var(--spacing-md);">
                        <input type="text" id="alias-name" class="input-field" placeholder="Nombre del Alias (ej: MercadoPago_1)">
                        <input type="number" id="alias-limit" class="input-field" placeholder="Límite de Acumulado">
                        <button class="btn btn-primary" style="width: 100%; margin-top: var(--spacing-md);" onclick="Stock.submitAlias()">Guardar Alias</button>
                    </div>
                </section>
            </div>
        `);
    },

    async renderAudit() {
        UI.showLoading();
        try {
            const res = await API.execute('system.audit.get_logs', { command: 'venta.cobrar', limit: 20 });
            const logs = res.data || [];

            UI.render('app-content', `
                <div class="audit-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                    <header style="display: flex; align-items: center; gap: 10px;">
                        <h3>${Icons.settings} Trazabilidad de Ventas</h3>
                    </header>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        ${logs.length === 0 ? '<p class="text-muted">No hay registros de ventas recientes.</p>' :
                            logs.map(log => `
                                <div style="background: white; padding: 10px; border-radius: var(--radius-md); border: 1px solid var(--color-border); font-size: 12px;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                        <span style="font-weight: 600;">${log.command}</span>
                                        <span class="text-muted">${new Date(log.timestamp).toLocaleString()}</span>
                                    </div>
                                    <div style="color: ${log.status === 'success' ? 'var(--color-success)' : 'var(--color-error)'};">
                                        ${log.message}
                                    </div>
                                </div>
                            `).join('')
                        }
                    </div>
                </div>
            `);
        } catch (e) {
            UI.toast('Error cargando auditoría: ' + e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async updateCashStatus() {
        try {
            const res = await API.execute('cash.report', {});
            const statusEl = document.getElementById('cash-status');
            if (statusEl) {
                statusEl.innerText = 'Caja Abierta';
                statusEl.style.background = 'var(--color-success)';
            }
        } catch (e) {
            const statusEl = document.getElementById('cash-status');
            if (statusEl) {
                statusEl.innerText = 'Caja Cerrada';
                statusEl.style.background = 'var(--color-error)';
            }
        }
    },

    isCashOpen() {
        const statusEl = document.getElementById('cash-status');
        return statusEl && statusEl.innerText === 'Caja Abierta';
    },

    async toggleCash() {
        const open = !this.isCashOpen();
        UI.showLoading();
        try {
            if (open) {
                const amount = prompt('Ingrese monto inicial de efectivo:', '0');
                if (amount === null) return;
                await API.execute('cash.open', { efectivo_inicial: parseFloat(amount) });
                UI.toast('Caja abierta con éxito', 'success');
            } else {
                await API.execute('cash.close', {});
                UI.toast('Caja cerrada con éxito', 'success');
            }
            this.renderCash();
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async getCashReport() {
        UI.showLoading();
        try {
            const res = await API.execute('cash.report', {});
            document.getElementById('cash-report-area').style.display = 'block';
            UI.render('cash-report-data', `
                <div style="display: flex; justify-content: space-between;">
                    <span class="text-muted">Efectivo Inicial:</span>
                    <span>$${res.data.efectivo_inicial}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span class="text-muted">Ventas Efectivo:</span>
                    <span>$${res.data.ventas_efectivo}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span class="text-muted">Ventas Digital:</span>
                    <span>$${res.data.ventas_digital}</span>
                </div>
                <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--color-border); padding-top: 8px; font-weight: 700; color: var(--color-primary);">
                    <span>Total en Caja:</span>
                    <span>$${res.data.total_en_caja}</span>
                </div>
            `);
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    toggleAliasField() {
        const method = document.getElementById('sale-method').value;
        const aliasField = document.getElementById('sale-alias');
        aliasField.style.display = (method === 'Transferencia') ? 'block' : 'none';
    },

    addSaleRow() {
        const container = document.getElementById('sale-items-container');
        const div = document.createElement('div');
        div.className = 'sale-item-row';
        div.style = 'display: flex; gap: 8px;';
        div.innerHTML = `
            <input type="text" class="input-field sale-code" placeholder="Código SKU" onchange="Stock.calculateSaleTotal()">
            <input type="number" class="input-field sale-qty" placeholder="Cant" style="width: 80px;" onchange="Stock.calculateSaleTotal()">
            <button class="btn" style="background: var(--color-error); color: white;" onclick="this.parentElement.remove(); Stock.calculateSaleTotal();">✕</button>
        `;
        container.appendChild(div);
    },

    async calculateSaleTotal() {
        const rows = document.querySelectorAll('.sale-item-row');
        let total = 0;

        for (const row of rows) {
            const code = row.querySelector('.sale-code').value;
            const qty = parseInt(row.querySelector('.sale-qty').value) || 0;

            if (code && qty > 0) {
                try {
                    const res = await API.execute('stock.get', { code });
                    total += res.data.price * qty;
                } catch (e) {
                    console.error('Producto no encontrado:', code);
                }
            }
        }
        document.getElementById('sale-total').innerText = `$ ${total.toFixed(2)}`;
        this.calculateChange();
    },

    calculateChange() {
        const totalStr = document.getElementById('sale-total').innerText.replace('$', '').trim();
        const payStr = document.getElementById('sale-pay').value;
        const total = parseFloat(totalStr) || 0;
        const pay = parseFloat(payStr) || 0;
        const change = pay - total;
        document.getElementById('sale-change').innerText = `$ ${Math.max(0, change).toFixed(2)}`;
    },

    async submitSale() {
        const cliente = document.getElementById('sale-cliente').value;
        const metodo_pago = document.getElementById('sale-method').value;
        const alias = document.getElementById('sale-alias').value;
        const paga_con = parseFloat(document.getElementById('sale-pay').value || 0);

        const rows = document.querySelectorAll('.sale-item-row');
        const items = [];
        rows.forEach(row => {
            items.push({
                product_code: row.querySelector('.sale-code').value,
                quantity: parseInt(row.querySelector('.sale-qty').value) || 0
            });
        });

        if (!cliente || items.length === 0) return UI.toast('Completa los datos y añade productos', 'error');

        UI.showLoading();
        try {
            const res = await API.execute('venta.cobrar', {
                cliente,
                items,
                metodo_pago,
                paga_con,
                alias
            });
            UI.toast(`Venta exitosa. Vuelto: $${res.data.vuelto}`, 'success');
            if (window.App) App.loadModule('stock', 'pos');
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async submitAlias() {
        const nombre = document.getElementById('alias-name').value;
        const limite = parseFloat(document.getElementById('alias-limit').value);

        if (!nombre || isNaN(limite)) return UI.toast('Completa los datos del alias', 'error');

        UI.showLoading();
        try {
            await API.execute('sales.create_alias', { nombre, limite });
            UI.toast('Alias registrado correctamente', 'success');
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    // =========================================================================
    // SECCIÓN: PREVENTAS Y HERRAMIENTAS
    // =========================================================================

    async renderPresale() {
        UI.render('app-content', `
            <div class="presale-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <header style="display: flex; align-items: center; gap: 10px;">
                    <h3>${Icons.sales} Sector Preventa</h3>
                </header>
                <section class="presale-card" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                    <h4>Crear Presupuesto / Pedido</h4>
                    <div style="display: flex; flex-direction: column; gap: var(--spacing-sm); margin-top: var(--spacing-md);">
                        <input type="text" id="pre-cliente" class="input-field" placeholder="Cliente">
                        <div id="pre-items-container" style="display: flex; flex-direction: column; gap: 8px;">
                            <div class="pre-item-row" style="display: flex; gap: 8px;">
                                <input type="text" class="input-field pre-code" placeholder="Código" onchange="Stock.calculatePresaleTotal()">
                                <input type="number" class="input-field pre-qty" placeholder="Cant" style="width: 80px;" onchange="Stock.calculatePresaleTotal()">
                            </div>
                        </div>
                        <button class="btn" style="background: var(--color-border); color: var(--color-text-main); font-size: 12px;" onclick="Stock.addPresaleRow()">+ Agregar Producto</button>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--color-bg); border-radius: var(--radius-sm); margin-top: 10px;">
                            <span style="font-weight: 600;">Precio Total Estimado:</span>
                            <span id="pre-total" style="font-size: 20px; font-weight: 700; color: var(--color-primary);">$ 0.00</span>
                        </div>
                        <button class="btn btn-primary" style="width: 100%; margin-top: var(--spacing-md);" onclick="Stock.savePresale()">Guardar Presupuesto</button>
                    </div>
                </section>
            </div>
        `);
    },

    async renderObjectives() {
        UI.showLoading();
        try {
            const res = await API.execute('products.list', {});
            const products = res.data || [];
            const critical = products.filter(p => p.quantity <= 5);

            UI.render('app-content', `
                <div class="objectives-container" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                    <header style="display: flex; align-items: center; gap: 10px;">
                        <h3>${Icons.settings} Objetivos de Stock</h3>
                    </header>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md);">
                        <div style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                            <div style="font-size: 12px; color: var(--color-text-muted);">Stock Crítico</div>
                            <div style="font-size: 24px; font-weight: 700; color: var(--color-error);">${critical.length} Productos</div>
                        </div>
                        <div style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                            <div style="font-size: 12px; color: var(--color-text-muted);">Total Referencias</div>
                            <div style="font-size: 24px; font-weight: 700; color: var(--color-success);">${products.length}</div>
                        </div>
                    </div>
                    <section style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                        <h4>Alertas de Reposición</h4>
                        <div id="alerts-list" style="display: flex; flex-direction: column; gap: 8px; margin-top: var(--spacing-md);">
                            ${critical.length === 0 ? '<p class="text-muted">Todo el stock está en niveles óptimos.</p>' :
                                critical.map(p => `
                                    <div style="padding: 8px; border-left: 4px solid var(--color-warning); background: var(--color-bg); font-size: 13px;">
                                        📦 Producto <b>${p.name}</b> debajo del mínimo (${p.quantity} unidades).
                                    </div>
                                `).join('')
                            }
                        </div>
                    </section>
                </div>
            `);
        } catch (e) {
            UI.toast('Error cargando objetivos: ' + e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async renderEmployeeTools() {
        UI.render('app-content', `
            <div class="employee-tools" style="display: flex; flex-direction: column; gap: var(--spacing-lg);">
                <header style="display: flex; align-items: center; gap: 10px;">
                    <h3>${Icons.user} Herramientas de Empleado</h3>
                </header>
                <div class="tools-grid" style="display: grid; grid-template-columns: 1fr; gap: var(--spacing-md);">
                    <section style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm);">
                        <h4>Consulta Rápida de Precios</h4>
                        <div style="display: flex; gap: 8px; margin-top: 10px;">
                            <input type="text" id="quick-code" class="input-field" placeholder="Ingresar código SKU...">
                            <button class="btn btn-primary" onclick="Stock.quickCheck()">Buscar</button>
                        </div>
                        <div id="quick-result" style="margin-top: 15px; font-weight: 600; font-size: 18px; color: var(--color-primary);"></div>
                    </section>
                    <div onclick="Stock.reportIssue()" style="background: white; padding: var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-border); text-align: center; cursor: pointer; box-shadow: var(--shadow-sm);">
                        ${Icons.settings} <div style="font-weight: 600; margin-top: 8px;">Reportar Error / Incidencia</div>
                    </div>
                </div>
            </div>
        `);
    },

    addPresaleRow() {
        const container = document.getElementById('pre-items-container');
        const div = document.createElement('div');
        div.className = 'pre-item-row';
        div.style = 'display: flex; gap: 8px;';
        div.innerHTML = `
            <input type="text" class="input-field pre-code" placeholder="Código" onchange="Stock.calculatePresaleTotal()">
            <input type="number" class="input-field pre-qty" placeholder="Cant" style="width: 80px;" onchange="Stock.calculatePresaleTotal()">
            <button class="btn" style="background: var(--color-error); color: white;" onclick="this.parentElement.remove(); Stock.calculatePresaleTotal();">✕</button>
        `;
        container.appendChild(div);
    },

    async calculatePresaleTotal() {
        const rows = document.querySelectorAll('.pre-item-row');
        let total = 0;

        for (const row of rows) {
            const code = row.querySelector('.pre-code').value;
            const qty = parseInt(row.querySelector('.pre-qty').value) || 0;

            if (code && qty > 0) {
                try {
                    const res = await API.execute('stock.get', { code });
                    total += res.data.price * qty;
                } catch (e) {
                    console.error('Producto no encontrado:', code);
                }
            }
        }
        document.getElementById('pre-total').innerText = `$ ${total.toFixed(2)}`;
    },

    savePresale() {
        const cliente = document.getElementById('pre-cliente').value;
        if (!cliente) return UI.toast('Ingresa el nombre del cliente', 'error');
        UI.toast(`Presupuesto para ${cliente} guardado correctamente`, 'success');
    },

    async quickCheck() {
        const code = document.getElementById('quick-code').value;
        if (!code) return;

        UI.showLoading();
        try {
            const res = await API.execute('stock.get', { code });
            document.getElementById('quick-result').innerText = `${res.data.name} - $${res.data.price} (Stock: ${res.data.quantity})`;
        } catch (e) {
            document.getElementById('quick-result').innerText = 'Producto no encontrado';
        } finally {
            UI.hideLoading();
        }
    },

    closeModal() {
        const modal = document.querySelector('.modal-overlay');
        if (modal) modal.remove();
    },

    reportIssue() {
        UI.toast('Abriendo formulario de incidencias...', 'info');
    }
};

window.Stock = Stock;
