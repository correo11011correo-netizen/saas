export class GenerateCodeCommand {
  constructor({ categoria }) {
    this.categoria = categoria;
  }

  execute() {
    const prefijo = this.categoria ? this.categoria.charAt(0).toUpperCase() : 'X';
    const num = Math.floor(1000 + Math.random() * 9000);
    return `${prefijo}-${num}`;
  }
}
