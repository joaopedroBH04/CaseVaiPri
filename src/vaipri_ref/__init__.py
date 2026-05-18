"""Buscador de referencias de trafego pago para clinicas medicas.

API publica do pacote: importe `buscar_referencias` para uso programatico.

    from vaipri_ref import buscar_referencias

    resultado = buscar_referencias(
        handle_cliente="@clinica.exemplo",
        especialidade="dermatologia",
    )
"""

from vaipri_ref.models import (
    Anuncio,
    Candidato,
    Metricas,
    Referencia,
    Resultado,
)
from vaipri_ref.pipeline import buscar_referencias

__all__ = [
    "Anuncio",
    "Candidato",
    "Metricas",
    "Referencia",
    "Resultado",
    "buscar_referencias",
]

__version__ = "0.1.0"
