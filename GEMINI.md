# Proyecto SaaS - Estándares de Ingeniería

## Protocolo de Calidad y Despliegue
- **Validación Estricta:** No se permite realizar `git commit` ni `git push` si el sistema de `pre-commit` falla.
- **Resolución Obligatoria:** Todo error detectado por linters (`ruff`) o formateadores debe ser solucionado antes de staging.
- **Prohibido Bypassing:** El uso de `--no-verify` está estrictamente prohibido. Cualquier despliegue debe ser garantizado por una suite de validación exitosa.
