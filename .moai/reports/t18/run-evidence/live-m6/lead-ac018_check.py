import json,os,sys,hashlib
R,JOBDIR=sys.argv[1],sys.argv[2]
L=lambda p: json.load(open(p,encoding="utf-8"))
sha=lambda p: hashlib.sha256(open(p,"rb").read()).hexdigest()
res={}
job=L(os.path.join(JOBDIR,"job.json"))
print("job.json keys:",sorted(job.keys())[:20])
print("1. status:",job.get("status"),"| delivery_status:",job.get("delivery_status"),"| exit/reason:",job.get("reason") or job.get("end_reason"))
idx=L(R+"/screens/index.json")
bad=[]; n=0
for v in idx["viewports"]:
    for t in v["tiles"]:
        n+=1; p=R+"/screens/"+t["file"]
        if not os.path.exists(p) or sha(p)!=t["sha256"]: bad.append(t["file"])
print("2. outcome:",idx["outcome"],"| viewports:",[(v["name"],v["status"],len(v["tiles"])) for v in idx["viewports"]],"| tiles",n,"| missing/sha-mismatch:",bad)
rc=L(R+"/review/receipt.json"); s=rc["screens"]
print("3. tiles_expected",len(s["tiles_expected"]),"tiles_read",len(s["tiles_read"]),"| read covers expected:",set(s["tiles_expected"])<=set(s["tiles_read"]),
      "| exit_code",rc["process"]["exit_code"],"timed_out",rc["process"]["timed_out"],"| draft_unchanged",rc["draft_unchanged"],
      "| judged_writes",rc.get("judged_writes",rc.get("writes",{}).get("judged") if isinstance(rc.get("writes"),dict) else "n/a"),
      "| snapshot_start==end:",s["snapshot_start"]==s["snapshot_end"])
print("   receipt: visual_admissible",rc.get("visual_admissible"),"| reasons",rc.get("reasons"))
ar=L(R+"/audit-review.json")
ck=ar["checks"]
print("4. audit-review checks:",{k:(v["status"],len(v.get("evidence","")>"" and v["evidence"])) for k,v in ck.items()},"| mode",ar.get("mode"),"| issues",len(ar.get("issues",[])))
print("   visual evidence starts with:",ck["visual"]["evidence"][:30].replace("\n"," "))
fa=L(R+"/review/delivery-audit.json")
print("5. review/delivery-audit: decision",fa.get("decision"),"| delivery_allowed",fa.get("delivery_allowed"))
print("   final dir exists:",os.path.isdir(R+"/final"))
fmt={"AUDIT_INPUT_VERSION","AUDIT_PREVIEW_VERSION","AUDIT_TIME","AUDIT_MODE"}
codes=sorted({x["code"] for x in fa.get("findings",[]) if isinstance(x,dict)})
print("   audit codes (server's own run):",codes)
print("   format-code intersection:",sorted(fmt&set(codes)))
