# PDR_DB_ODIN_BR_DIM

PDR_DB_ODIN_BR_DIM
Projeto responsável pela carga automática das dimensões do banco DB_ODIN_BR.

Fluxo:
SharePoint 
   ↓ 
Python 
   ↓
Snowflake

Banco: DB_ODIN_BR

Role: AZ-SF-BI-BR-DEPLOYER

Execução:
python src/main.py
