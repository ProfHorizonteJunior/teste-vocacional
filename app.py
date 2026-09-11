import os
import json
import re
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Carrega as variáveis de ambiente
load_dotenv()

st.set_page_config(page_title="Teste Vocacional IA", page_icon="🎓", layout="wide")

# ==========================================
# GERENCIAMENTO DE DADOS (JSON)
# ==========================================
ARQUIVO_ESTATISTICAS = "estatisticas.json"

def carregar_estatisticas():
    if os.path.exists(ARQUIVO_ESTATISTICAS):
        with open(ARQUIVO_ESTATISTICAS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"total_testes": 0, "profissoes": {}}

def salvar_resultado(profissoes_recomendadas):
    dados = carregar_estatisticas()
    dados["total_testes"] += 1
    
    for prof in profissoes_recomendadas:
        # Padroniza o nome (ex: "engenheiro de software" -> "Engenheiro De Software")
        prof = str(prof).strip().title()
        dados["profissoes"][prof] = dados["profissoes"].get(prof, 0) + 1
        
    with open(ARQUIVO_ESTATISTICAS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

# ==========================================
# CONFIGURAÇÃO DA API
# ==========================================
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.warning("Por favor, defina a variável GEMINI_API_KEY no arquivo .env")
    st.stop()

MODELO = "gemini-3.1-flash-lite"

# Salva o cliente na sessão para não perder a conexão (Evita o erro "client has been closed")
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

def inicializar_chat():
    instrucao = (
        "Você é um orientador vocacional experiente e empático. "
        "Sua missão é ajudar o usuário a descobrir sua profissão ideal. "
        "Faça uma pergunta por vez sobre os interesses, habilidades, matérias favoritas e "
        "ambientes de trabalho preferidos do usuário. Não faça todas as perguntas de uma vez. "
        "Após cerca de 4 a 5 interações (quando tiver dados suficientes), "
        "dê o seu diagnóstico sugerindo as 3 profissões que mais combinam com ele e explique o porquê."
    )
    # Usa o cliente persistido na sessão para criar o chat
    return st.session_state.client.chats.create(
        model=MODELO,
        config=types.GenerateContentConfig(system_instruction=instrucao)
    )

# ==========================================
# INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO
# ==========================================
if "chat" not in st.session_state:
    st.session_state.chat = inicializar_chat()

if "messages" not in st.session_state:
    # Mensagem de boas-vindas fixa: mais rápido e sem consumir a API na primeira tela
    mensagem_boas_vindas = "Seja bem vindo, vamos iniciar o seu teste? Diga-me, o que você gosta de fazer?"
    st.session_state.messages = [{"role": "assistant", "content": mensagem_boas_vindas}]

if "teste_finalizado" not in st.session_state:
    st.session_state.teste_finalizado = False
if "resultado_atual" not in st.session_state:
    st.session_state.resultado_atual = None

# ==========================================
# MENU LATERAL (ROTAS)
# ==========================================
st.sidebar.title("Navegação")
rota = st.sidebar.radio("Ir para:", ["📝 Teste Vocacional", "📊 Ranking de Profissões"])

# ==========================================
# ROTA 1: TESTE VOCACIONAL
# ==========================================
if rota == "📝 Teste Vocacional":
    st.title("🎓 Descubra sua Profissão Ideal")
    st.write("Responda às perguntas do nosso orientador para descobrir quais carreiras combinam com você!")

    # Exibe o histórico de mensagens
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Se o teste ainda não acabou, exibe a caixa de texto
    if not st.session_state.teste_finalizado:
        if user_input := st.chat_input("Digite sua resposta..."):
            
            # Exibe mensagem do usuário
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Exibe resposta do assistente (Em Streaming)
            with st.chat_message("assistant"):
                try:
                    response_stream = st.session_state.chat.send_message_stream(user_input)
                    
                    def gerar_texto(stream):
                        for chunk in stream:
                            if chunk.text:
                                yield chunk.text
                    
                    texto_completo = st.write_stream(gerar_texto(response_stream))
                    st.session_state.messages.append({"role": "assistant", "content": texto_completo})
                except Exception as e:
                    st.error(f"Erro: {e}")
        
        st.divider()
        
        # Botão para finalizar o teste
        if len(st.session_state.messages) > 2:
            if st.button("✅ Encerrar Teste e Ver Meu Resultado", type="primary", use_container_width=True):
                with st.spinner("Analisando seu perfil e gerando resultado..."):
                    
                    # Prompt oculto para extração em JSON
                    prompt_extracao = (
                        "Baseado em toda a nossa conversa, liste as 3 profissões que você recomendaria "
                        "para este usuário. Retorne EXATAMENTE um array JSON válido apenas com os nomes das profissões, "
                        "sem formatação markdown, sem crases e sem texto adicional. "
                        "Exemplo: [\"Engenheiro de Software\", \"Designer Gráfico\", \"Psicólogo\"]"
                    )
                    
                    try:
                        resposta_json = st.session_state.chat.send_message(prompt_extracao).text
                        
                        # Limpa possíveis crases de formatação markdown (```json ... ```)
                        resposta_limpa = re.sub(r'```(?:json)?', '', resposta_json).strip()
                        
                        profissoes = json.loads(resposta_limpa)
                        
                        if isinstance(profissoes, list):
                            salvar_resultado(profissoes)
                            st.session_state.resultado_atual = profissoes
                            st.session_state.teste_finalizado = True
                            st.rerun() # Recarrega a tela para mostrar o resultado final
                    except Exception as e:
                        st.error(f"Erro ao processar as profissões finais: {e}\nRetorno bruto: {resposta_json}")

    # Se o teste foi finalizado, bloqueia o chat e mostra o resultado
    else:
        st.success("🎉 **Teste Concluído!**")
        st.subheader("Suas Profissões Recomendadas:")
        for p in st.session_state.resultado_atual:
            st.markdown(f"- 🌟 **{p}**")
            
        st.info("Para ver como você se compara aos outros, acesse o **Ranking** no menu lateral.")
        
        # Botão para reiniciar para o próximo usuário
        if st.button("🔄 Iniciar Novo Teste (Próximo Usuário)"):
            st.session_state.chat = inicializar_chat()
            
            # Define a mesma mensagem fixa ao reiniciar
            mensagem_boas_vindas = "Seja bem vindo, vamos iniciar o seu teste? Diga-me, o que você gosta de fazer?"
            st.session_state.messages = [{"role": "assistant", "content": mensagem_boas_vindas}]
                
            st.session_state.teste_finalizado = False
            st.session_state.resultado_atual = None
            st.rerun()

# ==========================================
# ROTA 2: RANKING E ESTATÍSTICAS
# ==========================================
elif rota == "📊 Ranking de Profissões":
    st.title("📊 Estatísticas Globais")
    
    dados = carregar_estatisticas()
    total = dados.get("total_testes", 0)
    profissoes = dados.get("profissoes", {})
    
    st.metric(label="Total de Testes Realizados", value=total)
    st.divider()
    
    if total == 0:
        st.info("Nenhum teste foi finalizado ainda. Faça o primeiro teste!")
    else:
        st.subheader("🏆 Profissões Mais Recomendadas")
        
        # Ordena o dicionário de profissões (maior para menor)
        ranking = sorted(profissoes.items(), key=lambda x: x[1], reverse=True)
        
        for i, (prof, qtd) in enumerate(ranking):
            col1, col2 = st.columns([3, 1])
            with col1:
                # Calcula a barra de progresso (limita em 1.0 = 100%)
                porcentagem = min(qtd / total, 1.0)
                st.progress(porcentagem, text=f"{i+1}º Lugar: {prof}")
            with col2:
                st.write(f"**{qtd}** recomendações")