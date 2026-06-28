export class AddToCartCommand {
  constructor({ cart, product, weight = null }) {
    this.cart = cart;
    this.product = product;
    this.weight = weight;
  }

  async execute() {
    if (this.product.esPeso) {
      if (!this.weight) throw new Error('El peso es obligatorio para productos por kilo.');
      
      const pesoKilos = parseFloat(this.weight) / 1000;
      if (isNaN(pesoKilos) || pesoKilos <= 0) throw new Error('Ingresa un peso válido en gramos.');
      
      return [...this.cart, { ...this.product, cantidad: pesoKilos, totalItem: this.product.precio * pesoKilos }];
    }
    
    const existing = this.cart.find(c => c.codigo === this.product.codigo);
    if (existing) {
      return this.cart.map(c => c.codigo === this.product.codigo ? { ...c, cantidad: c.cantidad + 1 } : c);
    }
    return [...this.cart, { ...this.product, cantidad: 1 }];
  }
}
