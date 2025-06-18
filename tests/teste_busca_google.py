import os
import google.genai as genai

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types  # Para criar conteúdos (Content e Part)
from datetime import date
import textwrap # Para formatar melhor a saída de texto
import requests # Para fazer requisições HTTP
import warnings

warnings.filterwarnings("ignore")


#########################################################################
GOOGLE_API_KEY =  "AIzaSyDgETZ9Y6vzhRm7Zda5f5XegajGdci7_Vo"
#########################################################################


if not GOOGLE_API_KEY:
    raise ValueError("A variável de ambiente GOOGLE_API_KEY não está configurada.")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

#########################################################################
# TESTE GENAI
#########################################################################

client = genai.Client()
MODEL_ID = 'gemini-2.0-flash'

response= client.models.generate_content(
    model=MODEL_ID,
    contents='Encontre 3 links diretos para download de 3 imagens diferentes da capa do livro Merchants of doubt',
    config={"tools": [{"google_search": {}}]}
)

print(response.text)

# Exibe a busca
print(f"Busca realizada: {response.candidates[0].grounding_metadata.web_search_queries}")
# Exibe as URLs nas quais ele se baseou
print(f"Páginas utilizadas na resposta: {', '.join([site.web.title for site in response.candidates[0].grounding_metadata.grounding_chunks])}")
# print(response.candidates[0].grounding_metadata.search_entry_point.rendered_content)

