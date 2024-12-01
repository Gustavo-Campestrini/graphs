"""
EQUIPE:
 - LUCAS DE FARIAS TEIXEIRA
 - GUSTAVO CAMPESTRINI
 - NICOLAS CERUTTI
"""
import xmltodict
import os
import networkx as nx
import unicodedata
import matplotlib.pyplot as plt
import re
from typing import Literal

# caminho dos curriculos no sistema de arquivos
basepath = "/home/magalu/sandbox/graphs/curriculos/"

# inicializa algumas variaveis necessarias para a execucao
curriculos = []
pesquisadores = {}
todos_autores = {}
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


def inicia_autores_curriculos(curriculos: list[dict]) -> None:
    """
    Insere os pesquisadores dos currículos fornecidos no dicionário 'todos_autores'.
    Essa inserção é feita para registrar o nome fornecido nos currículos, o que depois facilita a inserção de vértices com cores
    diferentes, que permitem destacar esses pesquisadores.

    Args:
        curriculos (list[str]): Curriculos dos pesquisadores que são base do trabalho.
    """
    for curriculo in curriculos:
        id = curriculo["CURRICULO-VITAE"]["@NUMERO-IDENTIFICADOR"]
        nome = remove_acentos(curriculo["CURRICULO-VITAE"]["DADOS-GERAIS"]["@NOME-COMPLETO"]).lower()
        primeira_citacao = remove_acentos(curriculo["CURRICULO-VITAE"]["DADOS-GERAIS"]["@NOME-EM-CITACOES-BIBLIOGRAFICAS"]).split(";")[0]
        todos_autores[primeira_citacao] = {"id": id, "nome": nome}


def busca_ou_registra_autor(autor: dict) -> dict:
    """
    Procura o autor dentro do dicionário 'todos_autores', se baseando em seus nomes para citação, seu ID e seu nome.
    Como os nomes podem possuir várias variações, são feitas algumas verificações (que não garantem a não duplicidade do mesmo indivíduo).
    Caso o autor não seja encontrado, ele é inserido no dicionário.
    Por fim, os dados do autor são retornados pela função.

    Args:
        autor (str): Autor para ser procurado ou registrado.

    Returns:
        dict (dict of str: str): Dados do autor.
    """
    global id_cont
    id = autor["@NRO-ID-CNPQ"]
    nome_autor = remove_acentos(autor["@NOME-COMPLETO-DO-AUTOR"]).lower().replace("-", " ")
    if "," in nome_autor:
        nomes = nome_autor.split(",")
        nome_autor = nomes[1].strip() + " " + nomes[0].strip()
        
    nomes_citacao = remove_acentos(autor["@NOME-PARA-CITACAO"]).replace("-", " ").split(";")
    for k, v in todos_autores.items():
        nomes = nome_autor.split()
        nome = nomes[0]
        sobrenome = nomes[-1]
        pattern = f"{nome} ([a-z]+ )*{sobrenome}( [a-z]+ ?)*"
        if k in nomes_citacao or v["nome"] == nome_autor or v["id"] == id or re.search(pattern, v["nome"]):
            return {"id": v["id"], "nome": v["nome"]}
    else:
        id = autor["@NRO-ID-CNPQ"]
        if id == "":
            id = str(id_cont)
            id_cont += 1

        autor_obj = {"id": id, "nome": nome_autor} 
        todos_autores[nomes_citacao[0]] = autor_obj
        return autor_obj
            

def formata_autores(items: list[dict] | dict) -> list[dict]:
    """
    Recebe o(s) autor(es) e retorna em um formato reduzido, apenas com as informações necessárias.

    Args:
        items (list(dict) | dict): Um ou mais autores para serem formatados

    Returns:
        list(dict): Autores formatos com informações reduzidas e padronizadas.
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
    if isinstance(items, dict):
        obj = [{
            "titulo": items[f"DADOS-BASICOS-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@TITULO"],
            "orientado": items[f"DETALHAMENTO-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@NOME-DO-ORIENTADO"]
        }]
        return obj
    
    orientacoes = []
    for orientacao in items:
        orientacoes.append(
            {
                "titulo": orientacao[f"DADOS-BASICOS-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@TITULO"],
                "orientado": orientacao[f"DETALHAMENTO-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@NOME-DO-ORIENTADO"]
            }
        )

    return orientacoes


for filename in os.listdir(basepath):
    with open(basepath + filename, "r+", encoding="iso-8859-1") as file:
        curriculos.append(xmltodict.parse(file.read(), encoding="iso-8859-1"))

inicia_autores_curriculos(curriculos)

for curriculo in curriculos:
    id = curriculo["CURRICULO-VITAE"]["@NUMERO-IDENTIFICADOR"]
    nome = remove_acentos(curriculo["CURRICULO-VITAE"]["DADOS-GERAIS"]["@NOME-COMPLETO"]).lower()
    primeira_citacao = remove_acentos(curriculo["CURRICULO-VITAE"]["DADOS-GERAIS"]["@NOME-EM-CITACOES-BIBLIOGRAFICAS"]).split(";")[0]
    pesquisadores[id] = {
        "nome": nome,
        "artigos": [],
        "orientandos": {
            "mestrado": [],
            "doutorado": [],
        },
    }

    artigos = list(filter(lambda x: x["DADOS-BASICOS-DO-ARTIGO"]["@NATUREZA"] == "COMPLETO", curriculo["CURRICULO-VITAE"]["PRODUCAO-BIBLIOGRAFICA"]["ARTIGOS-PUBLICADOS"]["ARTIGO-PUBLICADO"]))
    pesquisadores[id]["artigos"] = formata_artigos(artigos)

    if (orientacoes := curriculo["CURRICULO-VITAE"]["OUTRA-PRODUCAO"]["ORIENTACOES-CONCLUIDAS"].get("ORIENTACOES-CONCLUIDAS-PARA-MESTRADO", False)):
        pesquisadores[id]["orientandos"]["mestrado"] = formata_orientacoes(orientacoes, "MESTRADO")
    
    if (orientacoes := curriculo["CURRICULO-VITAE"]["OUTRA-PRODUCAO"]["ORIENTACOES-CONCLUIDAS"].get("ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO", False)):
        pesquisadores[id]["orientandos"]["doutorado"] = formata_orientacoes(orientacoes, "DOUTORADO")

g = nx.Graph()

color_map = []
label_list = {}

for k, v in pesquisadores.items():
    g.add_node(v["nome"])
    color_map.append("yellow")
    label_list[v["nome"]] = v["nome"]

for k, v in pesquisadores.items():
    for a in v["artigos"]:
        for i in a["autores"]:
            for j in a["autores"]:
                if i["nome"] == j["nome"]:
                    continue

                if not g.has_node(i["nome"]):                  
                    g.add_node(i["nome"], weight=1)
                    color_map.append("blue")

                if not g.has_node(j["nome"]):                  
                    g.add_node(j["nome"], weight=1)
                    color_map.append("green")

                g.add_edge(i["nome"], j["nome"])

pos = nx.kamada_kawai_layout(g, scale=2, dim=2)
nx.draw_networkx_nodes(g, pos, node_size=50, node_color=color_map)
nx.draw_networkx_edges(g, pos)
_ = nx.draw_networkx_labels(g, pos, labels=label_list, font_color="red")
plt.show()
