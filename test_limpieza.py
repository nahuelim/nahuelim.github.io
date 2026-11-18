"""Chequeo de la limpieza de descripciones. Correr: python3 test_limpieza.py"""
from auto_ficha import limpiar_descripcion, normalizar_texto

texto = """Corredor Responsable: FULANA CPI 1234 / CSI 5678 -
Contacto: Juan Perez
Departamento de 3 ambientes al frente, muy luminoso.
Planes de pago: consultanos por las cuotas durante la obra.
Apto crédito.
Consultanos para coordinar una visita.
CPI 6234 - 7844
La información gráfica es estimativa y no forma parte de documentación contractual. Accesible: No (Ley 5.115).
Comprá la casa que querés! Simulá tu cuota en Lendar"""

limpio, sacado = limpiar_descripcion(texto, 'Pallarols Santander Propiedades')
assert 'Departamento de 3 ambientes' in limpio
assert 'consultanos por las cuotas' in limpio      # CTA en el medio: se queda
assert 'Apto crédito.' in limpio and 'Accesible: No (Ley 5.115).' in limpio
for fuera in ('CPI', 'Contacto', 'coordinar una visita', 'Lendar', 'contractual'):
    assert fuera not in limpio, fuera
assert any('Contacto: Juan Perez' in s for s in sacado)
assert normalizar_texto('&#x1d400;&#x1d414;&#x1d411;&#x1d400; 80 m² 7º') == 'AURA 80 m² 7º'
print('OK')
