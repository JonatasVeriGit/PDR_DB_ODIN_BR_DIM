import snowflake.connector
import config


def conectar():

    conn = snowflake.connector.connect(
        user=config.USER,
        authenticator=config.AUTHENTICATOR,
        account=config.ACCOUNT,
        warehouse=config.WAREHOUSE,
        database=config.DATABASE,
        schema=config.SCHEMA,
        role=config.ROLE
    )

    return conn
