# 📚 Biblioteca Doméstica

![image](https://github.com/user-attachments/assets/568aa059-efea-4840-94c5-8044c272b458)

Um sistema para catalogar e gerenciar sua biblioteca pessoal utilizando **Google Gemini**.

O próprio código em Python, HTML, JS e CSS foi gerado 100% pelo **Google Gemini** (em um único prompt!).

![image](https://github.com/user-attachments/assets/894b4bad-2427-4d8a-b05d-15354c1e8277)


### ✨ Motivação

**Oportunidade:** Quem é apaixonado por livros quer ter sua biblioteca pessoal sempre organizada.

**Problema:** Aplicativos e softwares que se propõem a fazer isso requerem cadastro manual dos livros, ou disponibilizam, quando muito, ferramentas ineficientes de busca das informações pelo código ISBN.

**Solução:** Aplicativo Web que **obtém as informações a partir de fotos tiradas dos livros**.  Para isso, utilizamos a IA do **Google Gemini** para tornar essa tarefa mais eficiente.

### ⚙️ Como Funciona

O **Biblioteca Doméstica** é uma aplicação Web com um CRUD básico que permite adicionar, editar, buscar e excluir livros de uma lista.
Seu diferencial é a utilização do **Gemini** para simplificar o processo de cadastro através do processamento de imagens.

![image](https://github.com/user-attachments/assets/e575357b-cd02-4cc6-a915-ae894976a4c8)

Exemplo com uma lista de livros salvos:

![image](https://github.com/user-attachments/assets/8e90c06a-5d82-4329-8c7b-ed4f2ac66e83)

O fluxo de navegação é simples e eficaz:

![image](https://github.com/user-attachments/assets/37b0cf40-eb2c-4d67-bd06-49791d1ba020)




### 🤖 Inteligência Artificial Integrada

O processamento de IA utilizou apenas um Cliente da API Google GenAI, retornando todas as informações solicitadas: Título do Livro, Autor, Idioma e Resenha.

![image](https://github.com/user-attachments/assets/9045dff1-141d-4b4d-baf2-06c90d88716c)

Finalmente uma forma fácil de cadastrar e gerenciar seus livros! E o Gemini ainda gera uma resenha e pode classificar o livro segundo idioma, gênero literário, etc.

![image](https://github.com/user-attachments/assets/4ff4d037-d73e-4b07-bc46-d4b7f660910b)

Obtenha os dados do livro por fotos da capa, da lombada, da ficha catalográfica ou do código ISBN:

![image](https://github.com/user-attachments/assets/6ad1c02a-1f5d-4c48-86aa-0457b0d3cd66)


### 🚀 Como Rodar

Instruções para executar o projeto localmente:

1.  **Clone o repositório:**

3.  **Instale as dependências:**

    ```bash
    pip -q install google-genai
    pip -q install flask
    etc.
    
    
    ```
5.  **Escolha a Aplicação e Execute o código em Python**

    * Para utilização de um IA com um Cliente da API GenAI: execute python **app.py**;
    * Futuramente, para utilização de Agentes: execute python **app_agetes.py**

6.  **Abra no navegador:** Acesse `http://localhost:5000`.

   

### 👷‍♂️ Sobre o Projeto

Este projeto teve como objetivo colocar em prática os conceitos aprendidos sobre Gemini Google na Imersão de IA promovida pela Alura de 12 a 16 de maio de 2025.

Trata-se de um protótipo. Por esse motivo, a persistência do dados foi feita em um arquivo JSON, e não em um banco de dados.

Como próximos passos, pretendemos explorar o uso de agentes para dividir o trabalho em funções atômicas, a saber: identificar o tipo de imagem, obter os dados do livro de forma otimizada a partir de cada tipo de imagem, obter a resenha, e fazer revisões e verificações.

Futuro: 

![image](https://github.com/user-attachments/assets/49902804-4721-4b7e-8552-eb24a53e542d)

E mais! Cadastre vários livros de uma instante de uma só vez!

![image](https://github.com/user-attachments/assets/18a1c0da-1c4b-4a98-8fb3-dd97881b3d51)





### ✉️ Contato

André Tomaz de Carvalho - [andre.carvalho.eng@gmail.com](andre.carvalho.eng@gmail.com)

