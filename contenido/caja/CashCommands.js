import { abrirCaja, cerrarCaja, getCajaEstado } from '../../utils/storage';

export class OpenCashCommand {
  constructor({ monto }) {
    this.monto = monto;
  }
  async execute() {
    await abrirCaja(this.monto);
    return await getCajaEstado();
  }
}

export class CloseCashCommand {
  constructor({ montoCierre }) {
    this.montoCierre = montoCierre;
  }
  async execute() {
    await cerrarCaja(this.montoCierre);
    return await getCajaEstado();
  }
}

export class GetCashStateCommand {
  async execute() {
    return await getCajaEstado();
  }
}
