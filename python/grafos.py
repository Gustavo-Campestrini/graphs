"""
EQUIPE:
 - LUCAS DE FARIAS TEIXEIRA
 - GUSTAVO HENRIQUE CAMPESTRINI
 - NICOLAS ANDREI CERUTTI
"""
import xmltodict
import os
import networkx as nx
import unicodedata
import matplotlib.pyplot as plt
import re
from typing import Literal

# consts
MESTRADO = "MESTRADO"
DOUTORADO = "DOUTORADO"

# caminho dos curriculos no sistema de arquivos
basepath = "./curriculos/"

# inicializa algumas variaveis necessarias para a execucao
curriculos = []
todos_pesquisadores = {}
todos_autores = {}
todos_orientados_mestrado = {}
todos_orientados_doutorado = {}
bases_orientados = {
    MESTRADO: todos_orientados_mestrado,
    DOUTORADO: todos_orientados_doutorado,
}
id_cont = 1


def remove_acentos(texto: str) -> str:
    """
    Remove acentos do texto

    Args:
        texto (str): Texto para remover os acentos.

    Returns:
        str: Texto sem acentos

    Obs: Utiliza o encoding ISO-8859-1 por estar lidando com XMLs que utilizam esse padrão
    """
    nfkd_form = unicodedata.normalize('NFKD', texto)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode(encoding="iso-8859-1")


def normaliza_nome(nome: str) -> str:
    nome = remove_acentos(nome).lower().replace("-", " ")
    if "," in nome:
        nomes = nome.split(",")
        nome = nomes[1].strip() + " " + nomes[0].strip()
        
    return nome


def autor_ou_pesquisador_existe_na_base(id: str, nome: str, nomes_citacao: list[str], base: dict):
    for k, v in base.items():
        nomes = nome.split()
        primeiro_nome = nomes[0]
        sobrenome = nomes[-1]
        pattern = f"{primeiro_nome} ([a-z]+ )*{sobrenome}( [a-z]+ ?)*"
        nomes_citacao_em_comum = len(set(v["nomes_citacao"]).intersection(set(nomes_citacao)))
        if k == nome or re.search(pattern, k) or nomes_citacao_em_comum > 0 or v["id"] == id:
            return k, True
        
    return "", False


def nome_existe_na_base(nome: str, base: dict):
    for k in base.keys():
        nomes = nome.split()
        primeiro_nome = nomes[0]
        sobrenome = nomes[-1]
        pattern = f"{primeiro_nome} ([a-z]+ )*{sobrenome}( [a-z]+ ?)*"
        if k == nome or re.search(pattern, k):
            return k, True
        
    return "", False


def pesquisa_orientado_nas_bases(nome: str) -> str:
    nome_encontrado, ok = nome_existe_na_base(nome, todos_pesquisadores)
    if ok:
        return nome_encontrado
    
    nome_encontrado, ok = nome_existe_na_base(nome, todos_autores)
    if ok:
        return nome_encontrado
    
    nome_encontrado, ok = nome_existe_na_base(nome, todos_orientados_mestrado)
    if ok:
        return nome_encontrado
    
    nome_encontrado, ok = nome_existe_na_base(nome, todos_orientados_doutorado)
    if ok:
        return nome_encontrado

    return nome

def busca_ou_registra_autor(autor: dict) -> dict:
    """
    Procura o autor dentro do dicionário 'todos_autores', se baseando em seus nomes para citação, seu ID e seu nome.
    Como os nomes podem possuir várias variações, são feitas algumas verificações (que não garantem a não duplicidade do mesmo indivíduo).
    Caso o autor não seja encontrado, ele é inserido no dicionário.
    Por fim, o nome do autor são retornados pela função.

    Args:
        autor (str): Autor para ser procurado ou registrado.

    Returns:
        str: Nome do autor.
    """
    global id_cont
    id = autor["@NRO-ID-CNPQ"]
    nome_autor = normaliza_nome(autor["@NOME-COMPLETO-DO-AUTOR"])
    nomes_citacao = remove_acentos(autor["@NOME-PARA-CITACAO"]).replace("-", " ").split(";")
    nome, ok = autor_ou_pesquisador_existe_na_base(id, nome_autor, nomes_citacao, todos_pesquisadores)
    if ok:
        return nome
    
    nome, ok = autor_ou_pesquisador_existe_na_base(id, nome_autor, nomes_citacao, todos_autores)
    if ok:
        return nome
    
    id = autor["@NRO-ID-CNPQ"]
    if id == "":
        id = str(id_cont)
        id_cont += 1

    autor_obj = {"id": id, "nomes_citacao": nomes_citacao} 
    todos_autores[nome_autor] = autor_obj
    return nome_autor
            

def formata_autores(items: list[dict] | dict) -> list[dict]:
    """
    Recebe o(s) autor(es) e retorna em um formato reduzido, apenas com as informações necessárias.

    Args:
        items (list(dict) | dict): Um ou mais autores para serem formatados

    Returns:
        list(dict): Nomes formatados dos autores.
    """
    if isinstance(items, dict):
        items = [items]
    
    return [busca_ou_registra_autor(autor) for autor in items]


def formata_artigos(items: list[dict] | dict) -> list[dict]:
    """
    Recebe o(s) artigo(s) e retorna em um formato reduzido, apenas com as informações necessárias.

    Args:
        items (list(dict) | dict): Um ou mais artigos para serem formatados

    Returns:
        list(dict): Artigos formatos com informações reduzidas e padronizadas.
    """
    if isinstance(items, dict):
        return [{"titulo": items["DADOS-BASICOS-DO-ARTIGO"]["@TITULO-DO-ARTIGO"], "autores": formata_autores(items["AUTORES"])}]
    
    artigos = []
    for artigo in items:
        artigos.append(
            {
                "titulo": artigo["DADOS-BASICOS-DO-ARTIGO"]["@TITULO-DO-ARTIGO"],
                "autores": formata_autores(artigo["AUTORES"]),
            }
        )

    return artigos


def formata_orientacoes(items: list[dict] | dict, tipo: Literal["MESTRADO", "DOUTORADO"]) -> list[dict]:
    """
    Recebe a(s) orientação(ões) e retorna em um formato reduzido, apenas com as informações necessárias.

    Args:
        items (list(dict) | dict): Uma ou mais orientações para serem formatados
        tipo (Literal["MESTRADO", "DOUTORADO"]): O tipo das orientações

    Returns:
        list(dict): Orientações formatos com informações reduzidas e padronizadas.
    """
    base = bases_orientados[tipo]

    if isinstance(items, dict):
        items = [items]
    
    orientacoes = []
    for orientacao in items:
        titulo = orientacao[f"DADOS-BASICOS-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@TITULO"]
        nome = normaliza_nome(orientacao[f"DETALHAMENTO-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@NOME-DO-ORIENTADO"])
        nome = pesquisa_orientado_nas_bases(nome)
        base[nome] = True
        orientacoes.append(
            {
                "titulo": titulo,
                "orientado": nome,
            }
        )
        
    return orientacoes


def inicia_pesquisadores(curriculos: list[dict]) -> None:
    """
    Insere os pesquisadores dos currículos fornecidos no dicionário 'todos_autores'.
    Essa inserção é feita para registrar o nome fornecido nos currículos, o que depois facilita a inserção de vértices com cores
    diferentes, que permitem destacar esses pesquisadores.

    Args:
        curriculos (list[str]): Curriculos dos pesquisadores que são base do trabalho.
    """
    for curriculo in curriculos:
        id = curriculo["CURRICULO-VITAE"]["@NUMERO-IDENTIFICADOR"]
        nome = normaliza_nome(curriculo["CURRICULO-VITAE"]["DADOS-GERAIS"]["@NOME-COMPLETO"])
        nomes_citacao = remove_acentos(curriculo["CURRICULO-VITAE"]["DADOS-GERAIS"]["@NOME-EM-CITACOES-BIBLIOGRAFICAS"]).split(";")
        todos_pesquisadores[nome] = {
            "id": id,
            "nomes_citacao": nomes_citacao,
            "artigos": [],
            "orientandos": {
                "mestrado": [],
                "doutorado": [],
            },
        }

        artigos = list(filter(lambda x: x["DADOS-BASICOS-DO-ARTIGO"]["@NATUREZA"] == "COMPLETO", curriculo["CURRICULO-VITAE"]["PRODUCAO-BIBLIOGRAFICA"]["ARTIGOS-PUBLICADOS"]["ARTIGO-PUBLICADO"]))
        todos_pesquisadores[nome]["artigos"] = formata_artigos(artigos)

        if (orientacoes := curriculo["CURRICULO-VITAE"]["OUTRA-PRODUCAO"]["ORIENTACOES-CONCLUIDAS"].get("ORIENTACOES-CONCLUIDAS-PARA-MESTRADO", False)):
            todos_pesquisadores[nome]["orientandos"]["mestrado"] = formata_orientacoes(orientacoes, "MESTRADO")
        
        if (orientacoes := curriculo["CURRICULO-VITAE"]["OUTRA-PRODUCAO"]["ORIENTACOES-CONCLUIDAS"].get("ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO", False)):
            todos_pesquisadores[nome]["orientandos"]["doutorado"] = formata_orientacoes(orientacoes, "DOUTORADO")


for filename in os.listdir(basepath):
    if filename == "2060996038464074.xml":
        with open(basepath + filename, "r+", encoding="iso-8859-1") as file:
            curriculos.append(xmltodict.parse(file.read(), encoding="iso-8859-1"))

inicia_pesquisadores(curriculos)

g = nx.Graph()

label_list = {}

pesquisadores_node_list = []
outros_individuos_node_list = []

# adiciona pesquisadores como nodes
for k, v in todos_pesquisadores.items():
    g.add_node(k)
    pesquisadores_node_list.append(k)
    #label_list[k] = k

# adiciona autores como nodes
for k, v in todos_pesquisadores.items():
    for a in v["artigos"]:
        for i in a["autores"]:
            for j in a["autores"]:
                if i == j:
                    continue

                if not g.has_node(i):                  
                    g.add_node(i, weight=1)
                    outros_individuos_node_list.append(i)

                if not g.has_node(j):                  
                    g.add_node(j, weight=1)
                    outros_individuos_node_list.append(j)

                g.add_edge(i, j)

# adiciona orientandos como nodes
for k, v in todos_pesquisadores.items():
    for orientacao in v["orientandos"]["mestrado"]:
        if not g.has_node(orientacao["orientado"]):
            g.add_node(orientacao["orientado"], weight=1)
            outros_individuos_node_list.append(orientacao["orientado"])
            g.add_edge(k, orientacao["orientado"])

    for orientacao in v["orientandos"]["doutorado"]:
        if not g.has_node(orientacao["orientado"]):
            g.add_node(orientacao["orientado"], weight=1)
            outros_individuos_node_list.append(orientacao["orientado"])
            g.add_edge(k, orientacao["orientado"])

node_colors = []

for node in g.nodes:
    is_pesquisador = node in todos_pesquisadores.keys()
    if is_pesquisador:
        continue

    is_coautor = node in todos_autores.keys()
    is_mestrado = node in todos_orientados_mestrado.keys()
    is_doutorado = node in todos_orientados_doutorado.keys()

    # Definir a cor com base nas condições
    if is_coautor and is_mestrado and is_doutorado:
        node_colors.append("orange")  # Coautor, mestrado e doutorado
    elif is_coautor and is_mestrado:
        node_colors.append("purple")  # Coautor e mestrado
    elif is_coautor and is_doutorado:
        node_colors.append("green")  # Coautor e doutorado
    elif is_mestrado and is_doutorado:
        node_colors.append("brown")  # Mestrado e doutorado
    elif is_coautor:
        node_colors.append("blue")  # Apenas coautor
    elif is_mestrado:
        node_colors.append("red")  # Apenas mestrado
    elif is_doutorado:
        node_colors.append("yellow")  # Apenas doutorado

label_list = {node: node for node in g.nodes}
pos = nx.kamada_kawai_layout(g, scale=2, dim=2)
nx.draw_networkx_nodes(g, pos, node_size=100, nodelist=pesquisadores_node_list, node_color="gray")
nx.draw_networkx_nodes(g, pos, node_size=50, nodelist=outros_individuos_node_list, node_color=node_colors)
nx.draw_networkx_edges(g, pos)
_ = nx.draw_networkx_labels(g, pos, labels=label_list, font_color="red")
plt.show()

# pesquisador analisado = cinza
# co-autores = azul
# mestrado = vermelho
# doutorado = amarelo
# co-autores && mestrado = roxo
# co-autores && doutorado = verde
# mestrado && doutorado = marrom
# co-autores && doutorado && mestrado = laranja
