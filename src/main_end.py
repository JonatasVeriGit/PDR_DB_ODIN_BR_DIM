"""
========================================================================
PROJETO: Carga de Arquivos Excel para Snowflake

OBJETIVO:
    Ler todos os arquivos Excel da pasta INPUT e realizar:
        1. Leitura do arquivo
        2. Criação/Recriação da tabela no Snowflake
        3. Carga dos dados via write_pandas
        4. Validação da quantidade carregada

EXEMPLO:
    DIM_CALENDARIO.xlsx -> SH_LANDING_DEVEL.DIM_CALENDARIO
    DIM_CLIENTE.xlsx    -> SH_LANDING_DEVEL.DIM_CLIENTE
========================================================================
"""

import os
import logging
import pandas as pd

import config

from conexao import conectar
from snowflake.connector.pandas_tools import write_pandas


# =========================================================================
# CONFIGURAÇÃO DE LOG
# =========================================================================

logging.basicConfig(
    filename=config.LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================================================
# CONFIGURAÇÕES
# =========================================================================

DATABASE = config.DATABASE
SCHEMA = config.SCHEMA
INPUT_PATH = config.INPUT_PATH


# =========================================================================
# FUNÇÃO PRINCIPAL
# =========================================================================

def main():

    print("\n" + "=" * 80)
    print("INICIANDO PROCESSO DE CARGA")
    print("=" * 80)

    logging.info("=" * 80)
    logging.info("INICIANDO PROCESSO DE CARGA")

    total_arquivos = 0
    total_sucesso = 0
    total_erro = 0

    conn = None
    cur = None

    try:

# ================================================================
# ETAPA 1 - CONEXÃO
# ================================================================

        print("\n[ETAPA 1] Conectando ao Snowflake...")

        conn = conectar()
        cur = conn.cursor()

        print("✅ Conexão realizada com sucesso")

        logging.info(
            "Conexão Snowflake realizada com sucesso"
        )

# ================================================================
# ETAPA 2 - CONTEXTO
# ================================================================

        print("\n[ETAPA 2] Configurando ambiente...")

        cur.execute(f"USE DATABASE {DATABASE}")
        cur.execute(f"USE SCHEMA {SCHEMA}")

        cur.execute("""
            SELECT CURRENT_DATABASE(),
                   CURRENT_SCHEMA(),
                   CURRENT_ROLE()
        """)

        contexto = cur.fetchone()

        print(f"Database : {contexto[0]}")
        print(f"Schema   : {contexto[1]}")
        print(f"Role     : {contexto[2]}")

        logging.info(f"Database: {contexto[0]}")
        logging.info(f"Schema: {contexto[1]}")
        logging.info(f"Role: {contexto[2]}")

# ================================================================
# ETAPA 3 - ARQUIVOS
# ================================================================

        print("\n[ETAPA 3] Buscando arquivos na pasta INPUT")

        arquivos = [
            arquivo
            for arquivo in os.listdir(INPUT_PATH)
            if arquivo.lower().endswith(".xlsx")
        ]

        total_arquivos = len(arquivos)

        print(
            f"Arquivos encontrados: {total_arquivos}"
        )

        logging.info(
            f"Arquivos encontrados: {total_arquivos}"
        )

        if total_arquivos == 0:

            print("⚠️ Nenhum arquivo encontrado.")

            logging.warning(
                "Nenhum arquivo encontrado."
            )

            return

# ================================================================
# ETAPA 4 - PROCESSAMENTO
# ================================================================

        for arquivo in arquivos:

            print("\n" + "-" * 80)
            print(f"PROCESSANDO: {arquivo}")
            print("-" * 80)

            try:

                tabela = os.path.splitext(
                    arquivo
                )[0].upper()

                caminho_arquivo = os.path.join(
                    INPUT_PATH,
                    arquivo
                )

                print(f"Arquivo : {arquivo}")
                print(f"Tabela  : {tabela}")

                logging.info(
                    f"Processando arquivo: {arquivo}"
                )

                logging.info(
                    f"Tabela destino: {SCHEMA}.{tabela}"
                )

# ---------------------------------------------------------
# LEITURA EXCEL
# ---------------------------------------------------------

                print(
                    "\n[1/4] Lendo arquivo Excel..."
                )

                df = pd.read_excel(
                    caminho_arquivo
                )

                df = df.convert_dtypes()

                print(
                    f"Leitura concluída -> "
                    f"{df.shape[0]} linhas x "
                    f"{df.shape[1]} colunas"
                )

                logging.info(
                    f"Excel carregado: "
                    f"{df.shape[0]} linhas x "
                    f"{df.shape[1]} colunas"
                )

# ---------------------------------------------------------
# CRIAÇÃO TABELA
# ---------------------------------------------------------

                print(
                    "\n[2/4] Criando tabela Snowflake..."
                )

                colunas = []

                for col in df.columns:

                    tipo_pandas = str(
                        df[col].dtype
                    )

                    nome_coluna = col.upper()

                    # LOGIN E ORIGEM SEMPRE TEXTO
                    if nome_coluna in (
                      "LOGIN",
                      "ORIGEM",
                    ):

                        tipo_snowflake = "VARCHAR"

                    elif (
                        "DATA" in nome_coluna
                        or "DATE" in nome_coluna
                        or nome_coluna.startswith("DT_")
                    ):

                        tipo_snowflake = "DATE"

                    elif "datetime" in tipo_pandas.lower():

                        tipo_snowflake = "TIMESTAMP_NTZ"

                    elif tipo_pandas in (
                        "int64",
                        "int32",
                        "Int64"
                    ):

                        tipo_snowflake = "NUMBER"

                    elif tipo_pandas in (
                        "float64",
                        "float32",
                        "Float64"
                    ):

                        tipo_snowflake = "FLOAT"

                    elif tipo_pandas in (
                        "bool",
                        "boolean"
                    ):

                        tipo_snowflake = "BOOLEAN"

                    else:

                        tipo_snowflake = "VARCHAR"

                    colunas.append(
                        f'"{col}" {tipo_snowflake}'
                    )

                    logging.info(
                        f"Coluna: {col} | "
                        f"Pandas: {tipo_pandas} | "
                        f"Snowflake: {tipo_snowflake}"
                    )

                create_sql = f"""
                CREATE OR REPLACE TABLE
                {SCHEMA}.{tabela}
                (
                    {', '.join(colunas)}
                )
                """

                cur.execute(
                    create_sql
                )

                print(
                    "Tabela criada com sucesso"
                )

                logging.info(
                    f"Tabela criada: {SCHEMA}.{tabela}"
                )

# ---------------------------------------------------------
# CARGA
# ---------------------------------------------------------
                print(
                    "\n[3/4] Realizando carga..."
                )

                df = df.replace(
                {
                pd.NA: None
                }
                )

                df = df.reset_index(
                drop=True
                )

                # LOGIN E ORIGEM SEMPRE TEXTO
                COLUNAS_SEMPRE_TEXTO = [
                    "LOGIN",
                    "ORIGEM"
                ]

                for coluna in COLUNAS_SEMPRE_TEXTO:

                    if coluna in df.columns:

                        df[coluna] = (
                            df[coluna]
                            .astype(str)
                        )


                success, nchunks, nrows, _ = write_pandas(
                    conn,
                    df,
                    table_name=tabela,
                    schema=SCHEMA
                )

                if not success:

                    raise Exception(
                        "Falha retornada pelo write_pandas"
                    )

                print(
                    f"Carga concluída: {nrows} linhas"
                )

                logging.info(
                    f"Linhas carregadas: {nrows}"
                )

                  
# ---------------------------------------------------------
# VALIDAÇÃO
# ---------------------------------------------------------

                print(
                    "\n[4/4] Validando carga..."
                )

                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM {SCHEMA}.{tabela}
                """)

                quantidade = cur.fetchone()[0]

                print(
                    f"Quantidade na tabela: {quantidade}"
                )

                logging.info(
                    f"Validação Snowflake: {quantidade}"
                )

                print(
                    f"✅ Arquivo {arquivo} processado com sucesso"
                )

                total_sucesso += 1

            except Exception as erro_arquivo:

                total_erro += 1

                print(
                    f"❌ Erro ao processar arquivo: {arquivo}"
                )

                print(
                    str(erro_arquivo)
                )

                logging.error(
                    f"Erro no arquivo {arquivo}: {erro_arquivo}"
                )

# ================================================================
# RESUMO
# ================================================================

        print("\n" + "=" * 80)
        print("RESUMO DA EXECUÇÃO")
        print("=" * 80)

        print(
            f"Arquivos encontrados : {total_arquivos}"
        )

        print(
            f"Arquivos com sucesso : {total_sucesso}"
        )

        print(
            f"Arquivos com erro    : {total_erro}"
        )

        logging.info(
            f"Arquivos encontrados: {total_arquivos}"
        )

        logging.info(
            f"Arquivos com sucesso: {total_sucesso}"
        )

        logging.info(
            f"Arquivos com erro: {total_erro}"
        )

    except Exception as erro:

        print(
            "\n❌ ERRO GERAL DO PROCESSO"
        )

        print(str(erro))

        logging.error(
            f"Erro geral: {erro}"
        )

    finally:

        print(
            "\nEncerrando conexões..."
        )

        if cur:
            cur.close()

        if conn:
            conn.close()

        print(
            "✅ Conexão encerrada"
        )

        print(
            "✅ Processo finalizado"
        )

        logging.info(
            "Conexão encerrada"
        )

        logging.info(
            "Processo finalizado"
        )

        logging.info("=" * 80)


# =========================================================================
# EXECUÇÃO
# =========================================================================

if __name__ == "__main__":
    main()
