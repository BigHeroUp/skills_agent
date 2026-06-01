"""
Data Source Manager Agent
Gestisce la selezione e il caricamento dei dati da diverse fonti
"""

import os
import pandas as pd
from agents.base_agent import BaseAgent
from connectors.data_connectors import DataSourceFactory
from utils.context import AgentContext


class DataSourceManagerAgent(BaseAgent):
    """Agent che gestisce le fonti dati"""
    
    def __init__(self):
        super().__init__(name="DataSourceManager", skill_name="oracle_sql")
        self.supported_sources = ["oracle", "csv", "excel"]
    
    def process(self, context: AgentContext) -> AgentContext:
        """Gestisce la selezione e il caricamento dati"""
        self.log("Inizializzazione gestore fonti dati...")
        
        try:
            # Estrai informazioni sulla fonte dal metadata
            source_type = context.metadata.get("source_type", "").lower()
            
            if not source_type or source_type not in self.supported_sources:
                context.add_error(f"Fonte dati non supportata: {source_type}", agent=self.name)
                return context
            
            self.log(f"Fonte selezionata: {source_type}")
            
            # Elabora in base al tipo di fonte
            if source_type == "oracle":
                self._handle_oracle(context)
            elif source_type == "csv":
                self._handle_csv(context)
            elif source_type == "excel":
                self._handle_excel(context)
            
            self.log("✅ Dati caricati con successo")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
    
    def _handle_oracle(self, context: AgentContext):
        """Gestisci caricamento da Oracle"""
        connector = None
        try:
            oracle_config = context.metadata.get("oracle_config", {})
            query = context.metadata.get("oracle_query", "").strip()
            if not query:
                raise ValueError("Inserire una query SELECT per estrarre i dati Oracle.")

            connector = DataSourceFactory.create_connector(
                "oracle",
                host=oracle_config.get("host"),
                port=int(oracle_config.get("port", 1521)),
                user=oracle_config.get("user"),
                password=oracle_config.get("password"),
                database=oracle_config.get("database"),
            )
            df = connector.query(query)
            
            context.raw_data = {
                "dataframe": df,
                "row_count": len(df),
                "columns": list(df.columns),
                "source": "oracle",
                "shape": df.shape
            }
        except Exception as e:
            raise Exception(f"Errore Oracle: {str(e)}")
        finally:
            if connector:
                connector.close()
    
    def _handle_csv(self, context: AgentContext):
        """Gestisci caricamento da CSV"""
        try:
            uploaded_df = context.metadata.get("dataframe")
            if isinstance(uploaded_df, pd.DataFrame):
                df = uploaded_df.copy()
                context.raw_data = {
                    "dataframe": df,
                    "row_count": len(df),
                    "columns": list(df.columns),
                    "source": "csv",
                    "shape": df.shape,
                    "file_size_mb": context.metadata.get("file_size_mb", 0),
                }
                return

            file_path = context.metadata.get("file_path")
            
            if not file_path or not os.path.exists(file_path):
                raise Exception(f"File non trovato: {file_path}")
            
            # Per grandi file, usa chunking
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size_mb > 100:
                import dask.dataframe as dd
                dask_df = dd.read_csv(file_path)
                df = dask_df.compute()
            else:
                df = pd.read_csv(file_path)
            
            context.raw_data = {
                "dataframe": df,
                "row_count": len(df),
                "columns": list(df.columns),
                "source": "csv",
                "shape": df.shape,
                "file_size_mb": file_size_mb
            }
            
        except Exception as e:
            raise Exception(f"Errore CSV: {str(e)}")
    
    def _handle_excel(self, context: AgentContext):
        """Gestisci caricamento da Excel"""
        try:
            uploaded_df = context.metadata.get("dataframe")
            if isinstance(uploaded_df, pd.DataFrame):
                df = uploaded_df.copy()
                context.raw_data = {
                    "dataframe": df,
                    "row_count": len(df),
                    "columns": list(df.columns),
                    "source": "excel",
                    "shape": df.shape,
                }
                return

            file_path = context.metadata.get("file_path")
            sheet_name = context.metadata.get("sheet_name", 0)
            
            if not file_path or not os.path.exists(file_path):
                raise Exception(f"File non trovato: {file_path}")
            
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            context.raw_data = {
                "dataframe": df,
                "row_count": len(df),
                "columns": list(df.columns),
                "source": "excel",
                "shape": df.shape
            }
            
        except Exception as e:
            raise Exception(f"Errore Excel: {str(e)}")
