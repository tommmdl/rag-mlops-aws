"""
streamlit/app.py — Interface visual do RAG MLOps para portfólio
Execute: streamlit run streamlit/app.py
"""
import os
import uuid
import requests
import streamlit as st

# ─── CONFIG ───────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="RAG MLOps Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.environ.get("RAG_API_URL", "http://localhost:8000")

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Configurações")

    api_url = st.text_input("API URL", value=API_URL)

    st.divider()
    st.markdown("**Stack**")
    st.markdown("""
    - 🟠 AWS Lambda (Python 3.12)
    - 🔵 Amazon Bedrock (Titan + Claude 3 Haiku)
    - 🟢 OpenSearch Service (t3.small)
    - 🟡 DynamoDB (histórico)
    - 🔴 Terraform (IaC completo)
    """)

    st.divider()
    st.markdown("**Base de conhecimento**")
    st.markdown("Documentos técnicos MLOps: papers, docs AWS, runbooks")

    st.divider()
    if st.button("🏥 Health Check"):
        try:
            resp = requests.get(f"{api_url}/health", timeout=5)
            if resp.ok:
                st.success("✅ API online!")
            else:
                st.error(f"❌ Status: {resp.status_code}")
        except Exception as e:
            st.error(f"❌ Offline: {e}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

st.title("🤖 RAG MLOps Assistant")
st.markdown(
    "Sistema de perguntas e respostas sobre MLOps, "
    "construído com **Amazon Bedrock**, **OpenSearch** e **Lambda**."
)

# Session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe histórico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption(f"📚 Fontes: {', '.join(msg['sources'])}")
        if msg.get("contexts"):
            with st.expander("🔍 Chunks recuperados"):
                for i, ctx in enumerate(msg["contexts"], 1):
                    st.markdown(f"**Chunk {i}** (score: `{ctx['score']:.3f}`)")
                    st.text(ctx["text"])

# Input do usuário
if prompt := st.chat_input("Pergunte sobre MLOps, CI/CD, Feature Store, Observabilidade..."):

    # Adiciona mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Chama a API RAG
    with st.chat_message("assistant"):
        with st.spinner("🔍 Buscando contexto + gerando resposta..."):
            try:
                resp = requests.post(
                    f"{api_url}/query",
                    json={"question": prompt, "session_id": st.session_state.session_id},
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()

                answer   = data.get("answer", "Sem resposta")
                sources  = data.get("sources", [])
                contexts = data.get("contexts", [])

                st.markdown(answer)
                if sources:
                    st.caption(f"📚 Fontes: {', '.join(sources)}")
                if contexts:
                    with st.expander("🔍 Chunks recuperados"):
                        for i, ctx in enumerate(contexts, 1):
                            st.markdown(f"**Chunk {i}** (score: `{ctx['score']:.3f}`)")
                            st.text(ctx["text"])

                st.session_state.messages.append({
                    "role":     "assistant",
                    "content":  answer,
                    "sources":  sources,
                    "contexts": contexts,
                })

            except requests.exceptions.ConnectionError:
                st.error("❌ API offline. Execute `make up` para provisionar a infra.")
            except Exception as e:
                st.error(f"❌ Erro: {e}")

# Botão para limpar chat
if st.session_state.messages:
    if st.button("🗑️ Limpar conversa"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
