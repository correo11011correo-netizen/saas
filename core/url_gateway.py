import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.auth import SECRET_KEY
from core.context import TenantContext
from core.dispatcher import dispatcher


class URLCommandGateway:
    """
    Permite la ejecución de comandos vía URL mediante tokens firmados (HMAC).
    Ideal para invitaciones, activaciones y deep-linking en APKs.
    """

    def __init__(self):
        self.secret = SECRET_KEY.encode()

    def generate_signed_url(self, command: str, params: dict, expires_in: int = 3600) -> str:
        """
        Genera un token firmado para ejecutar un comando.
        """
        timestamp = int(time.time())
        payload = {"cmd": command, "params": params, "exp": timestamp + expires_in}
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(self.secret, payload_json.encode(), hashlib.sha256).hexdigest()

        # Retornamos el payload y la firma (estos irán en la URL)
        return f"{payload_json}|{signature}"

    def validate_and_execute(self, signed_token: str, db_session: Session) -> Any:
        """
        Valida la firma del token y ejecuta el comando usando un contexto de sistema.
        """
        try:
            payload_json, signature = signed_token.rsplit("|", 1)

            # 1. Validar Firma
            expected_signature = hmac.new(
                self.secret, payload_json.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                raise HTTPException(status_code=403, detail="Invalid URL signature")

            payload = json.loads(payload_json)

            # 2. Validar Expiración
            if time.time() > payload.get("exp", 0):
                raise HTTPException(status_code=410, detail="URL token expired")

            # 3. Ejecutar con Contexto de Sistema (Bypass de Auth normal)
            # Usamos el rol 'system' para que el Dispatcher permita la acción administrativa
            context = TenantContext(
                tenant_id=payload["params"].get("tenant_id"),
                user_id=uuid.UUID(int(time.time())),  # ID efímero para auditoría
                role="system",
                plan="enterprise",
            )

            dispatcher.db_session_factory = lambda: db_session
            return dispatcher.execute(payload["cmd"], payload["params"], context)

        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Malformed URL token: {str(e)}")


url_gateway = URLCommandGateway()
