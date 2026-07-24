"""
GESTÃO DE SEGURANÇA DO TRABALHO - DASHBOARD DE COMPLIANCE
==========================================================
Dashboard corporativo com upload e captura correta de URLs do Supabase Storage.
"""

import datetime as dt
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

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
# ESTILO GLOBAL (MODERN DESIGN CORPORATIVO SST)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {background: transparent;}

        .stApp {
            background-color: #F4F6F9;
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2.5rem;
            max-width: 1400px;
        }

        .main-header-bar {
            background: linear-gradient(135deg, #0A2540 0%, #1E3A8A 100%);
            border-radius: 14px;
            padding: 18px 26px;
            color: #FFFFFF;
            font-size: 21px;
            font-weight: 700;
            margin-bottom: 22px;
            box-shadow: 0 4px 16px rgba(10, 37, 64, 0.15);
            letter-spacing: 0.4px;
        }

        .sub-header-container {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 14px 22px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        }
        .profile-name {
            color: #0F172A;
            font-size: 16px;
            font-weight: 700;
            margin: 0;
            line-height: 1.2;
        }
        .profile-role {
            color: #64748B;
            font-size: 13px;
            margin: 0;
        }

        .metric-card {
            border-radius: 14px;
            padding: 20px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
            height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.06);
        }
        .metric-card .m-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .metric-card .m-label {
            font-size: 13px;
            color: #64748B;
            font-weight: 600;
        }
        .metric-card .m-icon {
            font-size: 20px;
        }
        .metric-card .m-value {
            font-size: 30px;
            font-weight: 800;
            color: #0F172A;
        }
        .metric-card .m-sub {
            font-size: 12.5px;
            font-weight: 600;
        }
        
        .metric-card.neutral { border-left: 4px solid #3B82F6; }
        .metric-card.green   { border-left: 4px solid #10B981; background: #F0FDF4; }
        .metric-card.yellow  { border-left: 4px solid #F59E0B; background: #FFFBEB; }
        .metric-card.red     { border-left: 4px solid #EF4444; background: #FEF2F2; }

        .metric-card.neutral .m-value { color: #1E40AF; }
        .metric-card.green   .m-value, .metric-card.green   .m-sub { color: #047857; }
        .metric-card.yellow  .m-value, .metric-card.yellow  .m-sub { color: #B45309; }
        .metric-card.red     .m-value, .metric-card.red     .m-sub { color: #B91C1C; }

        .section-title {
            font-size: 16px;
            font-weight: 700;
            color: #0F172A;
            margin: 8px 0 12px 2px;
        }

        .chart-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 18px 20px 6px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
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


@st.cache_resource(show_spinner=False)
def get_supabase_client():
    try:
        url = st.secrets["connections"]["supabase"]["supabase_url"]
        key = st.secrets["connections"]["supabase"]["supabase_key"]
        return create_client(url, key)
    except Exception:
        return None


TIPOS_DOCUMENTO = ["Ficha Admissão", "ASO", "Ficha de EPI", "Certificado NR06"]
SETORES = ["TJ", "CEAGESP"]


def calcular_status_por_data(data_val):
    if not data_val or pd.isna(data_val):
        return "Regular", "✔️ Sem Data"
    else:
        try:
            if isinstance(data_val, str):
                dt_val = dt.datetime.strptime(data_val.strip()[:10], "%Y-%m-%d").date()
            elif isinstance(data_val, dt.datetime):
                dt_val = data_val.date()
            elif isinstance(data_val, dt.date):
                dt_val = data_val
        except Exception:
            dt_val = dt.date.today()

        hoje = dt.date.today()
        dias_restantes = (dt_val - hoje).days
        data_formatada = dt_val.strftime('%d/%m/%Y')

        if dias_restantes < 0:
            return "Vencido", f"🛑 Vencido ({data_formatada})"
        elif 0 <= dias_restantes <= 30:
            return "Vence em Breve", f"⚠️ Vence em {data_formatada}"
        else:
            return "Regular", f"✔️ {data_formatada}"


@st.cache_data(show_spinner=False, ttl=10)
def carregar_dados_supabase(_conn):
    try:
        func_resp = _conn.table("colaboradores").select(
            "id, nome_completo, cpf, foto_url, local_trabalho"
        ).execute()
        
        tipos_resp = _conn.table("tipos_documento").select("id, nome_documento").execute()
        tipos_dict = {t["id"]: t["nome_documento"] for t in tipos_resp.data}

        doc_resp = _conn.table("compliance_documentos").select(
            "id, colaborador_id, tipo_documento_id, data_validade, arquivo_url"
        ).execute()

        func_df = pd.DataFrame(func_resp.data)
        doc_df = pd.DataFrame(doc_resp.data)
        
        if func_df.empty or doc_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        doc_df["tipo_documento"] = doc_df["tipo_documento_id"].map(tipos_dict)
        
        status_grup = []
        status_det = []
        
        for _, r in doc_df.iterrows():
            g, s = calcular_status_por_data(r["data_validade"])
            status_grup.append(g)
            status_det.append(s)
            
        doc_df["status_grupo"] = status_grup
        doc_df["status_detalhado"] = status_det
        
        return func_df, doc_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


conn = get_connection()
supabase_client = get_supabase_client()
if conn is not None:
    func_df, doc_df = carregar_dados_supabase(conn)
else:
    func_df, doc_df = pd.DataFrame(), pd.DataFrame()


def fazer_upload_storage(arq, colaborador_id, tipo_id):
    if arq is not None and supabase_client is not None:
        try:
            # Limpa caracteres especiais do nome do arquivo para evitar conflitos na nuvem
            nome_limpo = "".join(c for c in arq.name if c.isalnum() or c in ('.', '_', '-'))
            file_name = f"colab_{colaborador_id}_tipo_{tipo_id}_{nome_limpo}"
            file_bytes = arq.getvalue()
            
            # Faz o upload (substitui se já existir)
            supabase_client.storage.from_("documentos_sst").upload(
                file_name,
                file_bytes,
                file_options={"upsert": "true", "content-type": arq.type}
            )
            
            # Extração correta da URL pública do objeto retornado pelo Supabase Python
            res = supabase_client.storage.from_("documentos_sst").get_public_url(file_name)
            
            if isinstance(res, dict):
                public_url = res.get("publicUrl") or res.get("public_url")
            else:
                public_url = str(res)
                
            return public_url
        except Exception as e:
            st.error(f"Erro no upload do arquivo: {e}")
            return None
    return None


# ----------------------------------------------------------------------------
# MODAL 1: VISUALIZAR DETALHES E LINKS
# ----------------------------------------------------------------------------
@st.dialog("👁️ Detalhes e Prontuário do Colaborador")
def modal_visualizar(conn, colaborador, docs_colab):
    col_img, col_info = st.columns([1, 3])
    with col_img:
        foto = colaborador.get("foto_url")
        if foto:
            st.image(foto, width=100)
        else:
            st.image("https://i.pravatar.cc/150?img=32", width=100)
    with col_info:
        st.markdown(f"### {colaborador['nome_completo']}")
        st.write(f"**CPF:** {colaborador['cpf']}")
        st.write(f"**Setor / Local:** {colaborador['local_trabalho']}")
    
    st.markdown("---")
    st.subheader("Documentos e Anexos")
    
    for _, doc in docs_colab.iterrows():
        url_arq = doc.get("arquivo_url")
        if url_arq and pd.notna(url_arq) and str(url_arq).strip() != "":
            link_html = f" - <a href='{url_arq}' target='_blank'>📎 <b>[Ver Documento]</b></a>"
        else:
            link_html = " - <span style='color: #94A3B8;'>Sem anexo</span>"
            
        st.markdown(f"• **{doc['tipo_documento']}**: {doc['status_detalhado']}{link_html}", unsafe_allow_html=True)
    
    st.write("")
    if st.button("Fechar Prontuário", use_container_width=True):
        st.rerun()


# ----------------------------------------------------------------------------
# MODAL 2: EDITAR PRAZOS E ANEXOS
# ----------------------------------------------------------------------------
@st.dialog("✏️ Atualizar Prazos e Anexos")
def modal_editar_prazos(conn, colaborador, docs_colab):
    st.write(f"Editando documentos de: **{colaborador['nome_completo']}**")
    st.markdown("---")
    
    with st.form(f"form_editar_{colaborador['id']}"):
        novas_datas = {}
        novos_arquivos_upload = {}
        
        for _, doc in docs_colab.iterrows():
            val_atual = dt.date.today()
            try:
                if pd.notna(doc["data_validade"]):
                    val_atual = dt.datetime.strptime(str(doc["data_validade"])[:10], "%Y-%m-%d").date()
            except Exception:
                pass
                
            st.markdown(f"**{doc['tipo_documento']}**")
            novas_datas[doc["tipo_documento_id"]] = st.date_input(
                f"Validade ({doc['tipo_documento']})",
                value=val_atual,
                key=f"date_edit_{colaborador['id']}_{doc['tipo_documento_id']}",
                label_visibility="collapsed"
            )
            novos_arquivos_upload[doc["tipo_documento_id"]] = st.file_uploader(
                f"Anexar novo arquivo ({doc['tipo_documento']})",
                type=["pdf", "png", "jpg", "jpeg"],
                key=f"file_edit_{colaborador['id']}_{doc['tipo_documento_id']}"
            )
            st.markdown("---")
            
        salvar_edicao = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
        
        if salvar_edicao:
            try:
                for tipo_id, nova_data in novas_datas.items():
                    dados_update = {"data_validade": str(nova_data)}
                    
                    arq = novos_arquivos_upload.get(tipo_id)
                    if arq is not None:
                        url_arquivo = fazer_upload_storage(arq, colaborador["id"], tipo_id)
                        if url_arquivo:
                            dados_update["arquivo_url"] = url_arquivo

                    conn.table("compliance_documentos").update(dados_update).eq("colaborador_id", colaborador["id"]).eq("tipo_documento_id", tipo_id).execute()
                    
                st.success("✨ Prazos e anexos atualizados com sucesso!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")


# ----------------------------------------------------------------------------
# MODAL 3: GERENCIAR / EXCLUIR
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
# NAVEGAÇÃO POR ABAS
# ----------------------------------------------------------------------------
aba_principal, aba_cadastro = st.tabs(["📊 Dashboard de Compliance", "➕ Cadastrar Novo Colaborador"])


# ============================================================================
# ABA 1: DASHBOARD COMPLETO
# ============================================================================
with aba_principal:
    st.markdown(
        '<div class="main-header-bar">GESTÃO DE SEGURANÇA DO TRABALHO - DASHBOARD DE COMPLIANCE</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="sub-header-container">', unsafe_allow_html=True)
    col_img, col_txt, col_date = st.columns([1, 8, 4])
    
    with col_img:
        if Path("angelica.png").is_file():
            st.image("angelica.png", width=46)
        else:
            st.image("https://i.pravatar.cc/150?img=32", width=46)
            
    with col_txt:
        st.markdown(
            """
            <div style="padding-top: 2px;">
                <p class="profile-name">Angelica Alves</p>
                <p class="profile-role">Gestora SST</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
    with col_date:
        intervalo = st.date_input(
            "Período de análise",
            value=(dt.date(2026, 1, 1), dt.date(2026, 12, 31)),
            label_visibility="collapsed",
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

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

    graf_esq, graf_dir = st.columns([6, 4])
    CORES = {"Regular": "#2563EB", "Vence em Breve": "#F59E0B", "Vencido": "#EF4444"}

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
        fig_bar.update_yaxes(gridcolor="#E2E8F0")
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
                    marker=dict(colors=["#2563EB", "#F59E0B", "#EF4444", "#8B5CF6"]),
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

    st.markdown('<div class="section-title">VISÃO GERAL DE DOCUMENTAÇÃO POR COLABORADOR (PRAZOS E ANEXOS)</div>', unsafe_allow_html=True)

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

        col_sel, col_btn1, col_btn2, col_del_btn = st.columns([5, 2, 2, 2])
        
        with col_sel:
            coluna_selecao = st.selectbox(
                "Selecione um colaborador:",
                options=tabela_exibicao["ID"].tolist(),
                format_func=lambda x: tabela_exibicao.loc[tabela_exibicao["ID"] == x, "Nome Completo"].values[0],
                label_visibility="collapsed"
            )
            
        with col_btn1:
            if st.button("👁️ Visualizar", use_container_width=True):
                if coluna_selecao:
                    colaborador_sel = func_df[func_df["id"] == coluna_selecao].iloc[0]
                    docs_sel = doc_df[doc_df["colaborador_id"] == coluna_selecao]
                    modal_visualizar(conn, colaborador_sel, docs_sel)
                    
        with col_btn2:
            if st.button("✏️ Editar Prazos", use_container_width=True):
                if coluna_selecao:
                    colaborador_sel = func_df[func_df["id"] == coluna_selecao].iloc[0]
                    docs_sel = doc_df[doc_df["colaborador_id"] == coluna_selecao]
                    modal_editar_prazos(conn, colaborador_sel, docs_sel)
                    
        with col_del_btn:
            if st.button("⚙️ Excluir", use_container_width=True):
                if coluna_selecao:
                    colaborador_sel = func_df[func_df["id"] == coluna_selecao].iloc[0]
                    modal_gerenciar_colaborador(conn, colaborador_sel)

        st.markdown("<div style='font-size: 13px; color: #64748B; margin-bottom: 5px;'>💡 Dica: Clique no botão <b>Visualizar</b> acima para abrir a janela com os links para visualizar cada documento anexado.</div>", unsafe_allow_html=True)

        st.dataframe(
            tabela_exibicao.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            height=380,
            column_config={
                "Nome Completo": st.column_config.TextColumn("Nome Completo", width="medium"),
                "CPF": st.column_config.TextColumn("CPF", width="small"),
                "Local de Trabalho": st.column_config.TextColumn("Local de Trabalho", width="small"),
            }
        )
    else:
        st.warning("⚠️ Nenhum registro encontrado.")

    st.caption(
        f"Exibindo dados do Supabase · Última atualização: "
        f"{dt.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )


# ============================================================================
# ABA 2: TELA DE CADASTRO
# ============================================================================
with aba_cadastro:
    st.markdown('<div class="main-header-bar">CADASTRO DE NOVO COLABORADOR E ANEXO DE LAUDOS SST</div>', unsafe_allow_html=True)
    st.info("💡 Informe os dados, defina os prazos de validade e selecione os arquivos do seu computador para envio automático.")

    with st.form("form_cadastro_separado", clear_on_submit=True):
        st.subheader("Dados Pessoais")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            nome = st.text_input("Nome Completo *")
        with f_col2:
            cpf = st.text_input("CPF *")
        with f_col3:
            setor = st.selectbox("Setor / Local de Trabalho", SETORES)
        
        foto_url_input = st.text_input(
            "Link da Foto do Colaborador (Opcional)",
            value=""
        )
        
        st.markdown("---")
        st.subheader("Validade e Upload de Documentos Obrigatórios")
        
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        
        with d_col1:
            st.markdown("**ASO**")
            data_aso = st.date_input("Validade ASO", value=dt.date(2026, 12, 31), label_visibility="collapsed")
            file_aso = st.file_uploader("Selecionar ASO", type=["pdf", "png", "jpg", "jpeg"], key="up_aso")
            
        with d_col2:
            st.markdown("**Ficha Admissão**")
            data_ficha_adm = st.date_input("Validade Ficha Admissão", value=dt.date(2026, 12, 31), label_visibility="collapsed")
            file_adm = st.file_uploader("Selecionar Admissão", type=["pdf", "png", "jpg", "jpeg"], key="up_adm")
            
        with d_col3:
            st.markdown("**Ficha de EPI**")
            data_epi = st.date_input("Validade Ficha de EPI", value=dt.date(2026, 12, 31), label_visibility="collapsed")
            file_epi = st.file_uploader("Selecionar EPI", type=["pdf", "png", "jpg", "jpeg"], key="up_epi")
            
        with d_col4:
            st.markdown("**Certificado NR06**")
            data_nr06 = st.date_input("Validade Certificado NR06", value=dt.date(2026, 12, 31), label_visibility="collapsed")
            file_nr06 = st.file_uploader("Selecionar NR06", type=["pdf", "png", "jpg", "jpeg"], key="up_nr06")
        
        st.write("")
        b_salvar, _ = st.columns([2, 8])
        with b_salvar:
            enviar = st.form_submit_button("💾 Salvar Colaborador e Anexos", use_container_width=True)
        
        if enviar:
            if nome and cpf:
                if conn is not None:
                    try:
                        foto_final = foto_url_input.strip() if foto_url_input and foto_url_input.startswith("http") else f"https://i.pravatar.cc/150?img={dt.datetime.now().second}"
                        
                        conn.table("colaboradores").insert({
                            "nome_completo": nome,
                            "cpf": cpf,
                            "local_trabalho": setor,
                            "foto_url": foto_final
                        }).execute()
                        
                        novo_id = conn.table("colaboradores").select("id").eq("cpf", cpf).execute().data[-1]["id"]

                        # Faz o upload direto do computador para a nuvem do Supabase
                        url_aso = fazer_upload_storage(file_aso, novo_id, 2)
                        url_adm = fazer_upload_storage(file_adm, novo_id, 1)
                        url_epi = fazer_upload_storage(file_epi, novo_id, 3)
                        url_nr06 = fazer_upload_storage(file_nr06, novo_id, 4)

                        docs_para_inserir = [
                            (1, str(data_ficha_adm), url_adm),
                            (2, str(data_aso), url_aso),
                            (3, str(data_epi), url_epi),
                            (4, str(data_nr06), url_nr06)
                        ]
                        
                        for tipo_id, val_data, url_doc in docs_para_inserir:
                            conn.table("compliance_documentos").insert({
                                "colaborador_id": novo_id,
                                "tipo_documento_id": tipo_id,
                                "data_validade": val_data,
                                "arquivo_url": url_doc
                            }).execute()
                            
                        st.success("✨ Colaborador, prazos e documentos anexados com sucesso no Supabase! Retorne à aba do Dashboard.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco: {e}")
                else:
                    st.error("Conexão com o Supabase indisponível.")
            else:
                st.warning("⚠️ Por favor, preencha obrigatoriamente o Nome e o CPF.")
