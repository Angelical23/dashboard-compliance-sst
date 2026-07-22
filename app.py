"""
GESTÃO DE SEGURANÇA DO TRABALHO - DASHBOARD DE COMPLIANCE
==========================================================
Dashboard Streamlit conectado ao Supabase para acompanhamento de
documentação obrigatória de SST por colaborador e por setor.
"""

import datetime as dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from st_supabase_connection import SupabaseConnection
except ImportError:
    SupabaseConnection = None


# ----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard de Compliance | SST",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# ESTILO GLOBAL (CSS)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {background: transparent;}

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        .main-header-bar {
            background: linear-gradient(90deg, #0B2545 0%, #13315C 100%);
            border-radius: 12px;
            padding: 14px 24px;
            color: #FFFFFF;
            font-size: 19px;
            font-weight: 700;
            margin-bottom: 16px;
            box-shadow: 0 4px 14px rgba(11, 37, 69, 0.2);
            letter-spacing: 0.3px;
        }

        .sub-header-container {
            background: #FFFFFF;
            border: 1px solid #ECECEC;
            border-radius: 12px;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 22px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        }
        .profile-block {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .profile-block img {
            width: 46px;
            height: 46px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #DCE3EE;
        }
        .profile-name {
            color: #17202A;
            font-size: 16px;
            font-weight: 700;
            margin: 0;
            line-height: 1.1;
        }
        .profile-role {
            color: #5B6470;
            font-size: 13px;
            margin: 0;
        }

        .metric-card {
            border-radius: 14px;
            padding: 18px 20px;
            background: #FFFFFF;
            border: 1px solid #ECECEC;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            height: 128px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .metric-card .m-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .metric-card .m-label {
            font-size: 13px;
            color: #5B6470;
            font-weight: 600;
        }
        .metric-card .m-icon {
            font-size: 20px;
        }
        .metric-card .m-value {
            font-size: 30px;
            font-weight: 800;
            color: #17202A;
        }
        .metric-card .m-sub {
            font-size: 12.5px;
            font-weight: 600;
        }
        .metric-card.neutral { background: #F7F9FC; border-color: #E5EAF2; }
        .metric-card.green   { background: #EAF7EF; border-color: #C9EBD7; }
        .metric-card.yellow  { background: #FEF7E3; border-color: #F7E5AE; }
        .metric-card.red     { background: #FCEBEA; border-color: #F5C6C3; }
        .metric-card.neutral .m-value { color: #13315C; }
        .metric-card.green   .m-value,  .metric-card.green   .m-sub { color: #1E7B45; }
        .metric-card.yellow  .m-value,  .metric-card.yellow  .m-sub { color: #9A6B00; }
        .metric-card.red     .m-value,  .metric-card.red     .m-sub { color: #B3261E; }

        .section-title {
            font-size: 16px;
            font-weight: 700;
            color: #17202A;
            margin: 6px 0 10px 2px;
        }

        .chart-card {
            background: #FFFFFF;
            border: 1px solid #ECECEC;
            border-radius: 14px;
            padding: 16px 18px 4px 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        
        .stButton button {
            background-color: #1E3A8A;
            color: white;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.3);
            font-weight: 600;
        }
        .stButton button:hover {
            background-color: #2563EB;
            border-color: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_connection():
    try:
        conn = st.connection("supabase", type=SupabaseConnection)
        return conn
    except Exception:
        return None


TIPOS_DOCUMENTO = ["Ficha Admissão", "ASO", "Ficha de EPI", "Certificado NR06"]
SETORES = ["Production", "Logistics", "Maintenance", "Administration"]


def mapear_status_grupo(status_bruto: str) -> str:
    if not isinstance(status_bruto, str):
        return "Regular"
    s = status_bruto.strip().lower()
    if "vencido" in s or "🛑" in s:
        return "Vencido"
    elif "vence" in s or "⚠️" in s:
        return "Vence em Breve"
    return "Regular"


@st.cache_data(show_spinner=False, ttl=10)
def carregar_dados_supabase(_conn):
    try:
        func_resp = _conn.table("colaboradores").select(
            "id, nome_completo, cpf, foto_url, local_trabalho"
        ).execute()
        
        tipos_resp = _conn.table("tipos_documento").select("id, nome_documento").execute()
        tipos_dict = {t["id"]: t["nome_documento"] for t in tipos_resp.data}

        doc_resp = _conn.table("compliance_documentos").select(
            "id, colaborador_id, tipo_documento_id, status_documento"
        ).execute()

        func_df = pd.DataFrame(func_resp.data)
        doc_df = pd.DataFrame(doc_resp.data)
        
        if func_df.empty or doc_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        doc_df["tipo_documento"] = doc_df["tipo_documento_id"].map(tipos_dict)
        
        def formatar_status_visual(val):
            if not isinstance(val, str):
                return "✔️ Em Dia"
            v = val.strip().lower()
            if "dia" in v:
                return "✔️ Em Dia"
            elif "vencido" in v:
                return "🛑 Vencido"
            else:
                return f"⚠️ {val}"

        doc_df["status_detalhado"] = doc_df["status_documento"].apply(formatar_status_visual)
        doc_df["status_grupo"] = doc_df["status_documento"].apply(mapear_status_grupo)
        
        return func_df, doc_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


conn = get_connection()
if conn is not None:
    func_df, doc_df = carregar_dados_supabase(conn)
else:
    func_df, doc_df = pd.DataFrame(), pd.DataFrame()


# ----------------------------------------------------------------------------
# MODAL: CADASTRAR NOVO REGISTRO
# ----------------------------------------------------------------------------
@st.dialog("Cadastrar Novo Colaborador e Documentos")
def modal_novo_registro(conn):
    with st.form("form_novo_colaborador"):
        nome = st.text_input("Nome Completo")
        cpf = st.text_input("CPF")
        setor = st.selectbox("Setor / Local de Trabalho", SETORES)
        
        st.markdown("---")
        st.subheader("Status dos Documentos")
        status_aso = st.selectbox("ASO", ["Em Dia", "Vencido", "Vence em Breve"])
        status_ficha_adm = st.selectbox("Ficha Admissão", ["Em Dia", "Vencido", "Vence em Breve"])
        status_epi = st.selectbox("Ficha de EPI", ["Em Dia", "Vencido", "Vence em Breve"])
        status_nr06 = st.selectbox("Certificado NR06", ["Em Dia", "Vencido", "Vence em Breve"])
        
        enviar = st.form_submit_button("Salvar no Supabase")
        
        if enviar:
            if nome and cpf:
                try:
                    foto_padrao = f"https://i.pravatar.cc/150?img={dt.datetime.now().second}"
                    conn.table("colaboradores").insert({
                        "nome_completo": nome,
                        "cpf": cpf,
                        "local_trabalho": setor,
                        "foto_url": foto_padrao
                    }).execute()
                    
                    novo_id = conn.table("colaboradores").select("id").eq("cpf", cpf).execute().data[0]["id"]
                    
                    docs_para_inserir = [
                        (1, status_ficha_adm),
                        (2, status_aso),
                        (3, status_epi),
                        (4, status_nr06)
                    ]
                    
                    for tipo_id, status_val in docs_para_inserir:
                        conn.table("compliance_documentos").insert({
                            "colaborador_id": novo_id,
                            "tipo_documento_id": tipo_id,
                            "status_documento": status_val
                        }).execute()
                        
                    st.success("Colaborador cadastrado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha o Nome e o CPF.")


# ----------------------------------------------------------------------------
# MODAL: GERENCIAR / EXCLUIR REGISTRO SELECIONADO
# ----------------------------------------------------------------------------
@st.dialog("Gerenciar Registro do Colaborador")
def modal_gerenciar_colaborador(conn, colaborador):
    st.write(f"**Colaborador:** {colaborador['nome_completo']}")
    st.write(f"**CPF:** {colaborador['cpf']} | **Setor:** {colaborador['local_trabalho']}")
    
    st.markdown("---")
    st.warning("Atenção: A exclusão removerá o colaborador e todo o seu histórico de documentos do Supabase.")
    
    if st.button("🗑️ Excluir Colaborador Permanentemente", type="primary", use_container_width=True):
        try:
            conn.table("colaboradores").delete().eq("id", colaborador["id"]).execute()
            st.success("Colaborador excluído com sucesso!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")


# ----------------------------------------------------------------------------
# CABEÇALHOS E BOTÃO DE NOVO REGISTRO
# ----------------------------------------------------------------------------
col_tit, col_btn = st.columns([8, 2])

with col_tit:
    st.markdown(
        '<div class="main-header-bar" style="margin-bottom:0;">GESTÃO DE SEGURANÇA DO TRABALHO - DASHBOARD DE COMPLIANCE</div>',
        unsafe_allow_html=True
    )

with col_btn:
    if st.button("➕ Novo Registro", use_container_width=True):
        if conn is not None:
            modal_novo_registro(conn)
        else:
            st.error("Conexão com o Supabase indisponível.")

st.write("")

col_sub1, col_sub2 = st.columns([6, 4])
with col_sub1:
    st.markdown(
        """
        <div class="sub-header-container" style="border: none; margin-bottom: 0; padding: 4px 0;">
            <div class="profile-block">
                <img src="https://i.pravatar.cc/150?img=47" />
                <div>
                    <p class="profile-name">Ana Silva</p>
                    <p class="profile-role">Gestora SST</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_sub2:
    st.markdown('<div style="display: flex; justify-content: flex-end;">', unsafe_allow_html=True)
    intervalo = st.date_input(
        "Período de análise",
        value=(dt.date(2026, 1, 1), dt.date(2026, 12, 31)),
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# 1. Métricas
total_funcionarios = func_df["id"].nunique() if not func_df.empty else 0
total_documentos = len(doc_df)

if not doc_df.empty and "colaborador_id" in doc_df.columns:
    status_por_func = (
        doc_df.groupby("colaborador_id")["status_grupo"]
        .apply(lambda s: "Regular" if all(x == "Regular" for x in s) else "Pendente")
    )
    colaboradores_em_dia = int((status_por_func == "Regular").sum())
else:
    colaboradores_em_dia = 0

pct_em_dia = round(100 * colaboradores_em_dia / total_funcionarios) if total_funcionarios else 0
qtd_vencendo = int((doc_df["status_grupo"] == "Vence em Breve").sum()) if not doc_df.empty else 0
pct_vencendo = round(100 * qtd_vencendo / total_documentos) if total_documentos else 0
qtd_vencido = int((doc_df["status_grupo"] == "Vencido").sum()) if not doc_df.empty else 0
pct_vencido = round(100 * qtd_vencido / total_documentos) if total_documentos else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="metric-card neutral">
            <div class="m-header">
                <span class="m-label">Total de Funcionários</span>
                <span class="m-icon">👥</span>
            </div>
            <div class="m-value">{total_funcionarios}</div>
            <div class="m-sub">&nbsp;</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card green">
            <div class="m-header">
                <span class="m-label">Colaboradores em Dia</span>
                <span class="m-icon">✅</span>
            </div>
            <div class="m-value">{colaboradores_em_dia} <span style="font-size: 18px;">({pct_em_dia}%)</span></div>
            <div class="m-sub">&nbsp;</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card yellow">
            <div class="m-header">
                <span class="m-label">Documentos Vencendo (30 dias)</span>
                <span class="m-icon">⚠️</span>
            </div>
            <div class="m-value">{qtd_vencendo} <span style="font-size: 18px;">({pct_vencendo}%)</span></div>
            <div class="m-sub">&nbsp;</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card red">
            <div class="m-header">
                <span class="m-label">Documentos Vencidos</span>
                <span class="m-icon">🛑</span>
            </div>
            <div class="m-value">{qtd_vencido} <span style="font-size: 18px;">({pct_vencido}%)</span></div>
            <div class="m-sub">&nbsp;</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# 2. Gráficos
graf_esq, graf_dir = st.columns([6, 4])
CORES = {"Regular": "#2E6FE0", "Vence em Breve": "#F4C430", "Vencido": "#E5484D"}

with graf_esq:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Status de Documentação por Setor</div>', unsafe_allow_html=True)

    if not doc_df.empty and not func_df.empty:
        doc_setor = doc_df.merge(func_df[["id", "local_trabalho"]], left_on="colaborador_id", right_on="id", how="left")
        contagem = (
            doc_setor.groupby(["local_trabalho", "status_grupo"])
            .size()
            .reset_index(name="quantidade")
        )
        todas_combos = pd.MultiIndex.from_product(
            [SETORES, ["Regular", "Vence em Breve", "Vencido"]], names=["local_trabalho", "status_grupo"]
        ).to_frame(index=False)
        contagem = todas_combos.merge(contagem, on=["local_trabalho", "status_grupo"], how="left").fillna(0)
        contagem["quantidade"] = contagem["quantidade"].astype(int)
    else:
        contagem = pd.DataFrame(columns=["local_trabalho", "status_grupo", "quantidade"])

    fig_bar = px.bar(
        contagem,
        x="local_trabalho",
        y="quantidade",
        color="status_grupo",
        barmode="group",
        color_discrete_map=CORES,
        category_orders={"local_trabalho": SETORES, "status_grupo": ["Regular", "Vence em Breve", "Vencido"]},
        labels={"local_trabalho": "Setor", "quantidade": "Qtd. de Documentos", "status_grupo": "Status"},
    )
    fig_bar.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig_bar.update_yaxes(gridcolor="#EEF0F3")
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with graf_dir:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Distribuição de Documentos Pendentes</div>', unsafe_allow_html=True)

    if not doc_df.empty:
        pendentes = doc_df[doc_df["status_grupo"] != "Regular"]
        pendentes_por_tipo = pendentes.groupby("tipo_documento").size().reset_index(name="quantidade")
        pendentes_por_tipo = pendentes_por_tipo.set_index("tipo_documento").reindex(TIPOS_DOCUMENTO, fill_value=0).reset_index()
    else:
        pendentes_por_tipo = pd.DataFrame({"tipo_documento": TIPOS_DOCUMENTO, "quantidade": [0]*4})

    fig_donut = go.Figure(
        data=[
            go.Pie(
                labels=pendentes_por_tipo["tipo_documento"],
                values=pendentes_por_tipo["quantidade"],
                hole=0.55,
                marker=dict(colors=["#2E6FE0", "#F4C430", "#E5484D", "#8E6FF4"]),
                textinfo="percent",
            )
        ]
    )
    fig_donut.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_donut, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# 3. Tabela Interativa de Visão Geral com Seleção de Gerenciamento
st.markdown('<div class="section-title">VISÃO GERAL DE DOCUMENTAÇÃO POR COLABORADOR</div>', unsafe_allow_html=True)

if not doc_df.empty and not func_df.empty:
    pivot_status = doc_df.pivot_table(
        index="colaborador_id",
        columns="tipo_documento",
        values="status_detalhado",
        aggfunc="first",
    ).reindex(columns=TIPOS_DOCUMENTO)

    tabela = func_df.merge(pivot_status, left_on="id", right_index=True, how="left").sort_values("nome_completo")
    
    tabela_exibicao = tabela[["id", "nome_completo", "cpf", "local_trabalho"] + TIPOS_DOCUMENTO].copy()
    tabela_exibicao.columns = ["ID", "Nome Completo", "CPF", "Local de Trabalho", "Ficha Admissão", "ASO", "Ficha de EPI", "Certificado NR06"]

    # Seleção interativa na tabela do Streamlit
    coluna_selecao = st.selectbox(
        "Selecione um colaborador para gerenciar/excluir:",
        options=tabela_exibicao["ID"].tolist(),
        format_func=lambda x: tabela_exibicao.loc[tabela_exibicao["ID"] == x, "Nome Completo"].values[0]
    )

    if coluna_selecao:
        colaborador_selecionado = func_df[func_df["id"] == coluna_selecao].iloc[0]
        if st.button("⚙️ Gerenciar / Excluir Colaborador Selecionado"):
            modal_gerenciar_colaborador(conn, colaborador_selecionado)

    st.dataframe(
        tabela_exibicao.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
        height=380,
    )
else:
    st.warning("⚠️ Nenhum registro encontrado.")

st.caption(
    f"Exibindo dados reais do Supabase · Última atualização: "
    f"{dt.datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
