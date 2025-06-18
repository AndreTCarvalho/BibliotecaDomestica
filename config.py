import os

class Config:
    # Define o caminho do banco de dados SQLite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///minha_biblioteca.db'
    # Desabilita o rastreamento de modificações do SQLAlchemy para economizar recursos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Define a chave secreta para segurança da sessão do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma_chave_secreta_muito_segura'
    # Define a pasta onde as capas dos livros serão armazenadas
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/img')
    # Define os tipos de arquivo permitidos para upload de imagens
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    # Chave da API do Google Gemini (substitua pela sua chave real)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'SUA_CHAVE_API_DO_GEMINI_AQUI'

    # Adicione esta linha para aumentar o limite de upload (ex: 50 MB)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024 # 50 Megabytes