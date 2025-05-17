# 📚 Biblioteca Doméstica

Um sistema para catalogar e gerenciar sua biblioteca pessoal utilizando Google Gemini.

### ✨ Motivação

**Oportunidade:** Quem é apaixonado por livros quer ter sua biblioteca pessoal organizada.

**Problema:** Aplicativos e softwares disponíveis para isso requerem o cadastro manual dos livros, ou propõem quando muito sistemas ineficientes de busca das informações pelo código ISBN.

**Solução:** Criar um aplicativo Web, pensado para ser usado no celular, que **obtém as informações a partir de fotos tiradas dos livros**.  Para isso, utilizamos a **IA** do Google Gemini para tornar essa tarefa mais eficiente.

### ⚙️ Como Funciona

O **Biblioteca Doméstica** é uma aplicação Web com um CRUD básico que permite adicionar, editar, buscar e excluir livros de uma lista.
O diferencial da é a utilização do Gemini Google para simplificar o processo de cadastro através do processamento de imagens.

![image](https://github.com/user-attachments/assets/3b08f460-ae6a-4f9d-9bf5-f07cd2a36400)


### 🤖 Inteligência Artificial Integrada

Duas abordagens de IA foram implementadas. 

A primeira abordagem, implementada em **app.py**, utilizou apenas um Cliente da API Google GenAI, retornando todas as informações solicitadas: Título do Livro, Autor, Idioma e Resenha.

![image](https://github.com/user-attachments/assets/b3de9912-39b6-47a9-b6b6-ee04a411cd02)


A segunda abordagem explorou o conceito de Agentes de IA, implementando a estrutura ilustrada abaixo.

![image](https://github.com/user-attachments/assets/49902804-4721-4b7e-8552-eb24a53e542d)


### 🚀 Como Rodar

Instruções para executar o projeto localmente:

1.  **Clone o repositório:**

3.  **Instale as dependências:**

    ```bash
    npm install  # Ou yarn install
    ```
5.  **Escolha a Aplicação e Execute o código em Python**

    * Para utilização de um IA com um Cliente da API GenAI: execute python **app;py**;

    * Para utilização de Agentes com a API : execute python **app_agents.py**;

6.  **Abra no navegador:** Acesse `http://localhost:5000`.

   

### 👷‍♂️ Sobre o Projeto

Este projeto teve como objetivo colocar em prática os conceitos aprendidos sobre Gemini Google na Imersão de IA promovida pela Alura de 12 a 16 de maio de 2025.

   **OBS: TODO O CÓDIGO DESTA APLICAÇÂO FOI GERADO PELO GEMINI EM UM ÚNICO PROMPT!!! Confira a documentação.**

Trata-se de um protótipo. Por esse motivo, a persistência do dados foi feita em um arquivo JSON, e não em um banco de dados. Colaborações são bem vindas.

### 📄 Licença

Distribuído sob a Licença GNU 3.0.

### ✉️ Contato

André Tomaz de Carvalho - [andre.carvalho.eng@gmail.com](andre.carvalho.eng@gmail.com)

