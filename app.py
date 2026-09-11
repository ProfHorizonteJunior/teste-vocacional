import os
import json
import re
import time # <--- IMPORTANTE: Importamos a biblioteca de tempo
import streamlit as st
from dotenv import load_dotenv
from google import genai

# Carrega as variáveis de ambiente
load_dotenv()

st.set_page_config(page_title="Teste Vocacional", page_icon="🎓", layout="wide")

# ==========================================
# LISTA DE PERGUNTAS DO TESTE
# ==========================================
PERGUNTAS = [
    "Você prefere criar ou organizar?",
    "Gosta de resolver problemas?",
    "Prefere trabalhar com pessoas ou computadores?",
    "Você gosta de liderar?",
    "Trabalha melhor sozinho ou em equipe?",
    "Você gosta de números?",
    "Gosta de tecnologia?",
    "Você se considera criativo?",
    "O que faria se tivesse um dia livre?"
]

# ==========================================
# GERENCIAMENTO DE DADOS (JSON)
# ==========================================
ARQUIVO_ESTATISTICAS = "estatisticas.json"

def carregar_estatisticas():
    if os.path.exists(ARQUIVO_ESTATISTICAS):
        try:
            with open(ARQUIVO_ESTATISTICAS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Proteção: Se houver colisão de leitura/escrita simultânea, retorna vazio temporariamente
            pass
    return {"total_testes": 0, "profissoes": {}}

def salvar_resultado(profissoes_recomendadas):
    dados = carregar_estatisticas()
    
    # Se retornou vazio pela proteção acima, mas o arquivo existe, tenta de novo
    if dados["total_testes"] == 0 and os.path.exists(ARQUIVO_ESTATISTICAS):
        time.sleep(0.1)
        dados = carregar_estatisticas()

    dados["total_testes"] += 1
    
    for prof in profissoes_recomendadas:
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

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

# ==========================================
# INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO
# ==========================================
if "pergunta_atual" not in st.session_state:
    st.session_state.pergunta_atual = 0

if "historico_qa" not in st.session_state:
    st.session_state.historico_qa = [] 

if "messages" not in st.session_state:
    msg_boas_vindas = f"Seja bem vindo, vamos iniciar o seu teste? \n\n**1.** {PERGUNTAS[0]}"
    st.session_state.messages = [{"role": "assistant", "content": msg_boas_vindas}]

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
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not st.session_state.teste_finalizado:
        if user_input := st.chat_input("Digite sua resposta..."):
            
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
                
            st.session_state.historico_qa.append({
                "pergunta": PERGUNTAS[st.session_state.pergunta_atual],
                "resposta": user_input
            })
            
            st.session_state.pergunta_atual += 1
            
            if st.session_state.pergunta_atual < len(PERGUNTAS):
                prox_pergunta = PERGUNTAS[st.session_state.pergunta_atual]
                txt_prox = f"**{st.session_state.pergunta_atual + 1}.** {prox_pergunta}"
                
                st.session_state.messages.append({"role": "assistant", "content": txt_prox})
                with st.chat_message("assistant"):
                    st.markdown(txt_prox)
                st.rerun()
                
            else:
                st.session_state.teste_finalizado = True
                st.rerun()

    if st.session_state.teste_finalizado and st.session_state.resultado_atual is None:
        with st.chat_message("assistant"):
            with st.spinner("Analisando suas respostas para diagnosticar o seu perfil..."):
                
                texto_entrevista = ""
                for qa in st.session_state.historico_qa:
                    texto_entrevista += f"Pergunta: {qa['pergunta']}\nResposta do Aluno: {qa['resposta']}\n\n"
                
                prompt_diagnostico = f"""Você é um orientador vocacional especialista em diagnosticar perfis profissionais.
O estudante respondeu ao seguinte questionário:

{texto_entrevista}

Com base nestas respostas, trace o perfil predominante, liste 5 competências principais do aluno e recomende um rank de 5 profissões indicadas.

Obrigatório: Retorne EXATAMENTE um objeto JSON válido, sem formatação markdown (sem ```json), com a seguinte estrutura estrita:
{{
    "perfil": "Nome do Perfil 1 + Nome do Perfil 2",
    "competencias": ["Competência 1", "Competência 2", "Competência 3", "Competência 4", "Competência 5"],
    "profissoes": ["Profissão 1", "Profissão 2", "Profissão 3", "Profissão 4", "Profissão 5"]
}}
"""
                try:
                    response = st.session_state.client.models.generate_content(
                        model=MODELO,
                        contents=prompt_diagnostico
                    )
                    
                    resposta_limpa = re.sub(r'```(?:json)?', '', response.text).strip()
                    resultado_json = json.loads(resposta_limpa)
                    
                    if "profissoes" in resultado_json:
                        salvar_resultado(resultado_json["profissoes"])
                        
                    st.session_state.resultado_atual = resultado_json
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar o diagnóstico: {e}")

    if st.session_state.teste_finalizado and st.session_state.resultado_atual:
        resultado = st.session_state.resultado_atual
        
        st.success("🎉 **Diagnóstico Concluído!**")
        
        st.markdown("### Seu Perfil")
        st.markdown(f"**Perfil predominante:**\n<br>{resultado.get('perfil', 'Não definido')}", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("### Suas principais competências")
        for comp in resultado.get('competencias', []):
            st.markdown(f"• {comp}")
        st.markdown("---")
        
        st.markdown("### Profissões indicadas")
        icones = ["🥇", "🥈", "🥉", "4º", "5º"]
        profissoes = resultado.get('profissoes', [])
        
        for i, prof in enumerate(profissoes[:5]):
            icone = icones[i] if i < len(icones) else "•"
            st.markdown(f"**{icone} {prof}**")
            
        st.info("Para ver como você se compara aos outros, acesse o **Ranking** no menu lateral.")
        
        st.divider()
        if st.button("🔄 Iniciar Novo Teste (Próximo Usuário)", type="primary"):
            st.session_state.pergunta_atual = 0
            st.session_state.historico_qa = []
            st.session_state.resultado_atual = None
            st.session_state.teste_finalizado = False
            msg_boas_vindas = f"Seja bem vindo, vamos iniciar o seu teste? \n\n**1.** {PERGUNTAS[0]}"
            st.session_state.messages = [{"role": "assistant", "content": msg_boas_vindas}]
            st.rerun()

# ==========================================
# ROTA 2: RANKING E ESTATÍSTICAS
# ==========================================
elif rota == "📊 Ranking de Profissões":
    
    # 1. Criação de um layout superior com o título e a chave (Toggle) do Datashow
    col_titulo, col_toggle = st.columns([3, 1])
    with col_titulo:
        st.title("📊 Estatísticas Globais")
    with col_toggle:
        st.write("") # Espaçamento
        # Toggle para ativar/desativar o recarregamento automático
        modo_datashow = st.toggle("📺 Modo Datashow (Tempo Real)", value=True)
    
    dados = carregar_estatisticas()
    total = dados.get("total_testes", 0)
    profissoes = dados.get("profissoes", {})
    
    st.metric(label="Total de Testes Realizados", value=total)
    st.divider()
    
    if total == 0:
        st.info("Nenhum teste foi finalizado ainda. Faça o primeiro teste!")
    else:
        st.subheader("🏆 Profissões Mais Recomendadas")
        
        ranking = sorted(profissoes.items(), key=lambda x: x[1], reverse=True)
        
        for i, (prof, qtd) in enumerate(ranking):
            col1, col2 = st.columns([3, 1])
            with col1:
                porcentagem = min(qtd / total, 1.0)
                st.progress(porcentagem, text=f"{i+1}º Lugar: {prof}")
            with col2:
                st.write(f"**{qtd}** recomendações")

    # 2. Lógica de Atualização Automática
    if modo_datashow:
        # Pausa de 3 segundos antes de atualizar (ótimo tempo para ler e não sobrecarregar)
        time.sleep(3)
        # Força o Streamlit a recarregar apenas essa aba
        st.rerun()