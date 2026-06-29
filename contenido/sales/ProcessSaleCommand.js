import { saveVenta, getInventario, saveInventario } from '../../utils/storage';

export class ProcessSaleCommand {
  constructor({ saleData, inventario }) {
    this.saleData = saleData;
    this.inventario = inventario;
  }

  async execute() {
    // 1. Guardar la venta
    await saveVenta(this.saleData);

    // 2. Actualizar el stock
    let newInv = [...this.inventario];
    this.saleData.items.forEach(item => {
      const idx = newInv.findIndex(i => i.codigo === item.codigo);
      if (idx > -1) {
        newInv[idx].cantidad -= item.cantidad;
      }
    });

    await saveInventario(newInv);
    return { success: true, updatedInventory: newInv };
  }
}
