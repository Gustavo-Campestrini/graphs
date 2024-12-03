"""
EQUIPE:
 - LUCAS DE FARIAS TEIXEIRA
 - GUSTAVO CAMPESTRINI
 - NICOLAS CERUTI
"""
import xmltodict
import os
import networkx as nx
import unicodedata
import matplotlib.pyplot as plt
import re
import community.community_louvain as community_louvain
from typing import Literal
import community.community_louvain as community_louvain
import matplotlib.cm as cm
from itertools import combinations

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
coautoria_frequente = {}
label_list = {}
pesquisadores_node_list = []
autores_node_list = []
orientados_mestrado_node_list = []
orientados_doutorado_node_list = []
autores_orientados_node_list = []
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


def existe_na_base(id: str, nome: str, nomes_citacao: list[str], base: dict):
    for k, v in base.items():
        nomes = nome.split()
        nome = nomes[0]
        sobrenome = nomes[-1]
        pattern = f"{nome} ([a-z]+ )*{sobrenome}( [a-z]+ ?)*"
        nomes_citacao_em_comum = len(set(v["nomes_citacao"]).intersection(set(nomes_citacao)))
        if k == nome or re.search(pattern, k) or nomes_citacao_em_comum > 0 or v["id"] == id:
            return k, True
        
    return "", False


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
    k, ok = existe_na_base(id, nome_autor, nomes_citacao, todos_pesquisadores)
    if ok:
        return k
    
    k, ok = existe_na_base(id, nome_autor, nomes_citacao, todos_autores)
    if ok:
        return k
    
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
    if isinstance(items, dict):
        items = [items]
    
    orientacoes = []
    for orientacao in items:
        titulo = orientacao[f"DADOS-BASICOS-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@TITULO"]
        nome = normaliza_nome(orientacao[f"DETALHAMENTO-DE-ORIENTACOES-CONCLUIDAS-PARA-{tipo}"]["@NOME-DO-ORIENTADO"])
        orientacoes.append(
            {
                "titulo": titulo,
                "orientado": nome,
            }
        )

        if tipo == "MESTRADO":
            todos_orientados_mestrado[nome] = True
        else:
            todos_orientados_doutorado[nome] = True
        
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


def adiciona_aresta(g: nx.Graph, u: str, v: str):
    g.add_edge(u, v)


def adiciona_aresta_e_contabiliza_relacao(g: nx.Graph, u: str, v: str):
    g.add_edge(u, v)
    pair = tuple(sorted([u, v]))
    if pair in coautoria_frequente:
        coautoria_frequente[pair] += 1
    else:
        coautoria_frequente[pair] = 1


def adiciona_pesquisadores_ao_grafo(g: nx.Graph):
    # adiciona pesquisadores como nodes
    for k in todos_pesquisadores.keys():
        g.add_node(k)
        pesquisadores_node_list.append(k)
        label_list[k] = k


def adiciona_autores_ao_grafo(g: nx.Graph, contabiliza_relacoes: bool):
    funcoes_adicao_arestas = {
        True: adiciona_aresta_e_contabiliza_relacao,
        False: adiciona_aresta,
    }
    func_adiciona_aresta = funcoes_adicao_arestas[contabiliza_relacoes]
    # adiciona autores como nodes
    for v in todos_pesquisadores.values():
        for a in v["artigos"]:
            for i in a["autores"]:
                for j in a["autores"]:
                    if i == j:
                        continue

                    if not g.has_node(i):            
                        g.add_node(i, weight=1)
                        autores_node_list.append(i)

                    if not g.has_node(j):                  
                        g.add_node(j, weight=1)
                        autores_node_list.append(j)

                    func_adiciona_aresta(g, i, j)
                    

def adiciona_orientados_ao_grafo(g: nx.Graph):
    # adiciona orientados como nodes
    for k, v in todos_pesquisadores.items():
        for orientacao in v["orientandos"]["mestrado"]:
            if not g.has_node(orientacao["orientado"]):
                g.add_node(orientacao["orientado"], weight=1, orientador=k)
                orientados_mestrado_node_list.append(orientacao["orientado"])
                g.add_edge(k, orientacao["orientado"])

        for orientacao in v["orientandos"]["doutorado"]:
            if not g.has_node(orientacao["orientado"]):
                g.add_node(orientacao["orientado"], weight=1, orientador=k)
                orientados_doutorado_node_list.append(orientacao["orientado"])
                g.add_edge(k, orientacao["orientado"])


def retorna_cores_para_grafo_com_todos_os_individuos(g: nx.Graph):
    node_colors = []

    for node in g.nodes:
        is_pesquisador = node in todos_pesquisadores.keys()
        # Como o peesquisador sempre sera apenas pesquisador, definimos a cor na hora de desenhar (sera vermelho)
        if is_pesquisador:
            continue

        is_coautor = node in todos_autores.keys()
        is_mestrado = node in todos_orientados_mestrado.keys()
        is_doutorado = node in todos_orientados_doutorado.keys()

        if is_coautor and (is_mestrado or is_doutorado):
            node_colors.append("yellow")  # Coautor e orientado
            autores_orientados_node_list.append(node)
        elif is_coautor:
            node_colors.append("blue")  # Apenas coautor
        elif is_mestrado or is_doutorado:
            node_colors.append("green")  # Apenas orientado

    return node_colors


def limpa_listas():
    pesquisadores_node_list.clear()
    autores_node_list.clear()
    orientados_mestrado_node_list.clear()
    orientados_doutorado_node_list.clear()


for filename in os.listdir(basepath):
    # if(filename == "9034603212802471.xml" or filename ==  "8255334501824754.xml"):
        with open(basepath +filename, "r+", encoding="iso-8859-1") as file:
            curriculos.append(xmltodict.parse(file.read(), encoding="iso-8859-1"))

inicia_pesquisadores(curriculos)
  
        
g_pesquisadores_autores = nx.Graph()
adiciona_pesquisadores_ao_grafo(g_pesquisadores_autores)
adiciona_autores_ao_grafo(g_pesquisadores_autores, True)

# Desenha grafo com pesquisadores e autores
pos = nx.kamada_kawai_layout(g_pesquisadores_autores, scale=2, dim=2)
nx.draw_networkx_nodes(g_pesquisadores_autores, pos, node_size=100, nodelist=pesquisadores_node_list, node_color="yellow")
nx.draw_networkx_nodes(g_pesquisadores_autores, pos, node_size=50, nodelist=autores_node_list, node_color="blue")
nx.draw_networkx_edges(g_pesquisadores_autores, pos)
# _ = nx.draw_networkx_labels(g_pesquisadores_autores, pos, labels=label_list)
plt.title("Grafo com Pesquisadores e Autores")
plt.show()
limpa_listas()

g_pesquisadores_orientados = nx.Graph()
adiciona_pesquisadores_ao_grafo(g_pesquisadores_orientados)
adiciona_orientados_ao_grafo(g_pesquisadores_orientados)

# Função para contar as colaborações possíveis
def contar_colaboracoes(grupo_orientados):
    n = len(grupo_orientados)
    if n < 2:
        return 0
    return n * (n - 1) // 2  # Combinação de 2 elementos de n (C(n, 2))

orientadores = {}
for node in g_pesquisadores_orientados.nodes():
    if node not in pesquisadores_node_list:  
        orientador = list(g_pesquisadores_orientados.neighbors(node))[0]
        if orientador not in orientadores:
            orientadores[orientador] = []
        orientadores[orientador].append(node)
        
total_colaboracoes = 0
total_orientandos = 0

for orientador, grupo in orientadores.items():
    num_colaboracoes = contar_colaboracoes(grupo)
    total_colaboracoes += num_colaboracoes
    total_orientandos += len(grupo)
    print(f"Orientador {orientador}: {len(grupo)} orientandos, {num_colaboracoes} colaborações possíveis")


# Calculando a probabilidade de colaboração
probabilidade_colaboracao = total_colaboracoes / (total_orientandos * (total_orientandos - 1) / 2) if total_orientandos > 1 else 0
print(probabilidade_colaboracao)
    
# Desenha grafo com pesquisadores e orientados de mestrado e doutorado
pos = nx.fruchterman_reingold_layout(g_pesquisadores_orientados, k=0.12)
nx.draw_networkx_nodes(g_pesquisadores_orientados, pos, node_size=100, nodelist=pesquisadores_node_list, node_color="yellow")
nx.draw_networkx_nodes(g_pesquisadores_orientados, pos, node_size=50, nodelist=orientados_mestrado_node_list, node_color="blue")
nx.draw_networkx_nodes(g_pesquisadores_orientados, pos, node_size=50, nodelist=orientados_doutorado_node_list, node_color="green")
nx.draw_networkx_edges(g_pesquisadores_orientados, pos)
# _ = nx.draw_networkx_labels(g_pesquisadores_orientados, pos, labels=label_list)
plt.title("Grafo com Pesquisadores e Orientados de Mestrado e Doutorado")
plt.show()
limpa_listas()

g_com_todos_os_individuos = nx.Graph()
adiciona_pesquisadores_ao_grafo(g_com_todos_os_individuos)
adiciona_autores_ao_grafo(g_com_todos_os_individuos, False)
adiciona_orientados_ao_grafo(g_com_todos_os_individuos)

# Desenha grafo com pesquisadores, autores, e orientados de mestrado e doutorado
node_colors = retorna_cores_para_grafo_com_todos_os_individuos(g_com_todos_os_individuos)
node_list = autores_node_list + orientados_mestrado_node_list + orientados_doutorado_node_list
pos = nx.kamada_kawai_layout(g_com_todos_os_individuos, scale=2, dim=2)
nx.draw_networkx_nodes(g_com_todos_os_individuos, pos, node_size=100, nodelist=pesquisadores_node_list, node_color="red")
nx.draw_networkx_nodes(g_com_todos_os_individuos, pos, node_size=50, nodelist=node_list, node_color=node_colors)
nx.draw_networkx_edges(g_com_todos_os_individuos, pos)
# _ = nx.draw_networkx_labels(g_com_todos_os_individuos, pos, labels=label_list)
plt.title("Grafo com Pesquisadores, Autores e Orientados de Mestrado e Doutorado")
plt.show()
limpa_listas()

# Identificando clusters de pesquisadores com o mesmo orientador
with open("clustering.txt", "w+") as file:
    file.write("Coeficiente de clusters para cada node de pesquisadores com o mesmo orientador\n")
    print("Coeficiente de clusters para cada node de pesquisadores com o mesmo orientador")
    clusters = nx.clustering(g_com_todos_os_individuos, nodes=autores_orientados_node_list)
    file.write(f"Dados de clustering: {clusters}")
    print(clusters)

# Calcula Degree Centrality
with open("degree_centrality.txt", "w") as file:
    file.write("Degree Centrality\n")
    print("Degree Centrality")
    degree_centrality = nx.degree_centrality(g_com_todos_os_individuos)
    print(degree_centrality)
    for node, centrality in degree_centrality.items():
        file.write(f"{node}: {centrality}\n")

# Calcula Betweenness Centrality
with open("betweenness_centrality.txt", "w") as file:
    file.write("Betweenness Centrality\n")
    print("Betweenness Centrality")
    betweenness_centrality = nx.betweenness_centrality(g_com_todos_os_individuos)
    print(betweenness_centrality)
    for node, centrality in betweenness_centrality.items():
        file.write(f"{node}: {centrality}\n")

# Identifica comunidades entre pesquisadores
partition = community_louvain.best_partition(g_com_todos_os_individuos)
plt.figure(figsize=(10, 10))
colors = [partition[node] for node in g_com_todos_os_individuos.nodes]
nx.draw_networkx_nodes(g_com_todos_os_individuos, pos, node_size=50, node_color=colors, cmap=plt.cm.jet)
nx.draw_networkx_edges(g_com_todos_os_individuos, pos, alpha=0.3)
nx.draw_networkx_labels(g_com_todos_os_individuos, pos, labels=label_list, font_size=10)
num_clusters = len(set(partition.values()))
print(f'Número de comunidades detectados: {num_clusters}')
plt.title("Principais Comunidades de Pesquisadores")
plt.show()

# Calcula a densidade do grafo
with open("densidade.txt", "w") as file:
    print("Densidade do grafo: ", end="")
    densidade_grafo = nx.density(g_com_todos_os_individuos)
    print(densidade_grafo)
    file.write(f"Densidade do grafo: {densidade_grafo}")

# Frequencia de colaborações entre pesquisadores
# Essas frequencias sao contabilizadas na funcao adiciona_aresta_e_contabiliza_relacao
# As frequencias sao divididas por 2 pois cada aresta é contada 2 vezes. Sendo um par de vértices (u, v), é contada como (u, v) e (v, u).
with open("frequencia_colaboracoes.txt", "w") as file:
    file.write("Identificação de Padrões de Coautoria e Frequência de Colaborações:\n")
    print("Identificação de Padrões de Coautoria e Frequência de Colaborações")
    for pair, freq in coautoria_frequente.items():
        freq = int(freq/2)
        print(f"{pair[0]} e {pair[1]}:  {freq} vezes\n")
        file.write(f"{pair[0]} e {pair[1]}:  {freq} vezes\n")


# Probabilidade de colaboração entre pesquisadores que possuem o mesmo orientador
# Função para contar as colaborações possíveis
def contar_colaboracoes_possiveis(grupo_orientados):
    n = len(grupo_orientados)
    if n < 2:
        return 0
    return n * (n - 1) // 2  # Combinação de 2 elementos de n (C(n, 2))

orientadores = {}
nodes = g_pesquisadores_orientados.nodes(data="orientador", default="")
for node in nodes:
    if node[1] == "":
        if node[0] not in orientadores.keys():
            orientadores[node[0]] = []
        continue

    if node[1] not in orientadores.keys():
        orientadores[node[1]] = []
    orientadores[node[1]].append(node[0])
        
total_colaboracoes_possiveis = 0
total_orientandos = 0
for orientador, grupo in orientadores.items():
    num_colaboracoes_possiveis = contar_colaboracoes_possiveis(grupo)
    total_colaboracoes_possiveis += num_colaboracoes_possiveis
    total_orientandos += len(grupo)
    print(f"Orientador {orientador}: {len(grupo)} orientandos, {num_colaboracoes_possiveis} colaborações possíveis")

# Calculando a probabilidade de colaboração
probabilidade_colaboracao = total_colaboracoes_possiveis / (total_orientandos * (total_orientandos - 1) / 2) if total_orientandos > 1 else 0
print(f"{probabilidade_colaboracao * 100:.2f}%")

# Assortatividade
orientandos = list(map(lambda x: (x[0], {"orientador": x[1]}), filter(lambda x: x[1], nodes)))
g_orientandos = nx.Graph()
g_orientandos.add_nodes_from(orientandos)
for i in orientandos:
    for j in orientandos:
        if g_com_todos_os_individuos.has_edge(i[0], j[0]):
            g_orientandos.add_edge(i[0], j[0])

assortatividade = nx.assortativity.attribute_assortativity_coefficient(g_pesquisadores_orientados, "orientador")
print(assortatividade)
pos = nx.fruchterman_reingold_layout(g_orientandos)
nx.draw_networkx_nodes(g_orientandos, pos, node_size=70, node_color="green")
nx.draw_networkx_edges(g_orientandos, pos)
plt.title("Grafo com Pesquisadores, Autores e Orientados de Mestrado e Doutorado")
plt.show()
