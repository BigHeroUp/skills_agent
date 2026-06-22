"""Service Oracle usato dalla dashboard Dash."""

from connectors.data_connectors import DataSourceFactory


def verify_oracle_connection(host, port, database, user, password, logger=None):
    """Verifica una connessione Oracle e ritorna la configurazione server-side.

    La password viene restituita solo al chiamante server-side; il callback Dash
    continua a non inviarla allo store browser.
    """
    connector = None
    try:
        if logger:
            logger.info("Test Oracle richiesto dalla dashboard")
        connector = DataSourceFactory.create_connector(
            "oracle",
            host=host.strip(),
            port=int(port),
            database=database.strip(),
            user=user.strip(),
            password=password,
        )
        connector.test_connection()
        config = {
            "host": host.strip(),
            "port": int(port),
            "database": database.strip(),
            "user": user.strip(),
            "password": password,
        }
        if logger:
            logger.info("Test Oracle riuscito")
        return config
    finally:
        if connector:
            connector.close()
