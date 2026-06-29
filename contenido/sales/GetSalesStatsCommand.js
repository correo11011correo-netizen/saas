import { getInventario, getVentas } from '../../utils/storage';

export class GetSalesStatsCommand {
  async execute() {
    const inventario = await getInventario();
    const ventas = await getVentas();

    // Calcular facturación total
    const totalFacturado = ventas.reduce((acc, v) => acc + v.total, 0);

    // Ganancia estimada (30%)
    const gananciaEstimada = totalFacturado * 0.3;

    // Productos bajo stock (< 5)
    const bajoStock = inventario.filter(i => i.cantidad < 5).slice(0, 3);

    // Top Productos
    const conteo = {};
    ventas.forEach(v => {
      v.items.forEach(item => {
        conteo[item.nombre] = (conteo[item.nombre] || 0) + item.cantidad;
      });
    });
    const topProductos = Object.entries(conteo)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 3)
      .map(([nombre, cant]) => ({ nombre, cant }));

    return {
      totalFacturado,
      gananciaEstimada,
      topProductos,
      bajoStock,
      ventasRecientes: ventas.slice(-5).reverse()
    };
  }
}
