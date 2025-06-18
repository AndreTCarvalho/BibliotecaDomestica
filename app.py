import os
import json
import base64
from datetime import datetime  # Para nomes de arquivos únicos

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

import google.generativeai as genai

# Importa a configuração e o modelo do banco de dados
from config import Config
from models import db, Livro

# Inicializa o aplicativo Flask
app = Flask(__name__)
# Carrega as configurações do arquivo Config
app.config.from_object(Config)

# Inicializa o banco de dados com o aplicativo Flask
db.init_app(app)

# Configura a chave da API do Gemini
genai.configure(api_key=app.config['GEMINI_API_KEY'])


# --- Funções Auxiliares ---

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def delete_local_cover_file(filename):
    """Deleta um arquivo de capa local se ele existir e não for uma URL ou base64."""
    if filename and not filename.startswith('http') and not filename.startswith('data:image'):
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                app.logger.info(f"Capa local antiga deletada: {full_path}")
            except OSError as e:
                app.logger.error(f"Erro ao deletar capa local antiga {full_path}: {e}")


# --- Rotas ---

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve arquivos da pasta de uploads."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def index():
    """Exibe a lista de livros, com opções de ordenação e filtro."""
    sort_by = request.args.get('sort_by', 'titulo')
    genre_filter = request.args.get('genero')
    language_filter = request.args.get('idioma')

    query = Livro.query

    if genre_filter:
        query = query.filter(Livro.genero.ilike(f'%{genre_filter}%'))
    if language_filter:
        query = query.filter(Livro.idioma.ilike(f'%{language_filter}%'))

    if sort_by == 'autor':
        livros = query.order_by(Livro.autor).all()
    else:
        livros = query.order_by(Livro.titulo).all()

    generos_unicos = sorted(list(set(livro.genero for livro in Livro.query.filter(Livro.genero.isnot(None)).all())))
    idiomas_unicos = sorted(list(set(livro.idioma for livro in Livro.query.filter(Livro.idioma.isnot(None)).all())))

    return render_template('index.html', livros=livros,
                           generos_unicos=generos_unicos,
                           idiomas_unicos=idiomas_unicos,
                           selected_genre=genre_filter,
                           selected_language=language_filter)


@app.route('/book/<int:book_id>')
def book_detail(book_id):
    """Exibe os detalhes de um livro específico."""
    book = Livro.query.get_or_404(book_id)
    return render_template('book_detail.html', book=book)


@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    """Adiciona um novo livro ao banco de dados."""
    if request.method == 'POST':
        # Coleta os dados do formulário
        titulo = request.form['titulo']
        autor = request.form['autor']
        genero = request.form.get('genero')
        idioma = request.form.get('idioma')
        resenha = request.form.get('resenha')
        estante = request.form.get('estante')
        prateleira = request.form.get('prateleira')

        capa_path = None  # Inicializa o caminho da capa como None

        cover_option = request.form.get('cover_option')

        # Lida com a capa com base na opção selecionada
        if cover_option == 'file':
            if 'capa_file' in request.files and request.files['capa_file'].filename:
                file = request.files['capa_file']
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    capa_path = filename  # Armazena apenas o nome do arquivo no DB
                else:
                    flash(f'Tipo de arquivo não permitido para {file.filename}', 'danger')

        elif cover_option == 'camera':
            if request.form.get('capa_camera_data'):
                data_url = request.form.get('capa_camera_data')
                if data_url.startswith('data:image'):
                    try:
                        header, encoded = data_url.split(",", 1)
                        data = base64.b64decode(encoded)
                        # Gerar nome de arquivo único
                        filename = secure_filename(f"camera_upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png")
                        file_save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        with open(file_save_path, "wb") as fh:
                            fh.write(data)
                        capa_path = filename  # Armazena apenas o nome do arquivo
                    except Exception as e:
                        flash(f'Erro ao processar dados da câmera: {e}', 'danger')
                else:
                    flash('Dados da imagem da câmera inválidos.', 'danger')

        elif cover_option == 'url':
            if request.form.get('capa_url'):
                capa_path = request.form.get('capa_url')
                # Por enquanto, apenas armazena a URL. Baixar a imagem exigiria mais lógica.
                flash('Download de imagem por URL não implementado; apenas a URL foi salva.', 'warning')

        # Se 'none' for selecionado, 'capa_path' permanece None.

        new_book = Livro(
            titulo=titulo,
            autor=autor,
            genero=genero,
            idioma=idioma,
            resenha=resenha,
            capa=capa_path,  # Será None se nenhuma opção de capa válida for selecionada
            estante=estante,
            prateleira=prateleira
        )
        db.session.add(new_book)
        db.session.commit()
        flash('Livro adicionado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('book_form.html')


@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """Edita um livro existente no banco de dados."""
    book = Livro.query.get_or_404(book_id)
    old_capa_filename = book.capa  # Guarda o nome do arquivo da capa antiga (ou URL/base64)

    if request.method == 'POST':
        # Atualiza os campos do livro
        book.titulo = request.form['titulo']
        book.autor = request.form['autor']
        book.genero = request.form.get('genero')
        book.idioma = request.form.get('idioma')
        book.resenha = request.form.get('resenha')
        book.estante = request.form.get('estante')
        book.prateleira = request.form.get('prateleira')

        new_capa_path = old_capa_filename  # Padrão: mantém a capa atual se nada mudar

        cover_option = request.form.get('cover_option')

        # Flag para indicar se a capa local antiga deve ser deletada
        should_delete_old_local_cover = False

        if cover_option == 'file':
            if 'capa_file' in request.files and request.files['capa_file'].filename:
                file = request.files['capa_file']
                if allowed_file(file.filename):
                    should_delete_old_local_cover = True  # Nova imagem, então deletar a antiga
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    new_capa_path = filename  # Armazena o nome do arquivo
                else:
                    flash(f'Tipo de arquivo não permitido para {file.filename}', 'danger')
                    # Se o upload falhar, mantém a capa antiga
                    new_capa_path = old_capa_filename
            else:  # Opção 'file' selecionada, mas nenhum arquivo enviado (limpa capa)
                should_delete_old_local_cover = True
                new_capa_path = None

        elif cover_option == 'camera':
            if request.form.get('capa_camera_data'):
                data_url = request.form.get('capa_camera_data')
                if data_url.startswith('data:image'):
                    try:
                        should_delete_old_local_cover = True  # Nova imagem da câmera, deletar a antiga
                        header, encoded = data_url.split(",", 1)
                        data = base64.b64decode(encoded)
                        filename = secure_filename(f"camera_upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png")
                        file_save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        with open(file_save_path, "wb") as fh:
                            fh.write(data)
                        new_capa_path = filename  # Armazena o nome do arquivo
                    except Exception as e:
                        flash(f'Erro ao processar dados da câmera: {e}', 'danger')
                        new_capa_path = old_capa_filename  # Reverte para a capa antiga se houver erro
                else:
                    flash('Dados da imagem da câmera inválidos.', 'danger')
                    new_capa_path = old_capa_filename  # Reverte para a capa antiga se houver erro
            else:  # Opção 'camera' selecionada, mas sem dados (limpa capa)
                should_delete_old_local_cover = True
                new_capa_path = None

        elif cover_option == 'url':
            if request.form.get('capa_url'):
                should_delete_old_local_cover = True  # Nova URL, deletar a antiga
                new_capa_path = request.form.get('capa_url')
                flash('Download de imagem por URL não implementado; apenas a URL foi salva.', 'warning')
            else:  # Opção 'url' selecionada, mas sem URL (limpa capa)
                should_delete_old_local_cover = True
                new_capa_path = None

        elif cover_option == 'none':
            # O usuário escolheu explicitamente 'Nenhuma'
            should_delete_old_local_cover = True  # Deletar capa local antiga
            new_capa_path = None  # Definir como None no DB

        elif cover_option == 'current_camera':
            # O usuário escolheu manter a imagem da câmera base64 atual.
            # O campo 'capa_camera_data' conterá o valor se for uma edição de um livro com capa de câmera.
            data_url = request.form.get('capa_camera_data')
            if data_url and data_url.startswith('data:image'):
                new_capa_path = data_url  # Mantém a string base64 se for válida
            else:
                new_capa_path = None  # Se os dados forem inválidos, limpa a capa
                should_delete_old_local_cover = True  # Se a capa era um arquivo, deleta

        # Lógica para "Manter Capa Atual" se nenhuma opção de capa explícita foi selecionada
        # Ou se a opção "none" ou "current_camera" foi selecionada no JS mas não havia capa antiga
        if request.form.get('keep_current_cover') == 'true' and new_capa_path is None:
            new_capa_path = old_capa_filename
            should_delete_old_local_cover = False  # Não deletar se estamos mantendo

        # Executa a deleção do arquivo físico antigo, se necessário
        # Só deleta se o old_capa_filename existia e era um arquivo local, E
        # se uma nova opção o substitui OU 'none' foi selecionado, E
        # se o nome da capa antiga for diferente do novo (evita deletar o mesmo arquivo)
        if should_delete_old_local_cover and old_capa_filename \
                and not old_capa_filename.startswith('http') \
                and not old_capa_filename.startswith('data:image') \
                and old_capa_filename != new_capa_path:  # Verifica se é um arquivo local e diferente
            delete_local_cover_file(old_capa_filename)

        book.capa = new_capa_path  # Atualiza o campo 'capa' do livro

        db.session.commit()
        flash('Livro atualizado com sucesso!', 'success')
        return redirect(url_for('book_detail', book_id=book.id))
    return render_template('book_form.html', book=book)


@app.route('/delete_book/<int:book_id>', methods=['GET', 'POST'])
def delete_book(book_id):
    """Deleta um livro e sua capa associada."""
    book = Livro.query.get_or_404(book_id)
    if request.method == 'POST':
        # Deleta a imagem da capa antes de deletar o registro do livro
        delete_local_cover_file(book.capa)
        db.session.delete(book)
        db.session.commit()
        flash('Livro deletado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('confirm_delete.html', book=book)


@app.route('/bulk_upload', methods=['GET', 'POST'])
def bulk_upload():
    """Permite o upload em massa de livros, com preenchimento via Gemini."""
    if request.method == 'POST':
        books_to_add = []

        # Itera sobre os campos do formulário para encontrar entradas de livro
        for key, value in request.form.items():
            if key.startswith('titulo_'):
                index = key.split('_')[1]
                titulo = value
                autor = request.form.get(f'autor_{index}')
                genero = request.form.get(f'genero_{index}')
                idioma = request.form.get(f'idioma_{index}')
                resenha = request.form.get(f'resenha_{index}')
                estante = request.form.get(f'estante_{index}')
                prateleira = request.form.get(f'prateleira_{index}')
                capa_path = None

                cover_option_key = f'cover_option_{index}'
                cover_option = request.form.get(cover_option_key)

                if cover_option == 'file':
                    capa_file_key = f'capa_file_{index}'
                    if capa_file_key in request.files and request.files[capa_file_key].filename:
                        file = request.files[capa_file_key]
                        if allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            capa_path = filename  # Armazena nome do arquivo
                elif cover_option == 'url':
                    capa_url_key = f'capa_url_{index}'
                    if request.form.get(capa_url_key):
                        capa_path = request.form.get(capa_url_key)
                elif cover_option == 'camera':
                    capa_camera_data_key = f'capa_camera_data_{index}'
                    if request.form.get(capa_camera_data_key):
                        data_url = request.form.get(capa_camera_data_key)
                        if data_url.startswith('data:image'):
                            header, encoded = data_url.split(",", 1)
                            data = base64.b64decode(encoded)
                            filename = secure_filename(
                                f"camera_upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{index}.png")
                            file_save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            with open(file_save_path, "wb") as fh:
                                fh.write(data)
                            capa_path = filename  # Armazena nome do arquivo

                books_to_add.append(Livro(
                    titulo=titulo,
                    autor=autor,
                    genero=genero,
                    idioma=idioma,
                    resenha=resenha,
                    capa=capa_path,
                    estante=estante,
                    prateleira=prateleira
                ))

        db.session.add_all(books_to_add)
        db.session.commit()
        flash('Livros adicionados em massa com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('bulk_upload.html')


@app.route('/process_camera_image', methods=['POST'])
def process_camera_image():
    """Processa a imagem da câmera com a API Gemini para extrair informações do livro."""
    app.logger.info("Iniciando processamento de imagem da câmera para Gemini.")

    if 'image' not in request.files:
        app.logger.warning("Nenhuma imagem fornecida na requisição /process_camera_image.")
        return jsonify({'error': 'Nenhuma imagem fornecida'}), 400

    file = request.files['image']
    if not file or not file.filename:
        app.logger.warning("Nenhum arquivo selecionado ou nome de arquivo vazio em /process_camera_image.")
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    if allowed_file(file.filename):
        filename = secure_filename(f"temp_camera_upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png")
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(temp_path)
            app.logger.info(f"Imagem temporária salva em: {temp_path}")

            model = genai.GenerativeModel('gemini-pro-vision')
            app.logger.info("Modelo Gemini inicializado.")

            with open(temp_path, 'rb') as f:
                image_data = f.read()

            prompt = "Extraia as seguintes informações deste livro: Título, Autor, Gênero, Idioma, Resenha (um breve resumo se possível). Retorne em formato JSON."

            app.logger.info("Enviando imagem para a API Gemini...")
            # Adicionado um timeout para a requisição Gemini para evitar hangs
            # O timeout abaixo é para a biblioteca do Gemini, não para a requisição HTTP do Flask.
            # Se o problema for de rede entre Flask e Gemini, este timeout pode ajudar a identificar.
            response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': image_data}],
                                              request_options={"timeout": 60})  # 60 segundos de timeout

            app.logger.info(
                f"Resposta da API Gemini recebida. Conteúdo: {response.text[:200]}...")  # Log dos primeiros 200 caracteres

            try:
                extracted_data = json.loads(response.text.strip())
                app.logger.info("Resposta Gemini parseada como JSON com sucesso.")
            except json.JSONDecodeError:
                # Se não for JSON, tenta usar a resposta bruta na resenha
                extracted_data = {"resenha": response.text.strip()}
                app.logger.warning("Resposta Gemini não é JSON válido. Usando texto bruto para resenha.")

            os.remove(temp_path)
            app.logger.info(f"Imagem temporária {temp_path} removida.")
            return jsonify({'success': True, 'data': extracted_data, 'temp_image_path': filename})

        except Exception as e:
            app.logger.error(f"Erro ao processar imagem com Gemini: {e}",
                             exc_info=True)  # exc_info=True para traceback completo
            if os.path.exists(temp_path):
                os.remove(temp_path)
                app.logger.info(f"Imagem temporária {temp_path} removida após erro.")
            return jsonify({'error': f'Erro ao processar imagem com Gemini: {str(e)}'}), 500

    app.logger.warning(f"Arquivo '{file.filename}' não permitido em /process_camera_image.")
    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400


@app.route('/process_shelf_image', methods=['POST'])
def process_shelf_image():
    """Processa a imagem da estante com a API Gemini para extrair informações de múltiplos livros."""
    app.logger.info("Iniciando processamento de imagem da estante para Gemini.")

    if 'image' not in request.files:
        app.logger.warning("Nenhuma imagem fornecida na requisição /process_shelf_image.")
        return jsonify({'error': 'Nenhuma imagem fornecida'}), 400

    file = request.files['image']
    if not file or not file.filename:
        app.logger.warning("Nenhum arquivo selecionado ou nome de arquivo vazio em /process_shelf_image.")
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    if allowed_file(file.filename):
        filename = secure_filename(f"temp_shelf_upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png")
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(temp_path)
            app.logger.info(f"Imagem temporária da estante salva em: {temp_path}")

            model = genai.GenerativeModel('gemini-pro-vision')
            app.logger.info("Modelo Gemini inicializado para estante.")

            with open(temp_path, 'rb') as f:
                image_data = f.read()

            prompt = "Dada a imagem de uma estante de livros, liste os livros detectados. Para cada livro, tente identificar Título, Autor, Gênero e Idioma. Formate a saída como um array de objetos JSON, onde cada objeto representa um livro e possui as chaves 'titulo', 'autor', 'genero' e 'idioma'. Se não puder identificar um campo, deixe-o como null."

            app.logger.info("Enviando imagem da estante para a API Gemini...")
            response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': image_data}],
                                              request_options={"timeout": 90})  # Aumentei timeout para estante

            app.logger.info(f"Resposta da API Gemini para estante recebida. Conteúdo: {response.text[:200]}...")

            try:
                extracted_books_data = json.loads(response.text.strip())
                app.logger.info("Resposta Gemini para estante parseada como JSON com sucesso.")
            except json.JSONDecodeError:
                extracted_books_data = []  # Retorna vazio se não for JSON
                flash(
                    'Não foi possível extrair dados em formato JSON da imagem da estante. Tente novamente ou insira manualmente.',
                    'warning')
                app.logger.warning("Resposta Gemini para estante não é JSON válido.")

            os.remove(temp_path)
            app.logger.info(f"Imagem temporária da estante {temp_path} removida.")
            return jsonify({'success': True, 'books': extracted_books_data})

        except Exception as e:
            app.logger.error(f"Erro ao processar imagem da estante com Gemini: {e}", exc_info=True)
            if os.path.exists(temp_path):
                os.remove(temp_path)
                app.logger.info(f"Imagem temporária da estante {temp_path} removida após erro.")
            return jsonify({'error': f'Erro ao processar imagem da estante com Gemini: {str(e)}'}), 500

    app.logger.warning(f"Arquivo '{file.filename}' não permitido em /process_shelf_image.")
    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400


# --- Inicialização da Aplicação ---

if __name__ == '__main__':
    # Configura o logger para exibir mensagens no console (útil para depuração)
    import logging

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    with app.app_context():
        # Cria a pasta de uploads se ela não existir
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            app.logger.info(f"Diretório de uploads criado: {app.config['UPLOAD_FOLDER']}")
        db.create_all()
        app.logger.info("Tabelas do banco de dados verificadas/criadas.")

    # Imprime o MAX_CONTENT_LENGTH configurado (para depuração)
    app.logger.info(f"MAX_CONTENT_LENGTH configurado: {app.config.get('MAX_CONTENT_LENGTH')} bytes")

    # Inicia o servidor Flask
    # Removi o ssl_context por padrão para evitar problemas de certificado em dev
    # Se precisar de HTTPS em desenvolvimento, configure adequadamente (mkcert, adhoc, etc.)
    app.run(debug=True, host='0.0.0.0', port=5000)  # Use a porta 5000 explicitamente