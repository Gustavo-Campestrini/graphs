import networkx as nx
import matplotlib.pyplot as plt
import json

import os

import xml.etree.ElementTree as ET

# Diretório onde estão os arquivos XML
pasta_curriculos = "./curriculos"

# Lista para armazenar os objetos gerados
array_objetos = []

import os
import xml.etree.ElementTree as ET

# Caminho para a pasta com os arquivos XML
caminho_pasta = "./curriculos"

# Função para processar um único XML e transformá-lo em um dicionário
def processar_xml(arquivo):
    try:
        # Carregar e processar o XML
        tree = ET.parse(arquivo)
        root = tree.getroot()
        
        # Converter para dicionário
        dicionario = xml_para_dict(root)
        
        # Converter para JSON
        return dicionario
   
    except Exception as e:
        print(f"Erro ao processar o arquivo {arquivo}: {e}")
        return None



def xml_para_dict(elemento):
    dicionario = {}

    # Adicionar atributos como pares chave-valor
    for chave, valor in elemento.attrib.items():
        dicionario[chave] = valor

    # Processar filhos
    for filho in elemento:
        valor = xml_para_dict(filho) if len(filho) > 0 or filho.attrib else (filho.text or "").strip()
        
        if filho.tag in dicionario:
            # Converter para lista se a tag já existir
            if not isinstance(dicionario[filho.tag], list):
                dicionario[filho.tag] = [dicionario[filho.tag]]
            dicionario[filho.tag].append(valor)
        else:
            dicionario[filho.tag] = valor

    # Caso não tenha filhos nem atributos, retorna texto como dicionário vazio ou valor direto
    if not dicionario and elemento.text:
        return elemento.text.strip()
    elif not dicionario:
        return {}  # Garante que objetos vazios sejam representados corretamente

    return dicionario





# Percorre todos os arquivos na pasta "curriculos"
def processar_todos_xml(caminho_pasta):
    array_objetos = []
    for arquivo_nome in os.listdir(caminho_pasta):
        if arquivo_nome.endswith(".xml"):  # Filtra apenas arquivos XML
            arquivo_caminho = os.path.join(caminho_pasta, arquivo_nome)
            obj = processar_xml(arquivo_caminho)
            if obj:
                array_objetos.append(obj)
    return array_objetos

# Executa o processamento
objetos = processar_todos_xml(caminho_pasta)

# Exibe o resultado

print(objetos[0])




def salvar_em_json(objetos, nome_arquivo):
    try:
        with open(nome_arquivo, "w", encoding="utf-8") as json_file:
            json.dump(objetos, json_file, ensure_ascii=False, indent=4)
        print(f"Arquivo JSON salvo com sucesso em: {nome_arquivo}")
    except Exception as e:
        print(f"Erro ao salvar o arquivo JSON: {e}")

salvar_em_json(objetos[0], "./json")
