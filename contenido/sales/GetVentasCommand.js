import { getVentas } from '../../utils/storage';

export class GetVentasCommand {
  async execute() {
    return await getVentas();
  }
}
