"""
Connettori per le diverse fonti dati
"""

import pandas as pd
import oracledb
from pathlib import Path
from typing import Any
import dask.dataframe as dd
from utils.logging_config import get_logger
from utils.oracle_query_validator import QuerySafetyValidator


logger = get_logger("connectors")


class OracleConnector:
    """Connettore per database Oracle"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
    
    def connect(self) -> bool:
        """Connetti al database Oracle"""
        try:
            logger.info("Apertura connessione Oracle richiesta")
            self.connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=f"{self.host}:{self.port}/{self.database}"
            )
            logger.info("Connessione Oracle aperta")
            return True
        except Exception as e:
            logger.error("Connessione Oracle fallita: %s", type(e).__name__)
            raise Exception(f"❌ Errore connessione Oracle: {str(e)}")

    def test_connection(self) -> bool:
        """Verifica che le credenziali consentano una connessione valida."""
        try:
            logger.info("Test connessione Oracle avviato")
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1 FROM dual")
            cursor.fetchone()
            cursor.close()
            logger.info("Test connessione Oracle completato con successo")
            return True
        finally:
            self.close()
    
    def query(self, sql: str, chunk_size: int = 10000) -> pd.DataFrame:
        """Esegui una query di sola lettura con chunking per grandi volumi."""
        validation = QuerySafetyValidator.validate_read_only(sql)
        if not validation.is_valid:
            logger.warning("Query Oracle bloccata: %s", validation.reason)
            raise ValueError(validation.reason)

        if not self.connection:
            self.connect()
        
        try:
            logger.info("Query Oracle di lettura avviata")
            # Usa pandas per leggere direttamente da Oracle
            df = pd.read_sql(sql, self.connection, chunksize=chunk_size)
            
            # Concatena i chunk
            chunks = []
            for chunk in df:
                chunks.append(chunk)
            
            result = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
            logger.info("Query Oracle completata. righe=%s colonne=%s", len(result), len(result.columns))
            return result
        except Exception as e:
            logger.error("Query Oracle fallita: %s", type(e).__name__)
            raise Exception(f"❌ Errore query Oracle: {str(e)}")
    
    def close(self):
        """Chiudi la connessione"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Connessione Oracle chiusa")


class CSVConnector:
    """Connettore per file CSV con supporto grandi volumi"""
    
    @staticmethod
    def read(file_path: str, chunk_size: int = 50000) -> pd.DataFrame:
        """Leggi CSV con chunking per grandi file"""
        try:
            # Per file molto grandi, usa Dask
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            
            if file_size_mb > 100:  # Se > 100MB usa Dask
                dask_df = dd.read_csv(file_path)
                return dask_df.compute()  # Converti a Pandas
            else:
                return pd.read_csv(file_path)
        except Exception as e:
            raise Exception(f"❌ Errore lettura CSV: {str(e)}")


class ExcelConnector:
    """Connettore per file Excel"""
    
    @staticmethod
    def read(file_path: str, sheet_name: str = 0, chunk_size: int = 10000) -> pd.DataFrame:
        """Leggi Excel con chunking"""
        try:
            return pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception as e:
            raise Exception(f"❌ Errore lettura Excel: {str(e)}")


class DataSourceFactory:
    """Factory per gestire le diverse fonti dati"""
    
    @staticmethod
    def create_connector(source_type: str, **kwargs) -> Any:
        """Crea il connettore appropriato"""
        if source_type.lower() == "oracle":
            return OracleConnector(**kwargs)
        elif source_type.lower() == "csv":
            return CSVConnector()
        elif source_type.lower() == "excel":
            return ExcelConnector()
        else:
            raise ValueError(f"❌ Tipo sorgente non supportato: {source_type}")
