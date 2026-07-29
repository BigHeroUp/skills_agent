import io
import pandas as pd
import pytest
from services.platform.robust_ingestion import load_tabular_upload

def test_csv_ingestion_detects_semicolon_and_cp1252():
    result=load_tabular_upload("città;valore\nForlì;1\nRoma;2\n".encode("cp1252"),"dati.csv",max_rows=10)
    assert result.dataframe.columns.tolist()==["città","valore"]
    assert len(result.dataframe)==2
    assert result.warnings

def test_ingestion_enforces_row_and_column_limits():
    with pytest.raises(ValueError,match="record"):
        load_tabular_upload(b"a\n1\n2\n","x.csv",max_rows=1)
    with pytest.raises(ValueError,match="colonne"):
        load_tabular_upload(b"a,b,c\n1,2,3\n","x.csv",max_rows=2,max_columns=2)

def test_realistic_excel_roundtrip():
    stream=io.BytesIO(); pd.DataFrame({"data":["29/07/2026"],"valore":[1.5]}).to_excel(stream,index=False)
    result=load_tabular_upload(stream.getvalue(),"x.xlsx",max_rows=10)
    assert result.source_type=="excel" and len(result.dataframe)==1
