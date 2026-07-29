"""Run the second bounded adversarial campaign."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from validation_lab.adversarial_campaign_v2 import run_adversarial_campaign_v2
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path); args=parser.parse_args()
    report=run_adversarial_campaign_v2(); rendered=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered,encoding="utf-8")
    print(rendered,end=""); return 0 if report["status"]=="passed" else 2
if __name__=="__main__": raise SystemExit(main())
