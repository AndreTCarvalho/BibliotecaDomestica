from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Inicializa o objeto SQLAlchemy
db = SQLAlchemy()

class Livro(db.Model):
    # Define o nome da tabela no banco de dados
    __tablename__ = 'livros'

    # Define as colunas da tabela
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    autor = db.Column(db.String(255), nullable=False)
    genero = db.Column(db.String(100))
    idioma = db.Column(db.String(50))
    resenha = db.Column(db.Text)
    capa = db.Column(db.String(255))  # Caminho da imagem da capa
    estante = db.Column(db.String(100))
    prateleira = db.Column(db.String(100))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        # Representação do objeto Livro para facilitar a depuração
        return f"<Livro {self.titulo} por {self.autor}>"