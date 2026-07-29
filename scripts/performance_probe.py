"""Bounded local performance probe for deterministic analysis."""
from __future__ import annotations
import argparse, json, time, tracemalloc, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import pandas as pd
from services.analysis_engine import AnalysisEngine

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--rows",type=int,default=10000); parser.add_argument("--max-rows",type=int,default=1000000); args=parser.parse_args()
    if args.rows < 1 or args.rows > args.max_rows: raise SystemExit("rows fuori dal limite bounded")
    frame=pd.DataFrame({"categoria":[f"C{i%20}" for i in range(args.rows)],"valore":[float(i%100) for i in range(args.rows)]})
    tracemalloc.start(); started=time.perf_counter(); result=AnalysisEngine().run("Somma valore per categoria",frame); elapsed=time.perf_counter()-started; _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    print(json.dumps({"rows":args.rows,"elapsed_seconds":round(elapsed,4),"peak_memory_mb":round(peak/1024/1024,2),"status":result["execution_summary"]["status"]}))
    return 0
if __name__=="__main__": raise SystemExit(main())
