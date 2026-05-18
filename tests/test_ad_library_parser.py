"""Testes do parser da Meta Ad Library com HTML sintetico."""

from __future__ import annotations

import json

from vaipri_ref.discovery.meta_ad_library import _parse_html, _extrair_pages_de_blob


def _html_com_blob(blob: dict) -> str:
    return f"<html><body><script>{json.dumps(blob)}</script></body></html>"


# IDs reais do Facebook tem 11-16 digitos. Usamos o mesmo padrao no teste
# porque o parser exige >= 6 digitos para evitar falsos positivos com numeros
# de telefone, IDs de post, etc.
_PAGE_ID_1 = "100100100100"
_PAGE_ID_2 = "200200200200"
_PAGE_ID_3 = "300300300300"


def test_extrai_multiplas_paginas_sem_vazamento():
    blob = {
        "data": {
            "search_results_connection": {
                "edges": [
                    {
                        "node": {
                            "page_id": _PAGE_ID_1,
                            "page_name": "Dr. A Dermato",
                            "page_profile_uri": "https://facebook.com/drA",
                            "ig_username": "dr.a",
                            "total_active_ads": 12,
                        }
                    },
                    {
                        "node": {
                            "page_id": _PAGE_ID_2,
                            "page_name": "Dr. B Plastica",
                            "page_profile_uri": "https://facebook.com/drB",
                            "total_active_ads": 8,
                        }
                    },
                ]
            }
        }
    }
    advs = _parse_html(_html_com_blob(blob))
    assert len(advs) == 2
    a = next(x for x in advs if x.fb_page_id == _PAGE_ID_1)
    b = next(x for x in advs if x.fb_page_id == _PAGE_ID_2)
    assert a.fb_page_name == "Dr. A Dermato"
    assert a.n_anuncios_ativos == 12
    assert a.ig_handle_hint == "dr.a"
    assert b.fb_page_name == "Dr. B Plastica"
    assert b.n_anuncios_ativos == 8
    # campos do A nao devem ter vazado pro B
    assert b.ig_handle_hint != "dr.a"


def test_extrai_handle_de_url_inline():
    blob = {
        "node": {
            "page_id": _PAGE_ID_3,
            "page_name": "Clinica Sigma",
            "page_profile_uri": "https://facebook.com/sigma",
            "instagram_link": "https://instagram.com/clinicasigma",
            "total_active_ads": 5,
        }
    }
    advs = _parse_html(_html_com_blob(blob))
    assert len(advs) == 1
    assert advs[0].ig_handle_hint == "clinicasigma"


def test_html_sem_blob_devolve_vazio():
    html = "<html><body><p>nada aqui</p></body></html>"
    assert _parse_html(html) == []


def test_pages_sem_total_assumem_pelo_menos_1():
    blob = {"node": {"page_id": _PAGE_ID_1, "page_name": "X"}}
    advs = _parse_html(_html_com_blob(blob))
    assert advs[0].n_anuncios_ativos == 1


def test_page_id_muito_curto_e_ignorado():
    """IDs com menos de 6 digitos sao ignorados: evita falso positivo."""
    blob = {"node": {"page_id": "123", "page_name": "Spam"}}
    advs = _parse_html(_html_com_blob(blob))
    assert advs == []
