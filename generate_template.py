"""
generate_template.py
Exporta el TEMPLATE de generate.py para uso en auto_ficha.py
Copiá este archivo a ~/Documents/nahuelim.github.io/ junto con auto_ficha.py
"""

# Importa el TEMPLATE desde tu generate.py existente.
# Si generate.py está en la misma carpeta, esto funciona directo.
# Si está en otra carpeta, ajustá el path.

import sys
from pathlib import Path

# Intentar importar desde generate.py en la misma carpeta
try:
    # Import directo si generate.py está al lado
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "generate",
        Path(__file__).parent / "generate.py"
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    TEMPLATE = _mod.TEMPLATE
except Exception as e:
    raise ImportError(
        f"No se pudo importar TEMPLATE desde generate.py: {e}\n"
        f"Asegurate de que generate.py esté en la misma carpeta que auto_ficha.py"
    )
