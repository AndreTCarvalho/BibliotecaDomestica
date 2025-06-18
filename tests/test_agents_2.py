from flask import Flask, render_template, request, redirect, url_for
import os
from PIL import Image
import io
import base64
import requests
from urllib.parse import quote

app = Flask(__name__)
UPLOAD_FOLDER = 'img'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Função simulada para buscar capas semelhantes (substituir por lógica real)
def buscar_capas_similares(descricao):
    termos_busca = quote(descricao + " capa de livro")
    url_busca = f"https://www.google.com/search?q={termos_busca}&tbm=isch"
    # Atenção: Fazer scraping do Google pode ser instável e violar termos de serviço.
    # Em uma aplicação real, considerar APIs de livros ou outras fontes de dados.
    # Para este exemplo, retornaremos URLs de imagens fixas.
    return [
        "https://m.media-amazon.com/images/I/7199Gf58fVL._SL1500_.jpg",
        "https://m.media-amazon.com/images/I/71sAl6CeYCL._SL1500_.jpg",
        "https://m.media-amazon.com/images/I/71yLyK6v8DL._SL1500_.jpg"
    ]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'foto_capa' in request.files:
            foto_capa = request.files['foto_capa']
            if foto_capa.filename != '':
                nome_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], "capa_capturada.jpg")
                foto_capa.save(nome_arquivo)

                # Simula análise da imagem para obter uma descrição (substituir por OCR ou análise real)
                descricao_imagem = "livro de ficção com elementos de fantasia"
                capas_similares = buscar_capas_similares(descricao_imagem)

                return render_template('index.html', foto_capturada='capa_capturada.jpg', capas_similares=capas_similares)
        elif 'capa_selecionada' in request.form:
            capa_url = request.form['capa_selecionada']
            titulo_livro = request.form.get('titulo_livro', 'Título não informado')
            # Aqui você salvaria o título e a URL da capa no seu banco de dados
            return render_template('salvo.html', titulo=titulo_livro, capa_url=capa_url)

    return render_template('index2.html')

if __name__ == '__main__':
    app.run(debug=True)