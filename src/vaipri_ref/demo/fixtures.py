"""Fixtures sinteticas: perfis ficticios estruturalmente identicos aos reais.

Os dados aqui foram desenhados para refletir distribuicoes realistas
do mercado brasileiro de medicos que anunciam no Meta. Os nomes,
handles e numeros sao **ficticios** e existem apenas para que o
avaliador possa testar o pipeline ponta-a-ponta sem depender de
acesso aberto a internet (no caso de rede corporativa ou sandbox).

Cada entrada simula o output bruto do `MetaAdLibraryScraper`. O
pipeline real entao roda toda a logica subsequente (resolucao de
handle, enriquecimento IG, match de especialidade, score) em cima
desses dados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class FixtureAdvertiser:
    """Anunciante ficticio. Espelha o shape de _AdvertiserBruto."""

    fb_page_id: str
    fb_page_name: str
    fb_page_url: str
    n_anuncios_ativos: int
    instagram_handle: str  # sempre presente em fixture (alta confianca)
    seguidores: int
    seguindo: int
    total_posts: int
    bio: str
    nome_completo: str


# -------------------- DERMATOLOGIA --------------------

DERMATOLOGIA: list[FixtureAdvertiser] = [
    FixtureAdvertiser(
        fb_page_id="1000010001",
        fb_page_name="Dra. Ana Lima — Dermatologia",
        fb_page_url="https://www.facebook.com/draanalima",
        n_anuncios_ativos=22,
        instagram_handle="draanalima.derm",
        seguidores=187_500,
        seguindo=412,
        total_posts=1_240,
        bio="Dermatologista | CRM-SP 198765 | RQE 5142 | Melasma, acne, harmonizacao | Agende: bit.ly/dra-ana",
        nome_completo="Dra. Ana Lima",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010002",
        fb_page_name="Clinica Lume Dermato",
        fb_page_url="https://www.facebook.com/lumederma",
        n_anuncios_ativos=18,
        instagram_handle="lume.derma",
        seguidores=112_300,
        seguindo=287,
        total_posts=789,
        bio="Clinica de dermatologia estetica | Procedimentos avancados | SP e RJ",
        nome_completo="Lume Dermato",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010003",
        fb_page_name="Dr. Pedro Salles — Dermato",
        fb_page_url="https://www.facebook.com/drpedrosalles",
        n_anuncios_ativos=14,
        instagram_handle="dr.pedrosalles",
        seguidores=85_400,
        seguindo=312,
        total_posts=634,
        bio="Dermatologista | Especialista em acne e pele oleosa | CRM 145897",
        nome_completo="Dr. Pedro Salles",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010004",
        fb_page_name="Dra. Beatriz Couto Dermatologia",
        fb_page_url="https://www.facebook.com/drabeatrizcouto",
        n_anuncios_ativos=11,
        instagram_handle="dra.beatrizcouto",
        seguidores=64_200,
        seguindo=198,
        total_posts=523,
        bio="Dermatologista | Harmonizacao facial | Belo Horizonte | CRM-MG 38221",
        nome_completo="Dra. Beatriz Couto",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010005",
        fb_page_name="Espaco Derma Renato Vidal",
        fb_page_url="https://www.facebook.com/espacoderma",
        n_anuncios_ativos=9,
        instagram_handle="espaco.derma",
        seguidores=48_900,
        seguindo=156,
        total_posts=412,
        bio="Dermatologia clinica e estetica | Tratamentos de pele | Dr. Renato Vidal CRM 67234",
        nome_completo="Espaco Derma",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010006",
        fb_page_name="Dra. Mariana Tavares Dermato",
        fb_page_url="https://www.facebook.com/dramarianatavares",
        n_anuncios_ativos=8,
        instagram_handle="dra.marianatavares",
        seguidores=39_100,
        seguindo=224,
        total_posts=387,
        bio="Dermatologista | Acne, melasma e estetica | Curitiba",
        nome_completo="Dra. Mariana Tavares",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010007",
        fb_page_name="Dr. Felipe Ribas — Botox e Preenchimento",
        fb_page_url="https://www.facebook.com/drfeliperibas",
        n_anuncios_ativos=12,
        instagram_handle="dr.feliperibas",
        seguidores=72_800,
        seguindo=343,
        total_posts=701,
        bio="Medico esteta | Botox, preenchimento e harmonizacao facial | CRM 89732",
        nome_completo="Dr. Felipe Ribas",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010008",
        fb_page_name="Clinica Beleza Saudavel Multiplas Especialidades",
        fb_page_url="https://www.facebook.com/belezasaudavel",
        n_anuncios_ativos=20,
        instagram_handle="beleza.saudavel.clinica",
        seguidores=92_000,
        seguindo=512,
        total_posts=812,
        bio="Clinica multi-especialidade | Cardiologia, ortopedia, ginecologia e mais",
        nome_completo="Clinica Beleza Saudavel",
    ),  # nao deve passar no match de dermatologia: clinica generica
    FixtureAdvertiser(
        fb_page_id="1000010009",
        fb_page_name="Dr. Caio Marcos Cardio",
        fb_page_url="https://www.facebook.com/drcaiomarcos",
        n_anuncios_ativos=6,
        instagram_handle="dr.caiomarcos",
        seguidores=34_500,
        seguindo=180,
        total_posts=298,
        bio="Cardiologista | Hipertensao | Check up cardiaco",
        nome_completo="Dr. Caio Marcos",
    ),  # cardiologia, nao deve passar
    FixtureAdvertiser(
        fb_page_id="1000010010",
        fb_page_name="Dra. Helena Oka — Dermatologia Funcional",
        fb_page_url="https://www.facebook.com/drahelenaoka",
        n_anuncios_ativos=7,
        instagram_handle="dra.helenaoka",
        seguidores=28_700,
        seguindo=145,
        total_posts=276,
        bio="Dermatologia funcional | Saude da pele de dentro pra fora | CRM 76234",
        nome_completo="Dra. Helena Oka",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010011",
        fb_page_name="Dr. Joao Brasil Plastica",
        fb_page_url="https://www.facebook.com/drjoaobrasil",
        n_anuncios_ativos=15,
        instagram_handle="dr.joaobrasil",
        seguidores=156_000,
        seguindo=298,
        total_posts=1_120,
        bio="Cirurgiao plastico | Rinoplastia, mommy makeover, lipo HD",
        nome_completo="Dr. Joao Brasil",
    ),  # plastica, nao dermato
    FixtureAdvertiser(
        fb_page_id="1000010012",
        fb_page_name="Dra. Yara Sales Dermato",
        fb_page_url="https://www.facebook.com/drayarasales",
        n_anuncios_ativos=5,
        instagram_handle="dra.yarasales",
        seguidores=21_400,
        seguindo=187,
        total_posts=234,
        bio="Dermatologista | Tratamento de melasma e manchas | Recife | CRM-PE 18745",
        nome_completo="Dra. Yara Sales",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010013",
        fb_page_name="Studio MM Estetica",
        fb_page_url="https://www.facebook.com/studiommestetica",
        n_anuncios_ativos=4,
        instagram_handle="studio.mm.estetica",
        seguidores=12_800,
        seguindo=234,
        total_posts=178,
        bio="Estetica avancada | Limpeza de pele profunda | Massagem | Sem medico",
        nome_completo="Studio MM Estetica",
    ),  # sem medico, nao serve
    FixtureAdvertiser(
        fb_page_id="1000010014",
        fb_page_name="Dr. Lucas Yamamoto Tricologia",
        fb_page_url="https://www.facebook.com/drlucasy",
        n_anuncios_ativos=10,
        instagram_handle="dr.lucasy.derma",
        seguidores=44_200,
        seguindo=176,
        total_posts=412,
        bio="Tricologia (dermato do cabelo) | Queda capilar | Microagulhamento | CRM 142398",
        nome_completo="Dr. Lucas Yamamoto",
    ),
    FixtureAdvertiser(
        fb_page_id="1000010015",
        fb_page_name="Dra. Camila Saito Skin",
        fb_page_url="https://www.facebook.com/dracamilasaito",
        n_anuncios_ativos=13,
        instagram_handle="dra.camilasaito",
        seguidores=68_900,
        seguindo=234,
        total_posts=587,
        bio="Dermatologista | Skincare avancado | Sao Paulo",
        nome_completo="Dra. Camila Saito",
    ),
]


# -------------------- NUTROLOGIA --------------------

NUTROLOGIA: list[FixtureAdvertiser] = [
    FixtureAdvertiser(
        fb_page_id="2000020001",
        fb_page_name="Dr. Rafael Pinheiro Nutrologia",
        fb_page_url="https://www.facebook.com/drrafaelpinheiro",
        n_anuncios_ativos=19,
        instagram_handle="dr.rafaelpinheiro",
        seguidores=158_000,
        seguindo=287,
        total_posts=890,
        bio="Nutrologo | Emagrecimento e saude metabolica | Sao Paulo | CRM 178342",
        nome_completo="Dr. Rafael Pinheiro",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020002",
        fb_page_name="Clinica Equilibrio Nutrologico",
        fb_page_url="https://www.facebook.com/equilibrionutro",
        n_anuncios_ativos=14,
        instagram_handle="equilibrio.nutro",
        seguidores=87_500,
        seguindo=198,
        total_posts=623,
        bio="Nutrologia e emagrecimento | Ozempic, Wegovy, dieta cetogenica",
        nome_completo="Clinica Equilibrio",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020003",
        fb_page_name="Dra. Tatiana Brito Nutrologia",
        fb_page_url="https://www.facebook.com/dratatianabrito",
        n_anuncios_ativos=11,
        instagram_handle="dra.tatianabrito",
        seguidores=64_800,
        seguindo=312,
        total_posts=521,
        bio="Nutrologa | Mulher 40+ | Reposicao hormonal e emagrecimento | CRM 87234",
        nome_completo="Dra. Tatiana Brito",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020004",
        fb_page_name="Dr. Henrique Lobo Nutrologia Esportiva",
        fb_page_url="https://www.facebook.com/drhenriquelobo",
        n_anuncios_ativos=8,
        instagram_handle="dr.henriquelobo",
        seguidores=51_200,
        seguindo=176,
        total_posts=387,
        bio="Nutrologia esportiva | Hipertrofia | Atletas amadores e profissionais",
        nome_completo="Dr. Henrique Lobo",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020005",
        fb_page_name="Dra. Sara Cavalcanti — Emagrece Saudavel",
        fb_page_url="https://www.facebook.com/drasaracav",
        n_anuncios_ativos=12,
        instagram_handle="dra.saracav",
        seguidores=72_400,
        seguindo=298,
        total_posts=612,
        bio="Nutrologa | Emagrecimento saudavel | Foco em mulheres acima de 30 | CRM 89812",
        nome_completo="Dra. Sara Cavalcanti",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020006",
        fb_page_name="Influencer Fit Saudavel",
        fb_page_url="https://www.facebook.com/influencerfit",
        n_anuncios_ativos=7,
        instagram_handle="fit.saudavel.influencer",
        seguidores=215_000,
        seguindo=512,
        total_posts=1_340,
        bio="Lifestyle saudavel | Receitas | Treinos | Nao sou medica, sigo um pra emagrecer",
        nome_completo="Influencer Fit",
    ),  # influencer, nao serve
    FixtureAdvertiser(
        fb_page_id="2000020007",
        fb_page_name="Dr. Vitor Cardoso Nutro",
        fb_page_url="https://www.facebook.com/drvitorcardoso",
        n_anuncios_ativos=9,
        instagram_handle="dr.vitorcardoso",
        seguidores=42_300,
        seguindo=156,
        total_posts=298,
        bio="Nutrologo | Performance, emagrecimento e longevidade | CRM 142876",
        nome_completo="Dr. Vitor Cardoso",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020008",
        fb_page_name="Suplementos Top Saude",
        fb_page_url="https://www.facebook.com/suplementostopsaude",
        n_anuncios_ativos=24,
        instagram_handle="suplementos.topsaude",
        seguidores=89_700,
        seguindo=234,
        total_posts=712,
        bio="Loja de suplementos | Vitaminas, proteinas, queima-gordura",
        nome_completo="Suplementos Top",
    ),  # marca, nao medico
    FixtureAdvertiser(
        fb_page_id="2000020009",
        fb_page_name="Dra. Paloma Diniz — Metabolico",
        fb_page_url="https://www.facebook.com/drapalomadiniz",
        n_anuncios_ativos=10,
        instagram_handle="dra.palomadiniz",
        seguidores=58_400,
        seguindo=287,
        total_posts=489,
        bio="Nutrologa | Sindrome metabolica e diabetes | CRM-RJ 65872",
        nome_completo="Dra. Paloma Diniz",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020010",
        fb_page_name="Dr. Eduardo Macedo — Reposicao Hormonal",
        fb_page_url="https://www.facebook.com/dreduardomacedo",
        n_anuncios_ativos=6,
        instagram_handle="dr.eduardomacedo",
        seguidores=31_800,
        seguindo=145,
        total_posts=276,
        bio="Nutrologo | Reposicao hormonal masculina e feminina | Anti-aging",
        nome_completo="Dr. Eduardo Macedo",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020011",
        fb_page_name="Dra. Carla Yamada Nutrologia",
        fb_page_url="https://www.facebook.com/dracarlayamada",
        n_anuncios_ativos=5,
        instagram_handle="dra.carlayamada",
        seguidores=24_100,
        seguindo=178,
        total_posts=234,
        bio="Nutrologa | Obesidade infantil e adulto | Sao Paulo",
        nome_completo="Dra. Carla Yamada",
    ),
    FixtureAdvertiser(
        fb_page_id="2000020012",
        fb_page_name="Estetica Definitiva",
        fb_page_url="https://www.facebook.com/esteticadefinitiva",
        n_anuncios_ativos=14,
        instagram_handle="estetica.definitiva",
        seguidores=42_300,
        seguindo=312,
        total_posts=387,
        bio="Estetica e beleza | Tratamentos corporais | Sem medico responsavel",
        nome_completo="Estetica Definitiva",
    ),  # sem medico
]


# -------------------- ORTOPEDIA --------------------

ORTOPEDIA: list[FixtureAdvertiser] = [
    FixtureAdvertiser(
        fb_page_id="3000030001",
        fb_page_name="Dr. Marcos Sanches — Ortopedia do Joelho",
        fb_page_url="https://www.facebook.com/drmarcossanches",
        n_anuncios_ativos=16,
        instagram_handle="dr.marcossanches",
        seguidores=98_400,
        seguindo=287,
        total_posts=634,
        bio="Ortopedista | Especialista em joelho | Lesoes do menisco e LCA | CRM 124567",
        nome_completo="Dr. Marcos Sanches",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030002",
        fb_page_name="Dra. Luana Aoki Coluna",
        fb_page_url="https://www.facebook.com/draluanaaoki",
        n_anuncios_ativos=12,
        instagram_handle="dra.luanaaoki",
        seguidores=72_300,
        seguindo=198,
        total_posts=523,
        bio="Ortopedista de coluna | Hernia de disco | Tratamento sem cirurgia | CRM-SP 187653",
        nome_completo="Dra. Luana Aoki",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030003",
        fb_page_name="Clinica Ortotrauma BH",
        fb_page_url="https://www.facebook.com/ortotraumabh",
        n_anuncios_ativos=10,
        instagram_handle="ortotrauma.bh",
        seguidores=54_700,
        seguindo=234,
        total_posts=412,
        bio="Ortopedia e traumatologia | Belo Horizonte | Atendimento ambulatorial",
        nome_completo="Ortotrauma BH",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030004",
        fb_page_name="Dr. Rodrigo Volpato Ombro",
        fb_page_url="https://www.facebook.com/drrodrigovolpato",
        n_anuncios_ativos=8,
        instagram_handle="dr.rodrigovolpato",
        seguidores=41_200,
        seguindo=176,
        total_posts=312,
        bio="Ortopedista | Cirurgia de ombro | Tendinite e LesoesEsportivas | CRM 145897",
        nome_completo="Dr. Rodrigo Volpato",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030005",
        fb_page_name="Dr. Andre Saito — Coluna sem Cirurgia",
        fb_page_url="https://www.facebook.com/drandresaito",
        n_anuncios_ativos=14,
        instagram_handle="dr.andresaito",
        seguidores=86_500,
        seguindo=312,
        total_posts=712,
        bio="Especialista em coluna | Tratamentos minimamente invasivos | Infiltracao",
        nome_completo="Dr. Andre Saito",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030006",
        fb_page_name="Dra. Patricia Mariano Quadril",
        fb_page_url="https://www.facebook.com/drapatriciamariano",
        n_anuncios_ativos=7,
        instagram_handle="dra.patriciamariano",
        seguidores=32_400,
        seguindo=178,
        total_posts=287,
        bio="Ortopedista | Cirurgia de quadril | Artrose | Curitiba | CRM-PR 65821",
        nome_completo="Dra. Patricia Mariano",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030007",
        fb_page_name="Personal Trainer Top Fit",
        fb_page_url="https://www.facebook.com/personaltoptop",
        n_anuncios_ativos=22,
        instagram_handle="personal.toptop",
        seguidores=125_000,
        seguindo=412,
        total_posts=987,
        bio="Personal trainer | Reabilitacao funcional | Sem medico",
        nome_completo="Personal Top Fit",
    ),  # nao medico
    FixtureAdvertiser(
        fb_page_id="3000030008",
        fb_page_name="Dr. Fabricio Otsuka Joelho",
        fb_page_url="https://www.facebook.com/drfabriciootsuka",
        n_anuncios_ativos=11,
        instagram_handle="dr.fabriciootsuka",
        seguidores=62_300,
        seguindo=234,
        total_posts=487,
        bio="Ortopedista | Joelho e tornozelo | Cirurgia artroscopica | CRM 187234",
        nome_completo="Dr. Fabricio Otsuka",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030009",
        fb_page_name="Dr. Diego Almeida — Pe e Tornozelo",
        fb_page_url="https://www.facebook.com/drdiegoalmeida",
        n_anuncios_ativos=9,
        instagram_handle="dr.diegoalmeida",
        seguidores=44_100,
        seguindo=156,
        total_posts=345,
        bio="Ortopedista | Pe e tornozelo | Cirurgia minimamente invasiva | CRM 132567",
        nome_completo="Dr. Diego Almeida",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030010",
        fb_page_name="Hospital Centro Ortopedico",
        fb_page_url="https://www.facebook.com/hospitalcentroort",
        n_anuncios_ativos=28,
        instagram_handle="hospital.centro.ortopedico",
        seguidores=178_000,
        seguindo=287,
        total_posts=1_240,
        bio="Hospital especializado em ortopedia | Atendimento 24h | Cirurgia eletiva e urgencia",
        nome_completo="Hospital Centro Ortopedico",
    ),  # hospital, descartar
    FixtureAdvertiser(
        fb_page_id="3000030011",
        fb_page_name="Dra. Tamires Inacio — Esporte e Trauma",
        fb_page_url="https://www.facebook.com/dratamiresinacio",
        n_anuncios_ativos=6,
        instagram_handle="dra.tamiresinacio",
        seguidores=28_400,
        seguindo=145,
        total_posts=234,
        bio="Ortopedista esportiva | Lesoes em corrida e crossfit | CRM-DF 18765",
        nome_completo="Dra. Tamires Inacio",
    ),
    FixtureAdvertiser(
        fb_page_id="3000030012",
        fb_page_name="Dr. Bruno Quezada — Maos",
        fb_page_url="https://www.facebook.com/drbrunoquezada",
        n_anuncios_ativos=5,
        instagram_handle="dr.brunoquezada",
        seguidores=18_700,
        seguindo=187,
        total_posts=178,
        bio="Ortopedista | Especialista em maos | Tunel do carpo, sindromes | CRM 154278",
        nome_completo="Dr. Bruno Quezada",
    ),
]


# -------------------- MAPA --------------------

_MAPA: dict[str, list[FixtureAdvertiser]] = {
    "dermatologia": DERMATOLOGIA,
    "nutrologia": NUTROLOGIA,
    "ortopedia": ORTOPEDIA,
}


def disponivel(especialidade: str) -> bool:
    return _normalizar_especialidade(especialidade) in _MAPA


def carregar(especialidade: str) -> list[FixtureAdvertiser]:
    """Carrega a fixture para a especialidade. KeyError se nao existir."""
    chave = _normalizar_especialidade(especialidade)
    if chave not in _MAPA:
        raise KeyError(
            f"Sem fixture para especialidade {especialidade!r}. "
            f"Disponiveis: {list(_MAPA.keys())}"
        )
    return list(_MAPA[chave])


def especialidades_disponiveis() -> Iterable[str]:
    return _MAPA.keys()


def _normalizar_especialidade(esp: str) -> str:
    return esp.strip().lower()
