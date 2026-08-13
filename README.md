# 🎓 Teste Vocacional IA com Gemini & Streamlit

Este é um aplicativo web interativo de orientação vocacional construído com Python, Streamlit e a API do Google Gemini.

## 🔑 1. Obter a API Key

Para que a inteligência artificial funcione, você precisa de uma chave gratuita do Google:
1. Acesse o **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Faça login e clique em **"Create API key"**.
3. Copie a chave gerada (ela começa com `AIzaSy...`) e guarde-a.

## 💻 2. Instalação e Configuração

Abra o seu terminal e execute os comandos abaixo na pasta do projeto.

**Linux/macOS:**
> python3 -m venv .venv
> source .venv/bin/activate

**Instalar dependências:**
> pip install google-genai streamlit python-dotenv

**Configurar a chave da API:**
Crie um arquivo chamado `.env` na raiz do projeto e adicione o seguinte conteúdo:
> GEMINI_API_KEY=cole_sua_chave_api_aqui_sem_aspas

## 🚀 3. Como Rodar o Projeto

Com o ambiente ativado e o `.env` configurado, inicie a aplicação executando:
> streamlit run app.py