/**
 * CommandDispatcher implementa el Dispatcher Pattern para desacoplar la UI de la lógica de negocio.
 * Permite ejecutar acciones mediante un identificador de comando y parámetros.
 */
import { 
  LoadStockCommand, 
  DeleteStockCommand, 
  GetStockCommand,
  GenerateCodeCommand
} from './stock';
import { 
  AddToCartCommand, 
  ProcessSaleCommand,
  GetVentasCommand,
  GetSalesStatsCommand
} from './sales';
import { 
  OpenCashCommand, 
  CloseCashCommand, 
  GetCashStateCommand 
} from './caja/CashCommands';
import { 
  SetUserCommand, 
  GetUserCommand 
} from './user/UserCommands';
import { 
  SaveAliasesCommand, 
  GetAliasesCommand, 
  DeleteAliasCommand 
} from './aliases/AliasCommands';

const COMMANDS = {
  'stock.load': LoadStockCommand,
  'stock.delete': DeleteStockCommand,
  'stock.get': GetStockCommand,
  'stock.generateCode': GenerateCodeCommand,
  'sales.add': AddToCartCommand,
  'sales.process': ProcessSaleCommand,
  'sales.get': GetVentasCommand,
  'sales.stats': GetSalesStatsCommand,
  'cash.open': OpenCashCommand,
  'cash.close': CloseCashCommand,
  'cash.get': GetCashStateCommand,
  'user.set': SetUserCommand,
  'user.get': GetUserCommand,
  'alias.save': SaveAliasesCommand,
  'alias.get': GetAliasesCommand,
  'alias.delete': DeleteAliasCommand,
};

export const CommandDispatcher = {
  async execute(commandName, params = {}) {
    const CommandClass = COMMANDS[commandName];
    
    if (!CommandClass) {
      throw new Error(`Comando no encontrado: ${commandName}`);
    }

    console.log(`[CommandDispatcher] Ejecutando: ${commandName}`, params);
    
    try {
      const command = new CommandClass(params);
      const result = await command.execute();
      
      // Aquí se podría integrar el sistema de auditoría solicitado en las preferencias globales
      await this.logAudit(commandName, params, 'SUCCESS');
      
      return result;
    } catch (error) {
      await this.logAudit(commandName, params, 'FAILURE', error.message);
      throw error;
    }
  },

  async logAudit(command, params, status, error = null) {
    // Implementación simplificada de auditoría (puede extenderse a DB)
    const entry = {
      timestamp: new Date().toISOString(),
      command,
      params,
      status,
      error
    };
    console.log(`[AuditLog] ${JSON.stringify(entry)}`);
    // Aquí se llamaría a storage.saveAudit(entry) si existiera
  }
};
