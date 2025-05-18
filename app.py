# /seu_projeto_biblioteca/app.py

import os
import json
import uuid  # Para gerar IDs únicos para os livros
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, current_app
from werkzeug.utils import secure_filename  # Para segurança no nome de arquivos enviados
import logging  # Para logs e debugging
from datetime import datetime
import google.generativeai as genai

# --- Configuração do Gemini ---
# Certifique-se de configurar sua chave de API do Gemini como uma variável de ambiente
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("A variável de ambiente GOOGLE_API_KEY não está configurada.")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')



# --- Configuração da Aplicação ---
app = Flask(__name__)
app.secret_key = "Obladioblada"  # Importante para mensagens flash e sessões


# Define o caminho para a pasta de uploads e o arquivo JSON
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')
BOOKS_FILE = os.path.join(BASE_DIR, 'books.json')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Extensões de imagem permitidas

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BOOKS_FILE'] = BOOKS_FILE

# Garante que a pasta de uploads exista
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Garante que o arquivo books.json exista e seja uma lista JSON válida
if not os.path.exists(BOOKS_FILE):
    with open(BOOKS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)  # Cria uma lista vazia se o arquivo não existir
else:  # Verifica se o arquivo existente é um JSON válido com uma lista
    try:
        with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
            content = json.load(f)
            if not isinstance(content, list):
                raise ValueError("O arquivo books.json não contém uma lista.")
    except (json.JSONDecodeError, ValueError) as e:
        app.logger.warning(f"Arquivo books.json corrompido ou mal formatado ({e}). Recriando com uma lista vazia.")
        with open(BOOKS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)


# --- Funções Auxiliares ---
def allowed_file(filename):
    """Verifica se o arquivo enviado tem uma extensão permitida."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_books():
    """Carrega os livros do arquivo JSON."""
    try:
        with open(app.config['BOOKS_FILE'], 'r', encoding='utf-8') as f:
            books = json.load(f)
            if not isinstance(books, list):  # Garante que o conteúdo seja uma lista
                app.logger.error("books.json não contém uma lista. Retornando lista vazia.")
                return []
    except (FileNotFoundError, json.JSONDecodeError):
        books = []  # Retorna lista vazia se o arquivo não existir ou for inválido
    return books


def save_books(books_data):
    """Salva os livros no arquivo JSON."""
    with open(app.config['BOOKS_FILE'], 'w', encoding='utf-8') as f:
        json.dump(books_data, f, indent=4, ensure_ascii=False)  # ensure_ascii=False para caracteres acentuados


def generate_unique_id():
    """Gera um ID único para um livro."""
    return str(uuid.uuid4())


def get_book_by_id(book_id):
    """Recupera um único livro pelo seu ID."""
    books = load_books()
    for book in books:
        if book.get('id') == book_id:
            return book
    return None


# --- Rotas da Aplicação ---
@app.route('/')
def index():
    """Exibe a página principal com a lista de livros e uma barra de busca."""
    current_year = datetime.now().year
    query = request.args.get('query', '').lower()  # Pega o termo de busca, se houver
    books = load_books()

    if query:
        # Busca simples: verifica título e autor (case-insensitive)
        filtered_books = [
            book for book in books
            if query in book.get('title', '').lower() or \
               query in book.get('author', '').lower()
        ]
    else:
        filtered_books = books
    return render_template('index.html', books=filtered_books, current_year=current_year, query=query)


@app.route('/register', methods=['GET', 'POST'])
def register_book():
    """Lida com o cadastro de novos livros."""
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        language = request.form.get('language')
        shelf = request.form.get('shelf')
        review = request.form.get('review')
        cover_image_file = request.files.get('cover_image')  # Pega o arquivo da capa

        # Validação básica (título e autor são obrigatórios)
        if not all([title, author]):
            flash('Título e Autor são campos obrigatórios.', 'error')
            return render_template('register.html', form_data=request.form)

        books = load_books()
        new_book_id = generate_unique_id()
        cover_path_for_json = None  # Caminho da capa para salvar no JSON

        if cover_image_file and cover_image_file.filename != '':
            if allowed_file(cover_image_file.filename):
                # Cria um nome de arquivo seguro e único para a capa
                filename = secure_filename(f"{new_book_id}_{cover_image_file.filename}")
                # Caminho completo para salvar o arquivo no servidor
                filepath_on_server = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                cover_image_file.save(filepath_on_server)
                # Caminho relativo para usar no HTML (static/uploads/filename.jpg)
                cover_path_for_json = os.path.join('uploads', filename).replace("\\",
                                                                                "/")  # Garante barras normais para web
            else:
                flash('Tipo de arquivo da capa inválido. Use png, jpg, jpeg, gif.', 'error')
                return render_template('register.html', form_data=request.form)

        new_book = {
            "id": new_book_id,
            "title": title,
            "author": author,
            "language": language,
            "shelf": shelf,
            "review": review,
            "cover_path": cover_path_for_json  # Salva o caminho relativo da capa
        }
        books.append(new_book)
        save_books(books)
        flash('Livro cadastrado com sucesso!', 'success')
        return redirect(url_for('index'))

    # Se for GET, apenas mostra o formulário de cadastro
    return render_template('register.html', form_data={})

#
@app.route('/analyze_cover_via_gemini', methods=['POST'])

def analyze_cover_with_gemini():
    """
    Endpoint para receber uma imagem (da câmera), enviá-la ao Gemini,
    e retornar informações extraídas do livro.
    """
    if 'image_data' not in request.files:
        current_app.logger.error("Nenhuma imagem recebida em /analyze_cover_via_gemini")
        return jsonify({"error": "Nenhuma imagem recebida."}), 400

    image_file = request.files['image_data']
    current_app.logger.info(f"Recebida imagem para análise: {image_file.filename}")

    try:

        image_bytes = image_file.read()
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}


        prompt =         '''
        A partir da imagem fornecida, obtenha os dados do título do livro,
        do autor do livro, do idioma do livro, e obtenha também uma resenha em português do
        livro. O resultado deve ser dado em um texto simples (não JSON) da seguinte forma:

                 {
            "title": "Título",
            "author": "Autor Extraído pela IA (Exemplo)",
            "language": "Idioma Sugerido (Exemplo)",
            "review": "Esta é uma resenha inicial sugerida pela IA com base na capa... (Exemplo)"
        }
        '''

        response = model.generate_content(
            [prompt, image_part],
            stream=False
        )
        # response.raise_for_status()

        gemini_output = response.text

        print(gemini_output)
        # app.logger.info(f"Dados obtidos do Gemini: {gemini_output}")
        # return jsonify(gemini_output)


        # Processar a resposta do Gemini para extrair os campos desejados
        # Esta é uma etapa que pode variar dependendo da formatação da resposta do Gemini.
        # Uma abordagem simples é procurar por palavras-chave.
        extracted_data = {}
        lines = gemini_output.split('\n')
        for line in lines:
            if "title" in line:
                extracted_data["title"] = line.split('"title":')[1].strip()
            elif "author" in line:
                extracted_data["author"] = line.split('"author":')[1].strip()
            elif "language" in line:
                extracted_data["language"] = line.split('"language":')[1].strip()
            elif "review" in line:
                extracted_data["review"] = line.split('"review":')[1].strip()

        current_app.logger.info(f"Dados extraídos do Gemini: {extracted_data}")
        return jsonify(extracted_data)

    except Exception as e:
        current_app.logger.error(f"Erro ao chamar a API do Gemini: {e}")
        return jsonify({"error": f"Erro ao processar a imagem com o Gemini: {e}"})



# def analyze_cover_with_gemini():
#     """
#     Endpoint para receber uma imagem (da câmera), (conceitualmente) enviá-la ao Gemini,
#     e retornar informações extraídas do livro.
#     !!! ATENÇÃO: ESTA É UMA IMPLEMENTAÇÃO DE EXEMPLO (PLACEHOLDER). !!!
#     Você precisará adicionar sua lógica de chamada à API do Gemini aqui.
#     """
#     if 'image_data' not in request.files:
#         app.logger.error("Nenhuma imagem recebida em /analyze_cover_via_gemini")
#         return jsonify({"error": "Nenhuma imagem recebida."}), 400
#
#     image_file = request.files['image_data']
#     app.logger.info(f"Recebida imagem para análise: {image_file.filename}")
#
#     # --- INÍCIO: INTEGRAÇÃO COM A API DO GEMINI (EXEMPLO/PLACEHOLDER) ---
#     # 1. Você precisará obter os bytes da imagem: image_bytes = image_file.read()
#     # 2. Configurar o cliente da API do Gemini com sua chave.
#     # 3. Enviar a imagem para a API do Gemini com um prompt adequado.
#     #    Exemplo de prompt: "Analise esta imagem de capa de livro e extraia o título, autor,
#     #                       idioma (se visível) e uma breve sugestão de resenha."
#     # 4. Processar a resposta da API do Gemini para extrair os campos desejados.
#     #
#     #    Por enquanto, vamos retornar dados de exemplo (simulando a resposta do Gemini):
#     try:
#         # Simulação de processamento e resposta
#         # (substitua pela chamada real ao Gemini)
#         extracted_data = {
#             "title": "Título",
#             "author": "Autor Extraído pela IA (Exemplo)",
#             "language": "Idioma Sugerido (Exemplo)",
#             "review": "Esta é uma resenha inicial sugerida pela IA com base na capa... (Exemplo)"
#         }
#         app.logger.info(f"Dados simulados do Gemini: {extracted_data}")
#         print(jsonify((extracted_data)))
#         return jsonify(extracted_data)
#
#     except Exception as e:
#         app.logger.error(f"Erro ao simular chamada ao Gemini: {e}")
#         return jsonify({"error": "Erro no processamento da imagem no servidor."}), 500
#     # --- FIM: INTEGRAÇÃO COM A API DO GEMINI ---






@app.route('/book/<book_id>')
def book_detail_route(book_id):  # Renomeado para evitar conflito com nome de módulo/função
    """Exibe os detalhes de um livro específico."""
    book = get_book_by_id(book_id)
    if book:
        return render_template('book_detail.html', book=book)
    flash('Livro não encontrado.', 'error')
    return redirect(url_for('index'))


@app.route('/edit/<book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """Lida com a edição de um livro existente."""
    book = get_book_by_id(book_id)
    if not book:
        flash('Livro não encontrado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        books = load_books()
        book_index = next((index for (index, d) in enumerate(books) if d.get("id") == book_id), None)

        if book_index is not None:
            # Atualiza os dados do livro
            books[book_index]['title'] = request.form.get('title', book['title'])
            books[book_index]['author'] = request.form.get('author', book['author'])
            books[book_index]['language'] = request.form.get('language', book.get('language'))
            books[book_index]['shelf'] = request.form.get('shelf', book.get('shelf'))
            books[book_index]['review'] = request.form.get('review', book.get('review'))

            cover_image_file = request.files.get('cover_image')
            if cover_image_file and cover_image_file.filename != '':
                if allowed_file(cover_image_file.filename):
                    # Caminho da capa antiga para possível remoção
                    old_cover_filename = books[book_index].get('cover_path')
                    old_cover_path_full = None
                    if old_cover_filename:
                        old_cover_path_full = os.path.join(app.config['UPLOAD_FOLDER'],
                                                           os.path.basename(old_cover_filename))

                    # Salva a nova capa
                    new_filename = secure_filename(f"{book_id}_{cover_image_file.filename}")
                    new_filepath_on_server = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                    cover_image_file.save(new_filepath_on_server)
                    books[book_index]['cover_path'] = os.path.join('uploads', new_filename).replace("\\", "/")

                    # Remove a capa antiga se for diferente da nova e existir
                    if old_cover_path_full and os.path.exists(old_cover_path_full) and os.path.basename(
                            old_cover_path_full) != new_filename:
                        try:
                            os.remove(old_cover_path_full)
                            app.logger.info(f"Capa antiga removida: {old_cover_path_full}")
                        except OSError as e:
                            app.logger.error(f"Erro ao remover capa antiga {old_cover_path_full}: {e}")
                else:
                    flash('Tipo de arquivo da nova capa inválido. Use png, jpg, jpeg, gif.', 'error')
                    return render_template('edit_book.html', book=book, book_id=book_id)

            save_books(books)
            flash('Livro atualizado com sucesso!', 'success')
            return redirect(url_for('book_detail_route', book_id=book_id))
        else:
            # Isso não deveria acontecer se o livro foi encontrado inicialmente
            flash('Erro ao encontrar o livro para edição.', 'error')
            return redirect(url_for('index'))

    return render_template('edit_book.html', book=book, book_id=book_id)


@app.route('/delete/<book_id>', methods=['POST'])  # Usar POST para exclusão por segurança
def delete_book(book_id):
    """Exclui um livro."""
    books = load_books()
    book_to_delete = get_book_by_id(book_id)  # Pega os detalhes do livro antes de filtrar a lista

    if not book_to_delete:
        flash('Livro não encontrado para exclusão.', 'error')
        return redirect(url_for('index'))

    # Remove o arquivo da capa do livro, se existir
    if book_to_delete.get('cover_path'):
        cover_filename = os.path.basename(book_to_delete['cover_path'])  # Pega apenas o nome do arquivo
        cover_file_path_on_server = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)
        if os.path.exists(cover_file_path_on_server):
            try:
                os.remove(cover_file_path_on_server)
                app.logger.info(f"Imagem da capa excluída: {cover_file_path_on_server}")
            except OSError as e:
                app.logger.error(f"Erro ao excluir imagem da capa {cover_file_path_on_server}: {e}")

    # Cria uma nova lista sem o livro excluído
    updated_books = [book for book in books if book.get('id') != book_id]

    if len(books) == len(updated_books):  # Verifica se algum livro foi realmente removido
        flash('Erro ao tentar excluir o livro. Livro não encontrado na lista.', 'warning')
    else:
        save_books(updated_books)
        flash('Livro excluído com sucesso!', 'success')

    return redirect(url_for('index'))








# --- Execução da Aplicação ---
if __name__ == '__main__':
    # host='0.0.0.0' permite acesso de outros dispositivos na mesma rede
    app.run(debug=True, host='0.0.0.0', port=5000)
