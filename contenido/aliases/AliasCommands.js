import { saveAliases, getAliases } from '../../utils/storage';

export class SaveAliasesCommand {
  constructor({ aliases }) {
    this.aliases = aliases;
  }
  async execute() {
    await saveAliases(this.aliases);
    return this.aliases;
  }
}

export class GetAliasesCommand {
  async execute() {
    return await getAliases();
  }
}

export class DeleteAliasCommand {
  constructor({ id }) {
    this.id = id;
  }
  async execute() {
    const current = await getAliases();
    const updated = current.filter(a => a.id !== this.id);
    await saveAliases(updated);
    return updated;
  }
}
