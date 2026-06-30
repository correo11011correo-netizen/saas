from typing import Dict, Any, Optional
from motor.infrastructure.providers.base import BaseProvider

class EngineState:
    """
    El corazón del sistema. Gestiona los 'enchufes' (providers) activos.
     Permite cambiar la fuente de datos en caliente sin reiniciar el daemon.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineState, cls).__new__(cls)
            cls._instance.providers: Dict[str, BaseProvider] = {}
        return cls._instance

    def set_provider(self, function_name: str, provider: BaseProvider):
        """Asigna un proveedor de datos a una función específica (ej. 'sales', 'users')."""
        self.providers[function_name] = provider

    def get_provider(self, function_name: str) -> Optional[BaseProvider]:
        """Obtiene el proveedor activo para una función."""
        return self.providers.get(function_name)

    def get_all_status(self) -> Dict[str, Any]:
        """Retorna el estado de salud de todos los proveedores conectados."""
        return {
            name: {
                "connected": provider.health_check(),
                "type": provider.__class__.__name__
            }
            for name, provider in self.providers.items()
        }

# Singleton instance
state = EngineState()
