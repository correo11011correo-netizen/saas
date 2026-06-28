import { getInventario, saveInventario } from '../../utils/storage';

export class DeleteStockCommand {
  constructor({ codigo }) {
    this.codigo = codigo;
  }

  async execute() {
    const inventario = await getInventario();
    const newInv = inventario.filter(i => i.codigo !== this.codigo);
    await saveInventario(newInv, true);
    return newInv;
  }
}
