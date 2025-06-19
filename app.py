import os
import uuid
import base64
import requests
import logging
import json
import mimetypes  # Novo import para detecção de tipo MIME
import re  # Novo import para expressões regulares, caso o JSON do Gemini falhe
from datetime import datetime
from pathlib import Path  # Novo import para manipulação de caminhos
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, current_app
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, and_, or_
import google.generativeai as genai
import shutil

# --- Configuração do Gemini ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Configuração de logging (garante que esteja configurado globalmente desde o início)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if not GOOGLE_API_KEY:
    logging.error("A variável de ambiente GOOGLE_API_KEY não está configurada. O serviço Gemini não funcionará.")
    # Não levantamos ValueError aqui para permitir que a aplicação continue funcionando sem o Gemini
    model = None
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # Usando 'gemini-1.5-flash' como um modelo mais estável e com custo-benefício.
        # 'gemini-2.0-flash' pode não ser um nome de modelo válido ou ser muito recente.
        model = genai.GenerativeModel('gemini-1.5-flash')
        logging.info("Modelo Gemini configurado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao inicializar o modelo Gemini: {e}")
        model = None  # Define model como None se houver falha
        logging.warning("API Key do Gemini encontrada, mas o serviço de análise de capa não pôde ser inicializado.")

# --- Configuração da Aplicação ---
app = Flask(__name__)

# Gerar uma chave secreta forte se não estiver definida como variável de ambiente
# ESSENCIAL para segurança em produção!
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
if not os.environ.get("FLASK_SECRET_KEY"):
    logging.warning("FLASK_SECRET_KEY não definida como variável de ambiente. Usando chave gerada aleatoriamente. "
                    "Para produção, defina uma chave persistente e segura.")

# Define o caminho para a pasta de uploads
BASE_DIR = Path(os.path.abspath(os.path.dirname(__file__)))  # <<--- MODIFICADO: Usando Pathlib
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'  # <<----------------- MODIFICADO: Usando Pathlib
BACKUP_FOLDER = BASE_DIR / 'backups'  # <<--------------------------- ADICIONADO: Pasta para backups do DB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)  # <<----------------- MODIFICADO: Convertendo Path para str
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(BASE_DIR / 'library.db')  # <- MODIFICADO para Pathlib
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DB_CHANGES_COUNT'] = 0  # <<----------------------------- ADICIONADO: Contador para backups
app.config['DB_BACKUP_THRESHOLD'] = 5  # <<--------------------------- ADICIONADO: Limite para acionar backup

db = SQLAlchemy(app)

# Garante que as pastas de uploads e backups existam
for folder_path in [UPLOAD_FOLDER, BACKUP_FOLDER]:  # <<------------- MODIFICADO: Loop para criar pastas
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)  # Garante criação de pais se necessário
            logging.info(f"Pasta criada: {folder_path}")
        except OSError as e:
            logging.critical(f"Erro CRÍTICO ao criar pasta {folder_path}: {e}")


# --- Modelo do Banco de Dados ---
class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100))
    language = db.Column(db.String(50))
    shelf = db.Column(db.String(100))
    bookshelf = db.Column(db.String(100))
    review = db.Column(db.Text)
    cover_path = db.Column(db.String(255))  # Caminho relativo da capa (ex: 'uploads/nome_arquivo.jpg')

    def __repr__(self):
        return f"<Book {self.title} by {self.author}>"


# <<------------------------------------------------------------------------>>
# <<---------------------- INÍCIO: FUNÇÕES DE BACKUP ----------------------->>
# <<------------------------------------------------------------------------>>
def backup_database():
    """Cria um backup do arquivo do banco de dados."""
    source_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    # Garante que estamos lidando com SQLite local
    if not source_db_uri.startswith('sqlite:///'):
        logging.error("Backup atualmente suportado apenas para URIs 'sqlite:///'.")
        return

    source_db_path_str = source_db_uri.replace('sqlite:///', '')
    source_db_path = Path(source_db_path_str)

    if not source_db_path.is_file():  # Verifica se é um arquivo e existe
        logging.error(f"Arquivo do banco de dados não encontrado em {source_db_path} para backup.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"library_backup_{timestamp}.db"
    backup_filepath = BACKUP_FOLDER / backup_filename

    try:
        shutil.copy2(source_db_path, backup_filepath)
        logging.info(f"Backup do banco de dados criado com sucesso: {backup_filepath}")
    except Exception as e:
        logging.error(f"Erro ao criar backup do banco de dados: {e}", exc_info=True)


def check_and_perform_backup():
    """Verifica o contador de alterações e realiza backup se necessário."""
    app.config['DB_CHANGES_COUNT'] += 1
    logging.debug(f"Contador de alterações do DB: {app.config['DB_CHANGES_COUNT']}")
    # Usa app.config.get para o threshold, com um fallback para garantir que funcione
    if app.config['DB_CHANGES_COUNT'] >= app.config.get('DB_BACKUP_THRESHOLD', 5):
        logging.info("Contador de alterações atingiu o limite. Iniciando backup...")
        backup_database()
        app.config['DB_CHANGES_COUNT'] = 0  # Reseta o contador


# <<------------------------------------------------------------------------>>
# <<------------------------ FIM: FUNÇÕES DE BACKUP ------------------------>>
# <<------------------------------------------------------------------------>>


# --- Funções Auxiliares de Capa ---
def allowed_file(filename):
    """Verifica se o arquivo tem uma extensão permitida."""
    if not filename:
        return False
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image_from_file(file_storage):  # Renomeado parâmetro para clareza
    if not file_storage or file_storage.filename == '': return None
    if not allowed_file(file_storage.filename):
        logging.warning(f"Tipo de arquivo não permitido para '{file_storage.filename}'.")
        return None
    try:
        extension = file_storage.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        filepath = UPLOAD_FOLDER / unique_filename  # Usando Pathlib
        file_storage.save(filepath)
        logging.info(f"Arquivo salvo: {filepath}")
        return (Path('uploads') / unique_filename).as_posix()  # Caminho relativo para DB/HTML
    except Exception as e:
        logging.error(f"Erro ao salvar arquivo '{file_storage.filename}': {e}", exc_info=True)
        return None


def save_image_from_base64(base64_string):
    if not base64_string: return None
    try:
        if ',' not in base64_string:
            logging.error("String Base64 não contém 'data:...' header.")
            return None
        header, encoded_data = base64_string.split(',', 1)
        mime_type = header.split(';')[0].split(':')[1] if ':' in header else 'application/octet-stream'
        extension = mimetypes.guess_extension(mime_type) or '.jpeg'  # Fallback
        extension = extension.lstrip('.')  # Remove o ponto se presente
        if extension not in ALLOWED_EXTENSIONS:
            logging.warning(f"Extensão '{extension}' (de {mime_type}) não permitida via Base64.")
            return None
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        filepath = UPLOAD_FOLDER / unique_filename  # Usando Pathlib
        decoded_data = base64.b64decode(encoded_data)
        with open(filepath, "wb") as fh:
            fh.write(decoded_data)
        logging.info(f"Imagem Base64 salva: {filepath}")
        return (Path('uploads') / unique_filename).as_posix()
    except Exception as e:
        logging.error(f"Erro ao salvar imagem Base64: {e}", exc_info=True)
        return None


def save_image_from_url(image_url):
    if not image_url: return None
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '').lower()
        extension = mimetypes.guess_extension(content_type) or '.jpg'  # Fallback
        extension = extension.lstrip('.')
        if extension not in ALLOWED_EXTENSIONS:
            logging.warning(f"Extensão '{extension}' (de {content_type}) não permitida via URL.")
            return None
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        filepath = UPLOAD_FOLDER / unique_filename  # Usando Pathlib
        with open(filepath, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=8192):
                out_file.write(chunk)
        logging.info(f"Imagem da URL salva: {filepath}")
        return (Path('uploads') / unique_filename).as_posix()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao baixar imagem da URL '{image_url}': {e}")
        return None
    except Exception as e:
        logging.error(f"Erro ao processar URL '{image_url}': {e}", exc_info=True)
        return None


def delete_existing_cover(book_cover_path):
    default_cover_rel_path = (Path('uploads') / 'default_cover.png').as_posix()
    if book_cover_path and book_cover_path != default_cover_rel_path:
        full_filepath = Path(app.static_folder) / book_cover_path  # Usando Pathlib
        if full_filepath.exists() and full_filepath.is_file():  # Verifica se existe e é arquivo
            try:
                full_filepath.unlink()  # Método de Pathlib para remover arquivo
                logging.info(f"Capa antiga removida: {full_filepath}")
            except OSError as e:
                logging.error(f"Erro ao remover capa antiga {full_filepath}: {e}", exc_info=True)
        else:
            logging.debug(f"Capa antiga não encontrada para exclusão ou não é arquivo: {full_filepath}")


def process_cover_options(book, request_form, request_files):
    """
    Processa as opções de capa e atualiza o caminho da capa do livro.
    Retorna o novo caminho da capa ou None se a capa deve ser mantida ou removida.
    """
    cover_option = request_form.get('cover_option')
    new_cover_path = book.cover_path  # Começa assumindo que a capa será mantida

    if cover_option == 'file':
        cover_file = request_files.get('cover_file')
        if cover_file and cover_file.filename != '':
            # Lógica para salvar o arquivo e obter o new_cover_path
            # Exemplo: new_cover_path = save_uploaded_file(cover_file, app.config['UPLOAD_FOLDER'])
            pass  # Substitua pelo seu código de salvamento de arquivo
        # Se nenhum arquivo for enviado, mas 'file' foi selecionado,
        # pode-se optar por manter a capa atual ou usar a padrão.
        # Para este caso, se 'file' é selecionado mas nenhum arquivo é enviado,
        # vamos assumir que o usuário não quis mudar, então new_cover_path permanece book.cover_path.
        # Se quisesse forçar a padrão, seria: new_cover_path = 'uploads/default_cover.png'

    elif cover_option == 'camera':
        image_data = request_form.get('cover_image_data')
        if image_data:
            # Lógica para salvar a imagem da câmera e obter o new_cover_path
            # Exemplo: new_cover_path = save_base64_image(image_data, app.config['UPLOAD_FOLDER'])
            pass  # Substitua pelo seu código de salvamento de imagem base64

    elif cover_option == 'url':
        cover_url = request_form.get('final_cover_url')  # Usar final_cover_url que é validado no JS
        if cover_url:
            # Lógica para baixar a imagem da URL, salvar e obter o new_cover_path
            # Exemplo: new_cover_path = download_and_save_image_from_url(cover_url, app.config['UPLOAD_FOLDER'])
            pass  # Substitua pelo seu código de download e salvamento

    elif cover_option == 'current':
        # Se a opção é 'current', explicitamente não fazemos nada,
        # new_cover_path já foi inicializado com book.cover_path.
        pass

    # Se a opção 'none' fosse reintroduzida no HTML:
    # elif cover_option == 'none':
    #     new_cover_path = None # Ou 'uploads/default_cover.png'

    # Opcional: Deletar a capa antiga se uma nova foi definida e a antiga não é a padrão
    # if new_cover_path != book.cover_path and book.cover_path and book.cover_path != 'uploads/default_cover.png':
    #     try:
    #         old_file_full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(book.cover_path))
    #         if os.path.exists(old_file_full_path):
    #             os.remove(old_file_full_path)
    #     except Exception as e:
    #         print(f"Erro ao deletar capa antiga: {e}")

    return new_cover_path


@app.route('/')
def index():
    query_term = request.args.get('query', '')
    selected_language = request.args.get('language_filter', '')
    selected_genre = request.args.get('genre_filter', '')
    selected_bookshelf = request.args.get('bookshelf_filter', '')
    selected_shelf = request.args.get('shelf_filter', '')

    # Obter opções distintas para os filtros (seu código existente aqui)
    all_languages = [
        lang[0] for lang in db.session.query(distinct(Book.language))
        .filter(Book.language.isnot(None), Book.language != '')
        .order_by(Book.language).all()
    ]
    all_genres = [
        genre[0] for genre in db.session.query(distinct(Book.genre))
        .filter(Book.genre.isnot(None), Book.genre != '')
        .order_by(Book.genre).all()
    ]
    all_bookshelves = [
        bs[0] for bs in db.session.query(distinct(Book.bookshelf))
        .filter(Book.bookshelf.isnot(None), Book.bookshelf != '')
        .order_by(Book.bookshelf).all()
    ]
    all_shelves = [
        sh[0] for sh in db.session.query(distinct(Book.shelf))
        .filter(Book.shelf.isnot(None), Book.shelf != '')
        .order_by(Book.shelf).all()
    ]

    query_obj = Book.query
    filter_conditions = []

    if query_term:
        filter_conditions.append(
            or_(
                Book.title.ilike(f'%{query_term}%'),
                Book.author.ilike(f'%{query_term}%')
            )
        )

    if selected_language:
        filter_conditions.append(Book.language == selected_language)
    if selected_genre:
        filter_conditions.append(Book.genre == selected_genre)
    if selected_bookshelf:
        filter_conditions.append(Book.bookshelf == selected_bookshelf)
    if selected_shelf:
        filter_conditions.append(Book.shelf == selected_shelf)

    if filter_conditions:
        query_obj = query_obj.filter(and_(*filter_conditions))

    # Contar quantos livros correspondem aos filtros ANTES de aplicar ordenação e .all()
    count_matching_books = query_obj.count()

    # Obter os livros para exibição (já filtrados)
    #books_for_display = query_obj.order_by(Book.title).all()
    books_for_display = query_obj.order_by(Book.id.desc()).limit(50).all()

    # Contagem total de livros cadastrados (para exibir o total geral)
    total_books_registered = Book.query.count()

    return render_template('index.html',
                           books=books_for_display,
                           query=query_term,
                           all_languages=all_languages,
                           selected_language=selected_language,
                           all_genres=all_genres,
                           selected_genre=selected_genre,
                           all_bookshelves=all_bookshelves,
                           selected_bookshelf=selected_bookshelf,
                           all_shelves=all_shelves,
                           selected_shelf=selected_shelf,
                           total_books_registered=total_books_registered,  # Contagem total de todos os livros
                           count_matching_books=count_matching_books)  # Contagem de livros que atendem aos filtros


@app.route('/register', methods=['GET', 'POST'])
def register_book():
    """Lida com o cadastro de novos livros."""
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        language = request.form.get('language')
        shelf = request.form.get('shelf')
        bookshelf = request.form.get('bookshelf')
        genre = request.form.get('genre')
        review = request.form.get('review')

        cover_option = request.form.get('cover_option')
        cover_path_for_db = None

        if not all([title, author]):
            flash('Título e Autor são campos obrigatórios.', 'error')
            return render_template('register.html', form_data=request.form)

        if cover_option == 'file':
            cover_image_file = request.files.get('cover_file')
            if cover_image_file and cover_image_file.filename != '':
                cover_path_for_db = save_image_from_file(cover_image_file)
                if not cover_path_for_db:
                    flash('Erro ao carregar imagem do arquivo. Verifique o tipo de arquivo.', 'error')
                    return render_template('register.html', form_data=request.form)
            else:
                logging.debug("Opção 'file' selecionada, mas nenhum arquivo foi fornecido para registro.")

        elif cover_option == 'camera':
            cover_image_data = request.form.get('cover_image_data')
            if cover_image_data:
                cover_path_for_db = save_image_from_base64(cover_image_data)
                if not cover_path_for_db:
                    flash('Erro ao salvar imagem da câmera. Tente novamente.', 'error')
                    return render_template('register.html', form_data=request.form)
            else:
                logging.debug("Opção 'camera' selecionada, mas dados da câmera estão vazios para registro.")

        elif cover_option == 'url':
            final_cover_url = request.form.get('final_cover_url')
            if final_cover_url:
                cover_path_for_db = save_image_from_url(final_cover_url)
                if not cover_path_for_db:
                    flash('Erro ao carregar imagem da URL. Verifique o link ou a conexão.', 'error')
                    return render_template('register.html', form_data=request.form)
            else:
                logging.debug("Opção 'url' selecionada, mas a URL final está vazia para registro.")
        # Se 'none' ou 'keep_current' for selecionado, cover_path_for_db permanece None ou o valor existente, que é o desejado.

        new_book = Book(
            title=title,
            author=author,
            language=language,
            genre=genre,
            shelf=shelf,
            bookshelf=bookshelf,
            review=review,
            cover_path=cover_path_for_db
        )

        db.session.add(new_book)
        try:
            db.session.commit()
            flash('Livro cadastrado com sucesso!', 'success')
            check_and_perform_backup()
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()  # Em caso de erro, desfaz a transação
            flash(f'Erro ao cadastrar livro: {e}', 'error')
            logging.error(f"Erro ao adicionar novo livro: {e}", exc_info=True)
            return render_template('register.html', form_data=request.form)

    return render_template('register.html', form_data={})


@app.route('/analyze_cover_via_gemini', methods=['POST'])
def analyze_cover_with_gemini():
    """
    Endpoint para receber uma imagem (da câmera), enviá-la ao Gemini,
    e retornar informações extraídas do livro.
    """
    if not model:
        current_app.logger.warning(
            "Serviço Gemini não está disponível devido à falta de API Key ou erro de inicialização.")
        return jsonify({"error": "Serviço de análise de capa indisponível."}), 503

    if 'image_data' not in request.files:
        current_app.logger.error("Nenhuma imagem recebida em /analyze_cover_via_gemini")
        return jsonify({"error": "Nenhuma imagem recebida."}), 400

    image_file = request.files['image_data']
    current_app.logger.info(f"Recebida imagem para análise: {image_file.filename}")

    try:
        image_bytes = image_file.read()
        # Tenta inferir o tipo MIME real do arquivo, fallback para JPEG
        mime_type = image_file.mimetype if image_file.mimetype else "image/jpeg"

        image_part = {"mime_type": mime_type, "data": image_bytes}

        prompt = '''
            A partir da imagem fornecida, obtenha os dados do livro: título, autor, gênero, idioma.
            Busque na internet uma breve resenha do livro. Adicione após a resenha uma nota, numa linha abaixo: --- Resenha gerada por IA.---
            Retorne os dados estritamente no formato JSON, sem texto adicional antes ou depois do JSON.
            Com exceção do título e do autor, escreva em portuguÊs.
    
            Exemplo de formato esperado:
            ```json
            {
                "title": "Título do Livro",
                "author": "Nome do Autor",
                "genre": "Gênero do Livro (Ex: Ficção Científica, Romance, Fantasia)",
                "language": "Idioma do Livro (Ex: Português, Inglês)",
                "review": "Uma breve resenha do livro, contendo um resumo e principais temas."
            }
            ```
            '''

        # Solicita explicitamente uma resposta JSON para o Gemini
        response = model.generate_content(
            [prompt, image_part],
            stream=False,
            generation_config={"response_mime_type": "application/json"}
        )

        gemini_output = response.text
        logging.debug(f"Resposta Gemini crua: {gemini_output}")

        extracted_data = {}
        try:
            parsed_json = json.loads(gemini_output)
            extracted_data["title"] = parsed_json.get("title", "")
            extracted_data["author"] = parsed_json.get("author", "")
            extracted_data["language"] = parsed_json.get("language", "")
            extracted_data["genre"] = parsed_json.get("genre", "")
            extracted_data["review"] = parsed_json.get("review", "")
        except json.JSONDecodeError as e:
            logging.error(
                f"Resposta do Gemini não é um JSON válido: {e}. Tentando parsear com regex. Resposta: {gemini_output}",
                exc_info=True)
            # Fallback mais robusto usando regex para extração de dados individuais
            extracted_data["title"] = re.search(r'"title":\s*"(.*?)"', gemini_output, re.DOTALL).group(1) if re.search(
                r'"title":\s*"(.*?)"', gemini_output, re.DOTALL) else ""
            extracted_data["author"] = re.search(r'"author":\s*"(.*?)"', gemini_output, re.DOTALL).group(
                1) if re.search(r'"author":\s*"(.*?)"', gemini_output, re.DOTALL) else ""
            extracted_data["genre"] = re.search(r'"genre":\s*"(.*?)"', gemini_output, re.DOTALL).group(1) if re.search(
                r'"genre":\s*"(.*?)"', gemini_output, re.DOTALL) else ""
            extracted_data["language"] = re.search(r'"language":\s*"(.*?)"', gemini_output, re.DOTALL).group(
                1) if re.search(r'"language":\s*"(.*?)"', gemini_output, re.DOTALL) else ""
            extracted_data["review"] = re.search(r'"review":\s*"(.*?)"', gemini_output, re.DOTALL).group(
                1) if re.search(r'"review":\s*"(.*?)"', gemini_output, re.DOTALL) else ""
            flash('A análise da capa retornou um formato inesperado. Alguns campos podem estar incompletos.', 'warning')

        current_app.logger.info(f"Dados extraídos do Gemini: {extracted_data}")
        return jsonify(extracted_data)

    except Exception as e:
        current_app.logger.error(f"Erro inesperado ao chamar a API do Gemini: {e}", exc_info=True)
        return jsonify({"error": f"Erro ao processar a imagem com o Gemini: {e}"}), 500


@app.route('/book/<book_id>')
def book_detail_route(book_id):
    """Exibe os detalhes de um livro específico."""
    book = db.session.get(Book, book_id)
    if book:
        return render_template('book_detail.html', book=book)
    flash('Livro não encontrado.', 'error')
    return redirect(url_for('index'))


@app.route('/edit/<book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash('Livro não encontrado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        book.title = request.form.get('title', book.title)
        book.author = request.form.get('author', book.author)
        book.genre = request.form.get('genre', book.genre)
        book.language = request.form.get('language', book.language)
        book.shelf = request.form.get('shelf', book.shelf)
        book.bookshelf = request.form.get('bookshelf', book.bookshelf)
        book.review = request.form.get('review', book.review)

        cover_option = request.form.get('cover_option')
        new_cover_path_candidate = None  # Caminho candidato para a nova capa

        if cover_option == 'file':
            cover_image_file = request.files.get('cover_file')
            if cover_image_file and cover_image_file.filename != '':
                temp_path = save_image_from_file(cover_image_file)
                if temp_path:
                    new_cover_path_candidate = temp_path
                else:
                    flash('Erro ao carregar nova capa do arquivo. Capa antiga mantida.', 'error')
        elif cover_option == 'camera':
            cover_image_data = request.form.get('cover_image_data')
            if cover_image_data:
                temp_path = save_image_from_base64(cover_image_data)
                if temp_path:
                    new_cover_path_candidate = temp_path
                else:
                    flash('Erro ao salvar nova capa da câmera. Capa antiga mantida.', 'error')
        elif cover_option == 'url':
            final_cover_url = request.form.get('final_cover_url')
            if final_cover_url:
                temp_path = save_image_from_url(final_cover_url)
                if temp_path:
                    new_cover_path_candidate = temp_path
                else:
                    flash('Erro ao carregar nova capa da URL. Capa antiga mantida.', 'error')
        # Se cover_option == 'current', new_cover_path_candidate permanece None,
        # e a capa não será alterada abaixo.

        # Atualiza a capa somente se uma nova foi processada com sucesso
        if new_cover_path_candidate:
            delete_existing_cover(book.cover_path)  # Deleta a antiga ANTES de atribuir a nova
            book.cover_path = new_cover_path_candidate
        # Se cover_option == 'current', nenhuma alteração em book.cover_path ocorre.

        try:
            db.session.commit()
            flash('Livro atualizado com sucesso!', 'success')
            check_and_perform_backup()
            return redirect(url_for('book_detail_route', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar livro: {e}', 'error')
            logging.error(f"Erro ao atualizar livro '{book.id}': {e}", exc_info=True)
            # Passar book_id para o template é redundante se book já é passado
            return render_template('edit_book.html', book=book)

    return render_template('edit_book.html', book=book)


@app.route('/delete/<book_id>', methods=['POST'])
def delete_book(book_id):
    """Exclui um livro."""
    book_to_delete = db.session.get(Book, book_id)

    if not book_to_delete:
        flash('Livro não encontrado para exclusão.', 'error')
        return redirect(url_for('index'))

    # Remove o arquivo da capa do livro, se existir
    delete_existing_cover(book_to_delete.cover_path)

    db.session.delete(book_to_delete)
    try:
        db.session.commit()
        check_and_perform_backup()
        flash('Livro excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir livro: {e}', 'error')
        logging.error(f"Erro ao excluir livro '{book_id}': {e}", exc_info=True)

    return redirect(url_for('index'))


# ... (resto do seu código app.py) ...

@app.route('/add_shelf_with_books', methods=['GET', 'POST'])
def add_shelf_with_books():
    if request.method == 'POST':
        bookshelf_name = request.form.get('bookshelf_name', '').strip()
        shelf_name = request.form.get('shelf_name', '').strip()

        titles = request.form.getlist('titles[]')
        authors = request.form.getlist('authors[]')

        if not bookshelf_name or not shelf_name:
            flash('Nome da Estante e da Prateleira são obrigatórios.', 'error')
            # Re-renderiza o formulário com os dados já inseridos para os livros
            # Isso é um pouco mais complexo de fazer perfeitamente sem JS avançado no lado do cliente
            # para reconstruir as linhas, então vamos simplificar por agora.
            # O ideal seria passar 'titles' e 'authors' de volta para o template.
            return render_template('add_shelf_with_books.html',
                                   bookshelf_name=bookshelf_name,
                                   shelf_name=shelf_name)

        books_added_count = 0
        for i in range(len(titles)):
            title = titles[i].strip()
            author = authors[i].strip()

            if title and author:  # Só adiciona se título e autor não estiverem em branco
                new_book = Book(
                    title=title,
                    author=author,
                    bookshelf=bookshelf_name,
                    shelf=shelf_name
                    # Outros campos como genre, language, review, cover_path serão None/default
                )
                db.session.add(new_book)
                books_added_count += 1

        if books_added_count > 0:
            try:
                db.session.commit()
                flash(
                    f'{books_added_count} livro(s) adicionado(s) à estante "{bookshelf_name}", prateleira "{shelf_name}" com sucesso!',
                    'success')
                check_and_perform_backup()  # Verifica backup após o lote de alterações
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar livros: {e}', 'error')
                logging.error(f"Erro ao salvar lote de livros: {e}", exc_info=True)
        else:
            flash('Nenhum livro válido (com título e autor) foi fornecido para adicionar.', 'warning')

        return redirect(url_for('index'))

    return render_template('add_shelf_with_books.html')


@app.route('/analyze_shelf_via_gemini', methods=['POST'])
def analyze_shelf_via_gemini():
    """
    Endpoint para receber uma imagem (da câmera), enviá-la ao Gemini,
    e retornar informações extraídas do livro.
    """
    if not model:
        current_app.logger.warning(
            "Serviço Gemini não está disponível devido à falta de API Key ou erro de inicialização.")
        return jsonify({"error": "Serviço de análise de capa indisponível."}), 503

    if 'shelf_image_data' not in request.files:
        current_app.logger.error("Nenhuma imagem recebida em /analyze_cover_via_gemini")
        return jsonify({"error": "Nenhuma imagem recebida."}), 400

    image_file = request.files['shelf_image_data']
    current_app.logger.info(f"Recebida imagem para análise: {image_file.filename}")

    try:
        image_bytes = image_file.read()
        # Tenta inferir o tipo MIME real do arquivo, fallback para JPEG
        mime_type = image_file.mimetype if image_file.mimetype else "image/jpeg"

        image_part = {"mime_type": mime_type, "data": image_bytes}

        prompt = '''
            A partir da imagem fornecida, conte quantas lombadas de livros existem
            na imagem, obtenha de cada lombada o título e o autor, e faça uma lista com título e autor de cada livro.
            Deduza qual é o idioma pelo título do livro.
            
            
            Busque na internet informações de cada livro com base na lista de título e autor, 
            e obtenha o gênero e uma breve resenha de cada livro. 
            Adicione após a resenha numa linha abaixo:  Resenha gerada por IA.
            
            Retorne os dados estritamente no formato JSON, sem texto adicional antes ou depois do JSON.
            
            Com exceção do título e do autor, escreva em portuguÊs.
    
            Exemplo de formato esperado:
            ```json
            [{
                "title": "Título do Livro",
                "author": "Nome do Autor",
                "genre": "Gênero do Livro (Ex: Ficção Científica, Romance, Fantasia)",
                "language": "Idioma do Livro (Ex: Português, Inglês)",
                "review": "Uma breve resenha do livro, contendo um resumo e principais temas."
            }]
            ```
            '''

        # Solicita explicitamente uma resposta JSON para o Gemini
        response = model.generate_content(
            [prompt, image_part],
            stream=False,
            generation_config={"response_mime_type": "application/json"}
        )

        # ... (previous code in analyze_shelf_via_gemini) ...

        gemini_output = response.text
        logging.debug(f"Resposta Gemini (análise de prateleira) crua: {gemini_output}")
        # The print(response.text) you added is helpful for debugging, you can keep or remove it.
        # print(response.text) # This line was in your provided app.py

        # MODIFICATION STARTS HERE
        try:
            # Gemini is expected to return a list of book objects
            list_of_books_from_gemini = json.loads(gemini_output)

            if not isinstance(list_of_books_from_gemini, list):
                logging.error(f"Resposta do Gemini para prateleira não é uma lista JSON: {gemini_output}")
                # Attempt a fallback if it's a dictionary containing a "books" key
                if isinstance(list_of_books_from_gemini, dict) and \
                        "books" in list_of_books_from_gemini and \
                        isinstance(list_of_books_from_gemini.get("books"), list):
                    list_of_books_from_gemini = list_of_books_from_gemini["books"]
                    logging.info("Fallback: Usada a chave 'books' da resposta do Gemini.")
                else:
                    flash('A análise da prateleira retornou um formato inesperado (não é uma lista de livros).',
                          'warning')
                    return jsonify([]), 200

            processed_books_for_frontend = []
            for book_data_from_gemini in list_of_books_from_gemini:
                if isinstance(book_data_from_gemini, dict):
                    # Ensure all expected keys are present for the frontend
                    processed_book = {
                        "title": book_data_from_gemini.get("title", ""),
                        "author": book_data_from_gemini.get("author", ""),
                        "genre": book_data_from_gemini.get("genre", ""),
                        "language": book_data_from_gemini.get("language", ""),
                        "review": book_data_from_gemini.get("review", "")
                    }
                    # Add to list if title and author are present
                    if processed_book["title"] and processed_book["author"]:
                        processed_books_for_frontend.append(processed_book)
                    else:
                        logging.warning(
                            f"Livro do Gemini descartado por falta de título/autor: {book_data_from_gemini}")
                else:
                    logging.warning(
                        f"Item inesperado na lista do Gemini (não é um dicionário de livro): {book_data_from_gemini}")

            if not processed_books_for_frontend and list_of_books_from_gemini:
                logging.info(
                    f"Nenhum livro válido (com título/autor) encontrado na lista processada do Gemini: {list_of_books_from_gemini}")

            current_app.logger.info(f"Livros processados para enviar ao frontend: {processed_books_for_frontend}")
            return jsonify(processed_books_for_frontend)

        except json.JSONDecodeError as e:
            logging.error(f"Resposta do Gemini para prateleira não é um JSON válido: {e}. Resposta: {gemini_output}",
                          exc_info=True)
            flash('A análise da prateleira retornou um formato que não pôde ser processado (JSON inválido).', 'error')
            return jsonify([]), 500
        except Exception as e_gen:  # Catch other general exceptions during response processing
            logging.error(f"Erro ao processar resposta do Gemini para prateleira: {e_gen}. Resposta: {gemini_output}",
                          exc_info=True)
            flash('Ocorreu um erro ao processar os dados da prateleira.', 'error')
            return jsonify([]), 500
        # MODIFICATION ENDS HERE

    except Exception as e:  # Catches errors in the Gemini call or image reading
        current_app.logger.error(f"Erro inesperado ao analisar prateleira com Gemini: {e}", exc_info=True)
        return jsonify({"error": f"Erro ao processar a imagem da prateleira: {str(e)}"}), 500


# --- Execução da Aplicação ---
# ... (resto do seu código)


# --- Execução da Aplicação ---
if __name__ == '__main__':
    # Cria as tabelas do banco de dados se elas não existirem
    with app.app_context():
        db.create_all()
        logging.info("Tabelas do banco de dados verificadas/criadas.")
        backup_database()  # <<------------------------------------ ADICIONADO
        app.config['DB_CHANGES_COUNT'] = 0  # <<----------------- ADICIONADO: Reseta contador

    ssl_cert_path = BASE_DIR / "ssl" / "cert.pem"  # <<------------- MODIFICADO: Usando Pathlib
    ssl_key_path = BASE_DIR / "ssl" / "key.pem"  # <<------------- MODIFICADO: Usando Pathlib

    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=(ssl_cert_path, ssl_key_path))
    # app.run(debug=True, host='0.0.0.0', port=5000)
