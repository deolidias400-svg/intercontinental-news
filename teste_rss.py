
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import html
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path


# ============================================================
# INTERCONTINENTAL NEWS
# MOTOR DE NOTÍCIAS
# ============================================================

URL_RSS = (
    "https://agenciabrasil.ebc.com.br/"
    "feed/ultimasnoticias/feed.xml"
)

ARQUIVO_SAIDA = Path(__file__).resolve().parent / "noticias.json"

EDITORIAS = [
    "Brasil",
    "Mundo",
    "Economia",
    "Esportes",
    "Ciência e Tecnologia",
    "Política"
]


# ============================================================
# LIMPEZA DE TEXTO
# ============================================================

def limpar_texto(texto):
    """Remove espaços extras e converte entidades HTML."""
    if texto is None:
        return ""

    texto = html.unescape(str(texto))
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ============================================================
# LEITURA DO RSS
# ============================================================

def obter_noticias():
    """Baixa e interpreta as notícias do feed da Agência Brasil."""
    requisicao = urllib.request.Request(
        URL_RSS,
        headers={
            "User-Agent": "IntercontinentalNews/1.0"
        }
    )

    with urllib.request.urlopen(
        requisicao,
        timeout=30
    ) as resposta:
        conteudo = resposta.read()

    raiz = ET.fromstring(conteudo)

    noticias = []

    # O feed da Agência Brasil utiliza RSS/XML.
    itens = raiz.findall(".//item")

    # Compatibilidade caso o feed venha em formato Atom.
    if not itens:
        namespace = {
            "atom": "http://www.w3.org/2005/Atom"
        }

        itens = raiz.findall(".//atom:entry", namespace)

        for item in itens:
            titulo = item.findtext(
                "atom:title",
                default="",
                namespaces=namespace
            )

            descricao = item.findtext(
                "atom:content",
                default="",
                namespaces=namespace
            )

            if not descricao:
                descricao = item.findtext(
                    "atom:summary",
                    default="",
                    namespaces=namespace
                )

            link_elemento = item.find(
                "atom:link",
                namespace
            )

            link = ""
            if link_elemento is not None:
                link = link_elemento.get("href", "")

            data = item.findtext(
                "atom:updated",
                default="",
                namespaces=namespace
            )

            autor = item.findtext(
                "atom:author/atom:name",
                default="",
                namespaces=namespace
            )

            categoria = ""

            categoria_elemento = item.find(
                "atom:category",
                namespace
            )

            if categoria_elemento is not None:
                categoria = categoria_elemento.get(
                    "term",
                    ""
                )

            if titulo and link:
                noticias.append({
                    "titulo": limpar_texto(titulo),
                    "descricao": descricao or "",
                    "data": limpar_texto(data),
                    "autor": limpar_texto(autor),
                    "categoria_original": limpar_texto(categoria),
                    "link": limpar_texto(link)
                })

        return noticias

    # Leitura tradicional do RSS.
    for item in itens:
        titulo = item.findtext("title", default="")
        descricao = item.findtext("description", default="")
        link = item.findtext("link", default="")
        data = item.findtext("pubDate", default="")
        autor = item.findtext(
            "{http://purl.org/dc/elements/1.1/}creator",
            default=""
        )

        # Preserva a descrição HTML original da notícia.
        # Não usar limpar_texto na descrição.
        categorias = item.findall("category")

        categoria = ""
        if categorias:
            categoria = limpar_texto(
                categorias[0].text or ""
            )

        if not titulo or not link:
            continue

        noticias.append({
            "titulo": limpar_texto(titulo),
            "descricao": descricao or "",
            "data": limpar_texto(data),
            "autor": limpar_texto(autor),
            "categoria_original": categoria,
            "link": limpar_texto(link)
        })

    return noticias


# ============================================================
# CLASSIFICAÇÃO DAS EDITORIAS
# ============================================================

def identificar_editoria(noticia):
    """Classifica pelo assunto, categoria e URL."""

    categoria = limpar_texto(
        noticia.get("categoria_original", "")
    ).lower()

    link = limpar_texto(
        noticia.get("link", "")
    ).lower()

    titulo = limpar_texto(
        noticia.get("titulo", "")
    ).lower()

    texto = f"{categoria} {titulo} {link}"

    # 1. Categorias específicas que são fortes indicadores.

    if any(p in categoria for p in (
        "esporte",
        "futebol",
        "olimp",
        "paralímp",
        "paralimp"
    )):
        return "Esportes"

    if any(p in categoria for p in (
        "economia",
        "econôm",
        "econom",
        "finanças",
        "mercado financeiro"
    )):
        return "Economia"

    if any(p in categoria for p in (
        "ciência",
        "ciencia",
        "tecnologia",
        "inovação",
        "inovacao"
    )):
        return "Ciência e Tecnologia"

    if any(p in categoria for p in (
        "mundo",
        "internacional",
        "exterior"
    )):
        return "Mundo"

    # 2. Economia pelo título ou categoria.

    if any(p in texto for p in (
        "dólar",
        "dolar",
        "bolsa de valores",
        "bolsa sobe",
        "bolsa cai",
        "inflação",
        "inflacao",
        "pib",
        "juros",
        "taxa selic",
        "mercado financeiro",
        "exportação",
        "exportacao",
        "importação",
        "importacao",
        "desemprego",
        "óleo diesel",
        "oleo diesel",
        "atividade econômica",
        "atividade economica",
        "crescimento econômico",
        "crescimento economico",
        "mercado de trabalho",
        "contas públicas",
        "contas publicas"
    )):
        return "Economia"

    # 3. Esportes pelo título.

    if any(p in texto for p in (
        "futebol",
        "brasileirão",
        "brasileirao",
        "campeonato brasileiro",
        "seleção brasileira",
        "selecao brasileira",
        "atleta",
        "medalha",
        "mundial de judô",
        "mundial de judo",
        "paralímpico",
        "paralimpico",
        "wta ",
        "grand prix",
        "fórmula 1",
        "formula 1",
        "gp de ",
        "tênis",
        "tenis",
        "campeonato mundial",
        "copa do mundo",
        "basquete",
        "vôlei",
        "volei"
    )):
        return "Esportes"

    # 4. Ciência e Tecnologia.

    if any(p in texto for p in (
        "inteligência artificial",
        "inteligencia artificial",
        "tecnologia",
        "cientista",
        "pesquisa científica",
        "pesquisa cientifica",
        "estudo científico",
        "estudo cientifico",
        "astronomia",
        "descoberta científica",
        "descoberta cientifica",
        "inovação tecnológica",
        "inovacao tecnologica",
        "exploração espacial",
        "exploracao espacial",
        "computação quântica",
        "computacao quantica",
        "robótica",
        "robotica"
    )):
        return "Ciência e Tecnologia"

    # 5. Mundo: acontecimentos internacionais.

    if any(p in texto for p in (
        "guerra na",
        "conflito internacional",
        "união europeia",
        "uniao europeia",
        "casa branca",
        "eleição nos estados unidos",
        "eleicao nos estados unidos",
        "presidente dos estados unidos",
        "governo argentino",
        "governo francês",
        "governo frances",
        "governo chinês",
        "governo chines",
        "conselho de segurança da onu",
        "conflito no oriente médio",
        "conflito no oriente medio"
    )):
        return "Mundo"

    # 6. Política e Justiça eleitoral.
    # A categoria original tem prioridade sobre palavras genéricas
    # como "ministro" ou "governo".

    if categoria in (
        "política",
        "politica",
        "justiça",
        "justica"
    ):
        return "Política"

    if any(p in texto for p in (
        "eleição",
        "eleicao",
        "eleições",
        "eleicoes",
        "deputado",
        "senador",
        "congresso nacional",
        "câmara dos deputados",
        "camara dos deputados",
        "senado federal",
        "presidente da república",
        "presidente da republica",
        "partido político",
        "partido politico",
        "tribunal superior eleitoral",
        "supremo tribunal federal",
        "polícia federal",
        "policia federal",
        "justiça eleitoral",
        "justica eleitoral",
        "votação no senado",
        "votacao no senado",
        "parlamentar",
        "urna eletrônica",
        "urna eletronica",
        "tse",
        "stf",
        "mpf"
    )):
        return "Política"

    # 7. Utilizar a URL como critério complementar.
    # Evita que uma notícia ambiental seja classificada como
    # Política apenas por mencionar um ministro.

    caminho = re.search(
        r"agenciabrasil\.ebc\.com\.br/([^/?#]+)",
        link
    )

    if caminho:
        secao_url = caminho.group(1)

        if secao_url in ("politica", "justica"):
            return "Política"

        if secao_url in ("esportes", "esporte"):
            return "Esportes"

        if secao_url == "economia":
            return "Economia"

        if secao_url in ("ciencia", "tecnologia"):
            return "Ciência e Tecnologia"

        if secao_url in ("internacional", "mundo"):
            return "Mundo"

    # 8. Demais notícias nacionais.
    return "Brasil"


# ============================================================
# ORGANIZAÇÃO DAS NOTÍCIAS
# ============================================================

def ordenar_noticias(noticias):
    """Classifica e organiza as notícias por editoria."""

    agrupadas = {
        editoria: []
        for editoria in EDITORIAS
    }

    for noticia in noticias:
        editoria = identificar_editoria(noticia)

        noticia["editoria"] = editoria

        agrupadas[editoria].append(noticia)

    # Notícias mais recentes primeiro.
    for editoria in EDITORIAS:
        agrupadas[editoria].sort(
            key=lambda noticia: converter_data(
                noticia.get("data", "")
            ),
            reverse=True
        )

    return agrupadas


# ============================================================
# CONVERSÃO DE DATA PARA ORDENAÇÃO
# ============================================================

def converter_data(data):
    """Converte datas RSS para permitir ordenação."""

    if not data:
        return datetime.min

    try:
        data_convertida = parsedate_to_datetime(data)

        if data_convertida.tzinfo is not None:
            data_convertida = data_convertida.replace(
                tzinfo=None
            )

        return data_convertida

    except (TypeError, ValueError, OverflowError):
        pass

    try:
        return datetime.fromisoformat(
            data.replace("Z", "+00:00")
        ).replace(tzinfo=None)

    except (TypeError, ValueError, OverflowError):
        return datetime.min


# ============================================================
# GERAÇÃO DA EDIÇÃO
# ============================================================

def gerar_edicao(agrupadas):
    """Mantém a estrutura JSON utilizada pelas páginas HTML."""

    edicao = []

    for editoria in EDITORIAS:
        lista = agrupadas.get(editoria, [])

        manchete = lista[0] if lista else None
        secundarias = lista[1:4] if len(lista) > 1 else []

        edicao.append({
            "editoria": editoria,
            "quantidade": len(lista),
            "manchete": manchete,
            "secundarias": secundarias
        })

    return edicao


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():
    print("=" * 54)
    print("INTERCONTINENTAL NEWS")
    print("MOTOR DE NOTICIAS")
    print("=" * 54)

    try:
        noticias = obter_noticias()

        if not noticias:
            print("Nenhuma notícia foi encontrada no RSS.")
            return

        print(f"\nNOTICIAS RECEBIDAS: {len(noticias)}")

        agrupadas = ordenar_noticias(noticias)

        print("\nQUANTIDADE POR EDITORIA:\n")

        for editoria in EDITORIAS:
            quantidade = len(agrupadas[editoria])

            print(
                f"{editoria}: {quantidade} noticia(s)"
            )

        edicao = gerar_edicao(agrupadas)

        # Gera primeiro um arquivo temporário.
        # Só substitui o JSON principal depois de concluir
        # a gravação, para reduzir o risco de perder o arquivo.
        arquivo_temporario = ARQUIVO_SAIDA.with_name(
            "noticias.tmp"
        )

        with open(
            arquivo_temporario,
            "w",
            encoding="utf-8"
        ) as arquivo:
            json.dump(
                edicao,
                arquivo,
                ensure_ascii=False,
                indent=2
            )

        arquivo_temporario.replace(ARQUIVO_SAIDA)

        print("\n" + "=" * 54)
        print(f"ARQUIVO GERADO: {ARQUIVO_SAIDA.name}")
        print(f"EDITORIAS PROCESSADAS: {len(edicao)}")
        print("EDICAO GERADA COM SUCESSO!")
        print("=" * 54)

    except Exception as erro:
        print("\nERRO AO ATUALIZAR O JORNAL:")
        print(erro)
        print(
            "\nConfira a conexão com a internet e tente novamente."
        )


if __name__ == "__main__":
    main()
