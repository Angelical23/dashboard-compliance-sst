import streamlit as st
from st_supabase_connection import SupabaseConnection

# Inicializa a conexão com o Supabase pegando os dados do secrets.toml
conn = st.connection("supabase", type=SupabaseConnection)

def popular_dados():
    # 1. Inserir Tipos de Documentos
    documentos = [
        {"id": 1, "nome_documento": "Ficha Admissão"},
        {"id": 2, "nome_documento": "ASO"},
        {"id": 3, "nome_documento": "Ficha EPI"},
        {"id": 4, "nome_documento": "Certificado NR06"}
    ]
    for doc in documentos:
        conn.table("tipos_documento").upsert(doc).execute()

    # 2. Inserir Colaboradores
    colaboradores = [
        {"id": 1, "nome_completo": "Carlos Oliveira", "cpf": "034375887265", "local_trabalho": "Production"},
        {"id": 2, "nome_completo": "Fernanda Costa", "cpf": "084694637929", "local_trabalho": "Logistics"},
        {"id": 3, "nome_completo": "Pedro Santos", "cpf": "934270889232", "local_trabalho": "Admin"},
        {"id": 4, "nome_completo": "Lucas Almeida", "cpf": "054499777768", "local_trabalho": "Maint."},
        {"id": 5, "nome_completo": "Jobs Almeida", "cpf": "054498736136", "local_trabalho": "Production"},
        {"id": 6, "nome_completo": "Carlia Olivera", "cpf": "08032250134", "local_trabalho": "Logistics"}
    ]
    for colab in colaboradores:
        conn.table("colaboradores").upsert(colab).execute()

    # 3. Inserir Histórico de Compliance / Status dos Documentos
    compliance = [
        # Carlos Oliveira
        {"colaborador_id": 1, "tipo_documento_id": 1, "status_documento": "Em Dia"},
        {"colaborador_id": 1, "tipo_documento_id": 2, "status_documento": "Em Dia"},
        {"colaborador_id": 1, "tipo_documento_id": 3, "status_documento": "Em Dia"},
        {"colaborador_id": 1, "tipo_documento_id": 4, "status_documento": "Vencido"},
        # Fernanda Costa
        {"colaborador_id": 2, "tipo_documento_id": 1, "status_documento": "Em Dia"},
        {"colaborador_id": 2, "tipo_documento_id": 2, "status_documento": "Em Dia"},
        {"colaborador_id": 2, "tipo_documento_id": 3, "status_documento": "Em Dia"},
        {"colaborador_id": 2, "tipo_documento_id": 4, "status_documento": "Em Dia"},
        # Pedro Santos
        {"colaborador_id": 3, "tipo_documento_id": 1, "status_documento": "Em Dia"},
        {"colaborador_id": 3, "tipo_documento_id": 2, "status_documento": "Vence em 15 dias"},
        {"colaborador_id": 3, "tipo_documento_id": 3, "status_documento": "Vence em 25 dias"},
        {"colaborador_id": 3, "tipo_documento_id": 4, "status_documento": "Vence em 10 dias"},
        # Lucas Almeida
        {"colaborador_id": 4, "tipo_documento_id": 1, "status_documento": "Em Dia"},
        {"colaborador_id": 4, "tipo_documento_id": 2, "status_documento": "Vencido"},
        {"colaborador_id": 4, "tipo_documento_id": 3, "status_documento": "Em Dia"},
        {"colaborador_id": 4, "tipo_documento_id": 4, "status_documento": "Vence em 10 dias"}
    ]
    for item in compliance:
        conn.table("compliance_documentos").insert(item).execute()

    print("✅ Banco de dados populado com sucesso!")

if __name__ == "__main__":
    popular_dados()
