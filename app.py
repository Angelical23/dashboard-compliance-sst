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
            padding: 16px 24px;
            color: #FFFFFF;
            font-size: 20px;
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

        table.custom-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
            font-family: "Source Sans Pro", sans-serif;
        }
        table.custom-table thead th {
            background: #13315C;
            color: #FFFFFF;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        table.custom-table tbody tr {
            border-bottom: 1px solid #EEF0F3;
        }
        table.custom-table tbody tr:hover {
            background: #F6F9FC;
        }
        table.custom-table td {
            padding: 8px 8px;
            vertical-align: middle;
            color: #2A2E34;
        }
        .emp-cell {
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }
        .emp-cell img {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            object-fit: cover;
        }
        .doc-pill {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 9px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
        }
        .doc-em-dia   { background: #DFF5E6; color: #1E7B45; }
        .doc-vencendo { background: #FCF0CE; color: #9A6B00; }
        .doc-vencido  { background: #FBE0DE; color: #B3261E; }
        .actions-cell { white-space: nowrap; font-size: 15px; }
        .actions-cell span { margin-right: 10px; cursor: pointer; opacity: 0.85; }
        .actions-cell span:hover { opacity: 1; }
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


def classificar_status(data_validade: dt.date, hoje: dt.date) -> str:
    if pd.isna(data_validade):
        return "Vencido"
    dias = (data_validade - hoje).days
    if dias < 0:
        return "Vencido"
    if dias <= 30:
        return f"Vence em {dias} dias" if dias > 0 else "Vence em 0 dias"
    return "Em Dia"


def status_grupo(status: str) -> str:
    if status == "Em Dia":
        return "Regular"
    if status == "Vencido":
        return "Vencido"
    return "Vence em Breve"


@st.cache_data(show_spinner=False, ttl=300)
def gerar_dados_mock():
    import random

    random.seed(42)
    hoje = dt.date.today()

    nomes = [
        "Carlos Oliveira", "Fernanda Costa", "Pedro Santos", "Lucas Almeida",
        "Lucas Almeida", "Jobs Almeida", "Carlia Olvera", "Lucas Almeida",
        "Mariana Costa", "Ricardo Nunes", "Juliana Ferreira", "André Martins",
        "Patrícia Gomes", "Bruno Castro", "Camila Rodrigues", "Felipe Teixeira",
        "Larissa Vieira", "Rafael Cardoso", "Beatriz Nogueira", "Diego Cavalcante"
    ]

    funcionarios = []
    for i, nome in enumerate(nomes, start=1):
        funcionarios.append(
            {
                "id": i,
                "nome_completo": f"{nome} {i if nomes.count(nome) > 1 else ''}".strip(),
                "cpf": f"{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(10,99)}",
                "foto_url": f"https://i.pravatar.cc/150?img={i+10}",
                "local_trabalho": random.choice(SETORES),
            }
        )
    func_df = pd.DataFrame(funcionarios)

    documentos = []
    doc_id = 1
    pesos = [0.83, 0.10, 0.07]
    tipo_map = {tipo: idx for idx, tipo in enumerate(TIPOS_DOCUMENTO, start=1)}

    for f in funcionarios:
        for tipo in TIPOS_DOCUMENTO:
            r = random.random()
            if r < pesos[0]:
                validade = hoje + dt.timedelta(days=random.randint(60, 400))
            elif r < pesos[0] + pesos[1]:
                validade = hoje + dt.timedelta(days=random.randint(1, 30))
            else:
                validade = hoje - dt.timedelta(days=random.randint(1, 120))

            documentos.append(
                {
                    "id": doc_id,
                    "colaborador_id": f["id"],
                    "tipo_documento_id": tipo_map[tipo],
                    "tipo_documento": tipo,
                    "data_vencimento": validade,
                }
            )
            doc_id += 1

    doc_df = pd.DataFrame(documentos)
    return func_df, doc_df


@st.cache_data(show_spinner=False, ttl=300)
def carregar_dados_supabase(_conn):
    try:
        func_resp = _conn.table("colaboradores").select(
            "id, nome_completo, cpf, foto_url, local_trabalho"
        ).execute()
        
        tipos_resp = _conn.table("tipos_documento").select("id, nome_documento").execute()
        tipos_dict = {t["id"]: t["nome_documento"] for t in tipos_resp.data}

        doc_resp = _conn.table("compliance_documentos").select(
            "id, colaborador_id, tipo_documento_id, data_vencimento"
        ).execute()

        func_df = pd.DataFrame(func_resp.data)
        doc_df = pd.DataFrame(doc_resp.data)
        
        # Se vier vazio do Supabase, retorna vazio para acionar o mock de segurança
        if func_df.empty or doc_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        doc_df["tipo_documento"] = doc_df["tipo_documento_id"].map(tipos_dict)
        doc_df["data_vencimento"] = pd.to_datetime(doc_df["data_vencimento"]).dt.date
        return func_df, doc_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


def carregar_base():
    conn = get_connection()
    if conn is not None:
        func_df, doc_df = carregar_dados_supabase(conn)
        if not func_df.empty and not doc_df.empty:
            return (func_df, doc_df), True
    
    # Fallback automático para dados simulados se o banco estiver vazio ou falhar
    return gerar_dados_mock(), False


(func_df, doc_df), usando_supabase = carregar_base()

hoje = dt.date.today()
if not doc_df.empty and "data_vencimento" in doc_df.columns:
    doc_df["status_detalhado"] = doc_df["data_vencimento"].apply(lambda d: classificar_status(d, hoje))
    doc_df["status_grupo"] = doc_df["status_detalhado"].apply(status_grupo)
else:
    doc_df["status_detalhado"] = "Em Dia"
    doc_df["status_grupo"] = "Regular"


# Cabeçalhos
st.markdown(
    '<div class="main-header-bar">GESTÃO DE SEGURANÇA DO TRABALHO - DASHBOARD DE COMPLIANCE</div>',
    unsafe_allow_html=True
)

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

if not usando_supabase:
    st.caption("⚠️ Modo demonstração: exibindo dados simulados (tabelas do Supabase vazias ou não configuradas).")

st.write("")

# 1. Métricas
total_funcionarios = func_df["id"].nunique() if not func_df.empty else 0
total_documentos = len(doc_df)

if not doc_df.empty and "colaborador_id" in doc_df.columns:
    status_por_func = (
        doc_df.groupby("colaborador_id")["status_detalhado"]
        .apply(lambda s: "Em Dia" if (s == "Em Dia").all() else "Pendente")
    )
    colaboradores_em_dia = int((status_por_func == "Em Dia").sum())
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

# 3. Tabela Principal
st.markdown('<div class="section-title">VISÃO GERAL DE DOCUMENTAÇÃO POR COLABORADOR</div>', unsafe_allow_html=True)

if not doc_df.empty and not func_df.empty:
    pivot_status = doc_df.pivot_table(
        index="colaborador_id",
        columns="tipo_documento",
        values="status_detalhado",
        aggfunc="first",
    ).reindex(columns=TIPOS_DOCUMENTO)

    tabela = func_df.merge(pivot_status, left_on="id", right_index=True, how="left").sort_values("nome_completo")
else:
    tabela = pd.DataFrame(columns=["id", "nome_completo", "cpf", "local_trabalho", "foto_url"])


def render_pill(status: str) -> str:
    if pd.isna(status):
        return '<span class="doc-pill doc-vencido">🛑 N/D</span>'
    if status == "Em Dia":
        return '<span class="doc-pill doc-em-dia">✔️ Em Dia</span>'
    if status == "Vencido":
        return '<span class="doc-pill doc-vencido">🛑 Vencido</span>'
    return f'<span class="doc-pill doc-vencendo">⚠️ {status}</span>'


linhas_html = []
for _, row in tabela.iterrows():
    linhas_html.append(
        f"""
        <tr>
            <td>
                <div class="emp-cell">
                    <img src="{row.get('foto_url', 'https://i.pravatar.cc/150')}" />
                    <span>{row.get('nome_completo', '')}</span>
                </div>
            </td>
            <td>{row.get('cpf', '')}</td>
            <td>{row.get('local_trabalho', '')}</td>
            <td>{render_pill(row.get('Ficha Admissão'))}</td>
            <td>{render_pill(row.get('ASO'))}</td>
            <td>{render_pill(row.get('Ficha de EPI'))}</td>
            <td>{render_pill(row.get('Certificado NR06'))}</td>
            <td class="actions-cell">
                <span title="Visualizar">👁️</span>
                <span title="Editar">✏️</span>
                <span title="Notificar">🔔</span>
            </td>
        </tr>
        """
    )

tabela_html = f"""
<div style="max-height: 560px; overflow-y: auto; border: 1px solid #ECECEC; border-radius: 14px;">
<table class="custom-table">
    <thead>
        <tr>
            <th>Nome Completo</th>
            <th>CPF</th>
            <th>Local de Trabalho</th>
            <th>Ficha de Admissão</th>
            <th>ASO</th>
            <th>Ficha de EPI</th>
            <th>Certificado NR06</th>
            <th>Ações</th>
        </tr>
    </thead>
    <tbody>
        {''.join(linhas_html)}
    </tbody>
</table>
</div>
"""

st.markdown(tabela_html, unsafe_allow_html=True)

st.caption(
    f"Exibindo {len(tabela)} colaboradores · Última atualização: "
    f"{dt.datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
