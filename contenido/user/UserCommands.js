import { setUsuarioActivo, getUsuarioActivo } from '../../utils/storage';

export class SetUserCommand {
  constructor({ role }) {
    this.role = role;
  }
  async execute() {
    await setUsuarioActivo(this.role);
    return await getUsuarioActivo();
  }
}

export class GetUserCommand {
  async execute() {
    return await getUsuarioActivo();
  }
}
