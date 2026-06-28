import { getInventario } from '../../utils/storage';

export class GetStockCommand {
  async execute() {
    return await getInventario();
  }
}
