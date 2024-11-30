import os

import matplotlib.pyplot as plt
import networkx as nx
import xmltodict

# Caminho para a pasta com os arquivos XML
basepath = "C:\\Users\\Dev-Gustavo\\Documents\\GitHub\\grafosss\\curriculos\\"
curriculos = []
infos = {}


def format_autores(items, id):
    if isinstance(items, dict):
        items = [items]

    autores = []
    for autor in items:

        if autor["@NRO-ID-CNPQ"] != id:
            autores.append(
                {
                    "id": autor["@NRO-ID-CNPQ"],
                    "nome": autor["@NOME-COMPLETO-DO-AUTOR"],
                }
            )

    return autores


def format_artigos(items, id):
    if isinstance(items, dict):
        return [{"titulo": items["DADOS-BASICOS-DO-ARTIGO"]["@TITULO-DO-ARTIGO"],
                 "autores": format_autores(items["AUTORES"], id)}]

    artigos = []
    for artigo in items:
        artigos.append(
            {
                "titulo": artigo["DADOS-BASICOS-DO-ARTIGO"]["@TITULO-DO-ARTIGO"],
                "autores": format_autores(artigo["AUTORES"], id),
            }
        )

    return artigos


def format_orientacoes(items, type):
    if isinstance(items, dict):
        obj = [{
            "titulo": items[f"DADOS-BASICOS-DE-ORIENTACOES-CONCLUIDAS-PARA-{type}"]["@TITULO"],
            "orientado": items[f"DETALHAMENTO-DE-ORIENTACOES-CONCLUIDAS-PARA-{type}"]["@NOME-DO-ORIENTADO"]
        }]
        return obj

    orientacoes = []
    for orientacao in items:
        orientacoes.append(
            {
                "titulo": orientacao[f"DADOS-BASICOS-DE-ORIENTACOES-CONCLUIDAS-PARA-{type}"]["@TITULO"],
                "orientado": orientacao[f"DETALHAMENTO-DE-ORIENTACOES-CONCLUIDAS-PARA-{type}"]["@NOME-DO-ORIENTADO"]
            }
        )

    return orientacoes


for filename in os.listdir(basepath):
    with open(basepath + filename, "r+") as file:
        curriculos.append(xmltodict.parse(file.read()))

for curriculo in curriculos:
    id = curriculo["CURRICULO-VITAE"]["@NUMERO-IDENTIFICADOR"]
    nome = curriculo["CURRICULO-VITAE"]["DADOS-GERAIS"]["@NOME-COMPLETO"]
    infos[id] = {
        "nome": nome,
        "artigos": [],
        "orientandos": {
            "mestrado": [],
            "doutorado": [],
        },
    }

    artigos = list(filter(lambda x: x["DADOS-BASICOS-DO-ARTIGO"]["@NATUREZA"] == "COMPLETO",
                          curriculo["CURRICULO-VITAE"]["PRODUCAO-BIBLIOGRAFICA"]["ARTIGOS-PUBLICADOS"][
                              "ARTIGO-PUBLICADO"]))
    infos[id]["artigos"] = format_artigos(artigos, id)

    if (orientacoes := curriculo["CURRICULO-VITAE"]["OUTRA-PRODUCAO"]["ORIENTACOES-CONCLUIDAS"].get(
            "ORIENTACOES-CONCLUIDAS-PARA-MESTRADO", False)):
        infos[id]["orientandos"]["mestrado"] = format_orientacoes(orientacoes, "MESTRADO")

    if (orientacoes := curriculo["CURRICULO-VITAE"]["OUTRA-PRODUCAO"]["ORIENTACOES-CONCLUIDAS"].get(
            "ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO", False)):
        infos[id]["orientandos"]["doutorado"] = format_orientacoes(orientacoes, "DOUTORADO")

g = nx.Graph()

for k, v in infos.items():
    for a in v['artigos']:
        for i in a['autores']:
            g.add_edge(v['nome'], i['nome'])

pos = nx.spring_layout(g, k=1)
nx.draw_networkx_nodes(g, pos)
# nx.draw_networkx_labels(g, pos)
nx.draw_networkx_edges(g, pos)

plt.show()
