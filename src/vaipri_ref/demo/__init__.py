"""Modo demo: fixtures sinteticas para avaliacao offline.

Quando o ambiente do avaliador bloqueia o acesso a Meta (rede corp,
sandbox, etc), o modo demo carrega dados sinteticos plausiveis,
estruturalmente identicos a producao, e roda o pipeline real de
scoring/ranking sobre eles. Util para validar a logica da ferramenta
sem depender de internet aberta para facebook.com.

**Aviso:** os perfis em fixtures sao FICTICIOS. Veja `notas` de cada
referencia para confirmar.
"""
