import { getInventario, saveInventario } from '../../utils/storage';

export class LoadStockCommand {
  constructor({ item }) {
    this.item = item;
  }

  async execute() {
    const inventario = await getInventario();
    let newInv = [...inventario];
    const idx = newInv.findIndex(i => i.codigo === this.item.codigo);

    if (idx > -1) {
      newInv[idx] = this.item;
    } else {
      newInv.push(this.item);
    }

    await saveInventario(newInv, true);
    return newInv;
  }
}
