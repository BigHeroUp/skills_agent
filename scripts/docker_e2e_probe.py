"""Bounded end-to-end probe for the Docker gateway, API, RQ worker and database."""
from __future__ import annotations
import argparse,json,time,urllib.request,urllib.error
from uuid import uuid4

def call(base,path,method="GET",body=None,token=None):
    data=json.dumps(body).encode() if body is not None else None
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    request=urllib.request.Request(base+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=10) as response:
        raw=response.read(); return response.status,json.loads(raw) if raw else None

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--base-url",default="http://127.0.0.1:8080"); parser.add_argument("--timeout",type=int,default=90); parser.add_argument("--max-seconds",type=float,default=30); args=parser.parse_args()
    suffix=uuid4().hex[:10]; probe_credential="E2e-validation-password-26!"
    _,health=call(args.base_url,"/health/ready")
    _,first=call(args.base_url,"/api/v1/auth/register","POST",{"organization":f"E2E {suffix}","email":f"e2e-{suffix}@example.test","password":probe_credential})
    _,second=call(args.base_url,"/api/v1/auth/register","POST",{"organization":f"E2E other {suffix}","email":f"other-{suffix}@example.test","password":probe_credential})
    token=first["access_token"]; other_token=second["access_token"]
    call(args.base_url,"/api/v1/users","POST",{"email":f"tester-{suffix}@example.test","password":probe_credential,"role":"analyst"},token)
    _,tester=call(args.base_url,"/api/v1/auth/login","POST",{"tenant_id":first["identity"]["tenant_id"],"email":f"tester-{suffix}@example.test","password":probe_credential})
    tester_token=tester["access_token"]
    started=time.monotonic()
    _,submitted=call(args.base_url,"/api/v1/analyses","POST",{"description":"Somma valore per categoria","records":[{"categoria":"A","valore":10},{"categoria":"A","valore":5},{"categoria":"B","valore":7}],"source_type":"csv"},token)
    analysis_id=submitted["id"]; deadline=time.monotonic()+args.timeout; detail=None
    while time.monotonic()<deadline:
        _,detail=call(args.base_url,f"/api/v1/analyses/{analysis_id}",token=token)
        if detail["status"] in {"completed","failed","cancelled"}: break
        time.sleep(.5)
    if not detail or detail["status"]!="completed": raise SystemExit(f"analysis did not complete: {detail and detail['status']}")
    isolated=False
    try: call(args.base_url,f"/api/v1/analyses/{analysis_id}",token=other_token)
    except urllib.error.HTTPError as exc: isolated=exc.code==404
    _,feedback_response=call(args.base_url,f"/api/v1/analyses/{analysis_id}/feedback","POST",{
        "rating":3,"outcome":"partial","feedback_source":"external",
        "reason_code":"missing_evidence","expected_result":"Show the category totals and source rows",
        "notes":"Production E2E verification",
    },tester_token)
    feedback_id=feedback_response["feedback"]["id"]
    _,reviewed=call(args.base_url,f"/api/v1/feedback/{feedback_id}","PATCH",{
        "verification_status":"verified","reviewer_notes":"Reproduced by Docker E2E probe",
        "issue_reference":f"E2E-{suffix}",
    },token)
    _,feedback_list=call(args.base_url,"/api/v1/feedback?verification_status=verified",token=token)
    _,foreign_feedback_list=call(args.base_url,"/api/v1/feedback",token=other_token)
    elapsed=round(time.monotonic()-started,3)
    summary=feedback_list.get("summary") or {}
    result=detail.get("result") or {}; checks={
        "health":health.get("status")=="ready" and int(health.get("schema_version") or 0)>=5,
        "registration":True,"rq_completed":detail["status"]=="completed",
        "deterministic_result":bool(result.get("deterministic_results")),
        "product_intelligence":bool(result.get("product_intelligence")),
        "tenant_isolation":isolated,
        "verified_feedback_workflow":reviewed.get("feedback",{}).get("verification_status")=="verified" and summary.get("verified_external_total")==1 and summary.get("distinct_external_testers")==1,
        "feedback_tenant_isolation":foreign_feedback_list.get("items")==[],
        "bounded_duration":elapsed <= args.max_seconds,
    }
    print(json.dumps({"status":"passed" if all(checks.values()) else "failed","checks":checks,"analysis_id":analysis_id,"end_to_end_seconds":elapsed,"maximum_seconds":args.max_seconds}))
    return 0 if all(checks.values()) else 2
if __name__=="__main__": raise SystemExit(main())
