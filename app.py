"""
GESTÃO DE SEGURANÇA DO TRABALHO - DASHBOARD DE COMPLIANCE
==========================================================
Dashboard corporativo sem fotos automáticas.
"""

import datetime as dt
from pathlib import Path

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


TIPOS_DOCUMENTO = ["Ficha Admissão", "ASO", "Ficha de EPI", "Certificado NR06"]


def calcular_status_por_data(data_val):
    if not data_val or pd.isna(data_val) or str(data_val).strip() in ["", "None", "NaT"]:
        return "Falta Cadastrar", "⚠️ Falta Cadastrar"
    else:
        try:
            if isinstance(data_val, str):
                dt_val = dt.datetime.strptime(data_val.strip()[:10], "%Y-%m-%d").date()
            elif isinstance(data_val, dt.datetime):
                dt_val = data_val.date()
            elif isinstance(data_val, dt.date):
                dt_val = data_val
        except Exception:
            return "Falta Cadastrar", "⚠️ Falta Cadastrar"

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
if conn is not None:
    func_df, doc_df = carregar_dados_supabase(conn)
else:
    func_df, doc_df = pd.DataFrame(), pd.DataFrame()


# ----------------------------------------------------------------------------
# MODAL 1: VISUALIZAR DETALHES E LINKS (SEM FOTO)
# ----------------------------------------------------------------------------
@st.dialog("👁️ Detalhes e Prontuário do Colaborador")
def modal_visualizar(conn, colaborador, docs_colab):
    st.markdown(f"### {colaborador['nome_completo']}")
    st.write(f"**CPF:** {colaborador['cpf']}")
    st.write(f"**Setor / Local:** {colaborador['local_trabalho']}")
    
    st.markdown("---")
    st.subheader("Documentos e Links de Acesso")
    
    if docs_colab.empty:
        st.info("Nenhum documento cadastrado para este colaborador.")
    else:
        for _, doc in docs_colab.iterrows():
            url_arq = doc.get("arquivo_url")
            if url_arq and pd.notna(url_arq) and str(url_arq).strip() != "":
                link_html = f" - <a href='{url_arq}' target='_blank'>📎 <b>[Ver Documento na Nuvem]</b></a>"
            else:
                link_html = " - <span style='color: #94A3B8;'>Sem link cadastrado</span>"
                
            st.markdown(f"• **{doc['tipo_documento']}**: {doc['status_detalhado']}{link_html}", unsafe_allow_html=True)
    
    st.write("")
    if st.button("Fechar Prontuário", use_container_width=True):
        st.rerun()


# ----------------------------------------------------------------------------
# MODAL 2: EDITAR PRAZOS E LINKS
# ----------------------------------------------------------------------------
@st.dialog("✏️ Atualizar Prazos e Links de Documentos")
def modal_editar_prazos(conn, colaborador, docs_colab):
    st.write(f"Editando documentos de: **{colaborador['nome_completo']}**")
    st.markdown("---")
    
    # Se por acaso o colaborador não tiver registros de documentos, cria os 4 padrões vazios para permitir edição
    if docs_colab.empty:
        try:
            for t_id in [1, 2, 3, 4]:
                conn.table("compliance_documentos").insert({
                    "colaborador_id": colaborador["id"],
                    "tipo_documento_id": t_id,
                    "data_validade": None,
                    "arquivo_url": None
                }).execute()
            # Recarrega os docs após criar
            doc_resp = conn.table("compliance_documentos").select("id, colaborador_id, tipo_documento_id, data_validade, arquivo_url").eq("colaborador_id", colaborador["id"]).execute()
            tipos_resp = conn.table("tipos_documento").select("id, nome_documento").execute()
            tipos_dict = {t["id"]: t["nome_documento"] for t in tipos_resp.data}
            docs_colab = pd.DataFrame(doc_resp.data)
            if not docs_colab.empty:
                docs_colab["tipo_documento"] = docs_colab["tipo_documento_id"].map(tipos_dict)
        except Exception:
            pass

    with st.form(f"form_editar_{colaborador['id']}"):
        novas_datas = {}
        novos_links = {}
        
        for _, doc in docs_colab.iterrows():
            val_atual = None
            try:
                val_raw = doc.get("data_validade")
                if pd.notna(val_raw) and str(val_raw).strip() not in ["", "None", "NaT"]:
                    val_atual = dt.datetime.strptime(str(val_raw)[:10], "%Y-%m-%d").date()
            except Exception:
                pass
                
            link_atual = doc.get("arquivo_url") if pd.notna(doc.get("arquivo_url")) else ""
            
            st.markdown(f"**{doc.get('tipo_documento', 'Documento')}**")
            novas_datas[doc["tipo_documento_id"]] = st.date_input(
                f"Validade ({doc.get('tipo_documento', 'Doc')})",
                value=val_atual,
                key=f"date_edit_{colaborador['id']}_{doc['tipo_documento_id']}"
            )
            novos_links[doc["tipo_documento_id"]] = st.text_input(
                f"Link do documento ({doc.get('tipo_documento', 'Doc')})",
                value=link_atual,
                key=f"link_edit_{colaborador['id']}_{doc['tipo_documento_id']}",
                placeholder="Cole o link do Google Drive, SharePoint ou OneDrive aqui..."
            )
            st.markdown("---")
            
        salvar_edicao = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
        
        if salvar_edicao:
            try:
                for tipo_id, nova_data in novas_datas.items():
                    link_informado = novos_links.get(tipo_id, "").strip()
                    dados_update = {
                        "data_validade": str(nova_data) if nova_data else None,
                        "arquivo_url": link_informado if link_informado else None
                    }
                    
                    # Verifica se o registro já existe para atualizar ou se precisa inserir
                    existe = conn.table("compliance_documentos").select("id").eq("colaborador_id", colaborador["id"]).eq("tipo_documento_id", tipo_id).execute()
                    if existe.data:
                        conn.table("compliance_documentos").update(dados_update).eq("colaborador_id", colaborador["id"]).eq("tipo_documento_id", tipo_id).execute()
                    else:
                        dados_update["colaborador_id"] = colaborador["id"]
                        dados_update["tipo_documento_id"] = tipo_id
                        conn.table("compliance_documentos").insert(dados_update).execute()
                    
                st.success("✨ Prazos e links atualizados com sucesso!")
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
aba_principal, aba_cadastro, aba_importacao = st.tabs(["📊 Dashboard de Compliance", "➕ Cadastrar Novo Colaborador", "📁 Importar Planilha"])


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
    
    CORES = {
        "Regular": "#2563EB", 
        "Vence em Breve": "#F59E0B", 
        "Vencido": "#EF4444",
        "Falta Cadastrar": "#94A3B8"
    }

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
            setores_existentes = func_df["local_trabalho"].dropna().unique().tolist()
            if not setores_existentes:
                setores_existentes = ["Geral"]
            
            status_possiveis = ["Regular", "Vence em Breve", "Vencido", "Falta Cadastrar"]
            todas_combos = pd.MultiIndex.from_product(
                [setores_existentes, status_possiveis], names=["local_trabalho", "status_grupo"]
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
            category_orders={"status_grupo": ["Regular", "Vence em Breve", "Vencido", "Falta Cadastrar"]},
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
        # --- FILTRO POR SETOR ---
        lista_setores = ["Todos os Setores"] + sorted(func_df["local_trabalho"].dropna().unique().tolist())
        setor_selecionado = st.selectbox("Filtrar por Setor / Local de Trabalho:", options=lista_setores)

        if setor_selecionado != "Todos os Setores":
            func_filtrado = func_df[func_df["local_trabalho"] == setor_selecionado]
        else:
            func_filtrado = func_df

        mapa_status = {}
        for _, r in doc_df.iterrows():
            c_id = r["colaborador_id"]
            t_doc = r["tipo_documento"]
            g, s = calcular_status_por_data(r["data_validade"])
            
            url = r.get("arquivo_url")
            if url and pd.notna(url) and str(url).strip() != "":
                s_final = f"{s} <a href='{url}' target='_blank' style='text-decoration:none; margin-left: 5px;' title='Ver Documento'>📎</a>"
            else:
                s_final = s
                
            if c_id not in mapa_status:
                mapa_status[c_id] = {}
            mapa_status[c_id][t_doc] = s_final

        lista_linhas = []
        for _, colab in func_filtrado.iterrows():
            c_id = colab["id"]
            row_data = {
                "id": c_id,
                "Nome Completo": colab["nome_completo"],
                "CPF": str(colab["cpf"]).strip(),
                "Local de Trabalho": colab["local_trabalho"]
            }
            for tipo in TIPOS_DOCUMENTO:
                row_data[tipo] = mapa_status.get(c_id, {}).get(tipo, "⚠️ Falta Cadastrar")
            lista_linhas.append(row_data)

        if lista_linhas:
            tabela_html_df = pd.DataFrame(lista_linhas).sort_values("Nome Completo")
            ids_disponiveis = tabela_html_df["id"].tolist()
            tabela_exibicao = tabela_html_df.drop(columns=["id"])

            if "coluna_selecao_id" not in st.session_state or st.session_state["coluna_selecao_id"] not in ids_disponiveis:
                st.session_state["coluna_selecao_id"] = ids_disponiveis[0] if ids_disponiveis else None

            col_sel, col_btn1, col_btn2, col_del_btn = st.columns([5, 2, 2, 2])
            
            with col_sel:
                coluna_selecao = st.selectbox(
                    "Selecione um colaborador:",
                    options=ids_disponiveis,
                    format_func=lambda x: tabela_html_df.loc[tabela_html_df["id"] == x, "Nome Completo"].values[0] if not tabela_html_df.loc[tabela_html_df["id"] == x].empty else "",
                    key="coluna_selecao_id",
                    label_visibility="collapsed"
                )
                
            with col_btn1:
                if st.button("👁️ Visualizar", use_container_width=True):
                    if coluna_selecao:
                        colaborador_sel = func_df[func_df["id"] == coluna_selecao].iloc[0]
                        docs_sel = doc_df[doc_df["colaborador_id"] == coluna_selecao]
                        modal_visualizar(conn, colaborador_sel, docs_sel)
                        
            with col_btn2:
                if st.button("✏️ Editar Prazos e Links", use_container_width=True):
                    if coluna_selecao:
                        colaborador_sel = func_df[func_df["id"] == coluna_selecao].iloc[0]
                        docs_sel = doc_df[doc_df["colaborador_id"] == coluna_selecao]
                        modal_editar_prazos(conn, colaborador_sel, docs_sel)
                        
            with col_del_btn:
                if st.button("⚙️ Excluir", use_container_width=True):
                    if coluna_selecao:
                        colaborador_sel = func_df[func_df["id"] == coluna_selecao].iloc[0]
                        modal_gerenciar_colaborador(conn, colaborador_sel)

            st.markdown("<div style='font-size: 13px; color: #64748B; margin-bottom: 5px;'>💡 Dica: O símbolo <b>📎</b> ao lado da data na tabela já serve como link direto para abrir o documento em nova aba!</div>", unsafe_allow_html=True)

            st.markdown(
                """
                <style>
                    table.dataframe {
                        width: 100%;
                        border-collapse: collapse;
                        font-family: sans-serif;
                        font-size: 14px;
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 8px;
                        overflow: hidden;
                    }
                    table.dataframe th {
                        background-color: #F8FAFC;
                        color: #0F172A;
                        text-align: left;
                        padding: 12px 16px;
                        border-bottom: 2px solid #E2E8F0;
                        font-weight: 700;
                    }
                    table.dataframe td {
                        padding: 12px 16px;
                        border-bottom: 1px solid #E2E8F0;
                        color: #334155;
                        vertical-align: middle;
                    }
                    table.dataframe th:nth-child(2),
                    table.dataframe td:nth-child(2) {
                        text-align: center;
                        white-space: nowrap;
                    }
                    table.dataframe tr:hover {
                        background-color: #F1F5F9;
                    }
                </style>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                tabela_exibicao.to_html(escape=False, index=False, classes="dataframe"),
                unsafe_allow_html=True
            )
        else:
            st.info("ℹ️ Nenhum colaborador encontrado para o setor selecionado.")
    else:
        st.warning("⚠️ Nenhum registro encontrado.")

    st.caption(
        f"Exibindo dados do Supabase · Última atualização: "
        f"{dt.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )


# ============================================================================
# ABA 2: TELA DE CADASTRO MANUAL
# ============================================================================
with aba_cadastro:
    st.markdown('<div class="main-header-bar">CADASTRO DE NOVO COLABORADOR E LINKS DE LAUDOS SST</div>', unsafe_allow_html=True)
    st.info("💡 Informe os dados, defina os prazos e cole o link do documento (Google Drive, SharePoint, OneDrive, etc.).")

    with st.form("form_cadastro_separado", clear_on_submit=True):
        st.subheader("Dados Pessoais")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            nome = st.text_input("Nome *")
        with f_col2:
            cpf = st.text_input("CPF *")
        with f_col3:
            setor = st.text_input("Setor / Local de Trabalho *", placeholder="Ex: Setor A, Obra 1...")
            
        st.markdown("---")
        st.subheader("Validade e Links dos Documentos Obrigatórios")
        
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        
        with d_col1:
            st.markdown("**ASO**")
            data_aso = st.date_input("Validade ASO", value=None, key="cad_d_aso")
            link_aso = st.text_input("Link ASO", placeholder="https://...", key="cad_l_aso")
            
        with d_col2:
            st.markdown("**Ficha Admissão**")
            data_ficha_adm = st.date_input("Validade Ficha Admissão", value=None, key="cad_d_adm")
            link_adm = st.text_input("Link Admissão", placeholder="https://...", key="cad_l_adm")
            
        with d_col3:
            st.markdown("**Ficha de EPI**")
            data_epi = st.date_input("Validade Ficha de EPI", value=None, key="cad_d_epi")
            link_epi = st.text_input("Link EPI", placeholder="https://...", key="cad_l_epi")
            
        with d_col4:
            st.markdown("**Certificado NR06**")
            data_nr06 = st.date_input("Validade Certificado NR06", value=None, key="cad_d_nr06")
            link_nr06 = st.text_input("Link NR06", placeholder="https://...", key="cad_l_nr06")
        
        st.write("")
        b_salvar, _ = st.columns([2, 8])
        with b_salvar:
            enviar = st.form_submit_button("💾 Salvar Colaborador e Links", use_container_width=True)
        
        if enviar:
            if nome and cpf and setor:
                if conn is not None:
                    try:
                        conn.table("colaboradores").insert({
                            "nome_completo": nome,
                            "cpf": str(cpf).strip(),
                            "local_trabalho": setor,
                            "foto_url": ""
                        }).execute()
                        
                        novo_id = conn.table("colaboradores").select("id").eq("cpf", str(cpf).strip()).execute().data[-1]["id"]

                        docs_para_inserir = [
                            (1, str(data_ficha_adm) if data_ficha_adm else None, link_adm.strip()),
                            (2, str(data_aso) if data_aso else None, link_aso.strip()),
                            (3, str(data_epi) if data_epi else None, link_epi.strip()),
                            (4, str(data_nr06) if data_nr06 else None, link_nr06.strip())
                        ]
                        
                        for tipo_id, val_data, url_doc in docs_para_inserir:
                            conn.table("compliance_documentos").insert({
                                "colaborador_id": novo_id,
                                "tipo_documento_id": tipo_id,
                                "data_validade": val_data,
                                "arquivo_url": url_doc if url_doc else None
                            }).execute()
                            
                        st.success("✨ Colaborador, prazos e links salvos com sucesso no Supabase! Retorne à aba do Dashboard.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco: {e}")
                else:
                    st.error("Conexão com o Supabase indisponível.")
            else:
                st.warning("⚠️ Por favor, preencha obrigatoriamente o Nome, o CPF e o Setor/Local de Trabalho.")


# ============================================================================
# ABA 3: IMPORTAÇÃO EM MASSA DE PLANILHA (MÚLTIPLAS ABAS/SETORES)
# ============================================================================
with aba_importacao:
    st.markdown('<div class="main-header-bar">IMPORTAÇÃO AUTOMÁTICA DE PLANILHAS POR SETOR</div>', unsafe_allow_html=True)
    st.info("💡 Faça o upload de um arquivo Excel contendo várias abas (cada aba representando um setor). O sistema lerá o nome da aba como setor e os cadastros automaticamente.")

    arquivo_upload = st.file_uploader("Escolha o arquivo Excel (.xlsx)", type=["xlsx"])

    if arquivo_upload is not None:
        try:
            todas_as_abas = pd.read_excel(arquivo_upload, sheet_name=None)
            st.success(f"Arquivo carregado com sucesso! Foram encontradas {len(todas_as_abas)} abas (setores).")

            for nome_aba, df_aba in todas_as_abas.items():
                st.markdown(f"**Setor / Aba: {nome_aba}** ({len(df_aba)} registros encontrados)")
                st.dataframe(df_aba.head(2))

            if st.button("🚀 Processar e Importar Todas as Abas para o Supabase", use_container_width=True):
                if conn is not None:
                    sucessos = 0
                    erros = 0

                    for nome_aba, df_aba in todas_as_abas.items():
                        setor_atual = nome_aba.strip()

                        for _, linha in df_aba.iterrows():
                            try:
                                nome_colab = str(linha.get("Nome", linha.get("Nome Completo", ""))).strip()
                                cpf_colab = str(linha.get("CPF", "")).strip()

                                if not nome_colab or nome_colab == "nan" or not cpf_colab or cpf_colab == "nan":
                                    continue

                                conn.table("colaboradores").insert({
                                    "nome_completo": nome_colab,
                                    "cpf": cpf_colab,
                                    "local_trabalho": setor_atual,
                                    "foto_url": ""
                                }).execute()

                                novo_id = conn.table("colaboradores").select("id").eq("cpf", cpf_colab).execute().data[-1]["id"]

                                for tipo_id in [1, 2, 3, 4]:
                                    conn.table("compliance_documentos").insert({
                                        "colaborador_id": novo_id,
                                        "tipo_documento_id": tipo_id,
                                        "data_validade": None,
                                        "arquivo_url": None
                                    }).execute()

                                sucessos += 1
                            except Exception:
                                erros += 1

                    st.success(f"Importação finalizada! {sucessos} cadastros inseridos com sucesso.")
                    if erros > 0:
                        st.warning(f"Ocorreram {erros} falhas ou registros ignorados (verifique se há CPFs duplicados ou campos vazios).")

                    st.cache_data.clear()
                else:
                    st.error("Conexão com o Supabase indisponível.")
        except Exception as e:
            st.error(f"Erro ao processar as planilhas: {e}")
