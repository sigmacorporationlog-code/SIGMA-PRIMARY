from __future__ import annotations
import json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path.cwd()
V441 = "tests/test_v441_update_agent.py::test_update_manifest_generator"
PYTEST = [sys.executable, "-m", "pytest"]

def run(cmd, timeout=180):
    t=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
        return {"exit_code":p.returncode,"duration":time.monotonic()-t,
                "stdout":p.stdout,"stderr":p.stderr,"timed_out":False}
    except subprocess.TimeoutExpired as e:
        return {"exit_code":None,"duration":time.monotonic()-t,
                "stdout":str(e.stdout or "")[-12000:],"stderr":str(e.stderr or "")[-12000:],
                "timed_out":True}

def collect():
    r=run(PYTEST+["--collect-only","-q","--disable-warnings"])
    if r["exit_code"] != 0:
        raise SystemExit("COLLECT FAIL\n"+r["stdout"]+r["stderr"])
    ids=[]
    for line in (r["stdout"]+"\n"+r["stderr"]).splitlines():
        s=line.strip().replace("\\","/")
        m=re.search(r"(tests/[^\s]+::[^\s]+)", s)
        if m:
            ids.append(m.group(1))
    if V441 not in ids:
        direct=run(PYTEST+["--collect-only","-q","tests/test_v441_update_agent.py"])
        print("DIRECT_V441_COLLECTION_STDOUT:\n"+direct["stdout"]+"\nDIRECT_V441_COLLECTION_STDERR:\n"+direct["stderr"])
        raise SystemExit("V441 not found in collection")
    return ids

def one(ids,label):
    r=run(PYTEST+["-q","-s","--disable-warnings"]+ids)
    status="TIMEOUT" if r["timed_out"] else ("PASS" if r["exit_code"]==0 else "FAIL")
    return {"label":label,"count":len(ids),"status":status,**r}

def vnum(x):
    m=re.search(r"test_v(\d+)",Path(x.split("::",1)[0]).name)
    return int(m.group(1)) if m else None

def static_map(pre):
    lines=["# V441 predecessor test map","",
           "Reference: 7c557f36432f416534dd56b92bc37685b3d90f88","",
           "|Order|Test|Module|Classe|Fixtures définies|Risques statiques|",
           "|---:|---|---|---|---|---|"]
    risk_words=["subprocess","Popen","os.system","cmd.exe","powershell","threading","Thread(","ThreadPoolExecutor","ProcessPoolExecutor","asyncio","os.environ","monkeypatch.setenv","monkeypatch.delenv","os.chdir","cwd=","env=","tempfile","NamedTemporaryFile","TemporaryDirectory","unlink","rmtree","socket","requests","urllib","Lock(","RLock(","Event(","Semaphore(","Queue("]
    for i,x in enumerate(pre+[V441],1):
        fn=x.split("::",1)[0]
        p=Path(fn); txt=p.read_text(encoding="utf-8",errors="replace")
        parts=x.split("::")
        fixtures=re.findall(r"@pytest\\.fixture[^\\n]*\\n(?:def|async def)\\s+([A-Za-z_]\\w*)",txt)
        risks=[w for w in risk_words if w in txt]
        cls=parts[1] if len(parts)>2 else ""
        test=parts[-1]
        lines.append(f"|{i}|{test}|{fn}|{cls}|{', '.join(fixtures) or '—'}|{', '.join(risks) or '—'}|")
    c=Path("tests/conftest.py")
    if c.exists():
        ct=c.read_text(encoding="utf-8",errors="replace")
        hooks=re.findall(r"def\\s+(pytest_(?:sessionstart|sessionfinish|runtest_setup|runtest_teardown|configure|unconfigure))",ct)
        lines += ["","","## conftest.py hooks",", ".join(hooks) or "aucun détecté"]
    Path("V441_PREDECESSOR_TEST_MAP.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

def main():
    ids=collect()
    pre=ids[:ids.index(V441)]
    print(f"COLLECTION={len(ids)} PREDECESSORS={len(pre)} V441_ORDER={len(pre)+1}")
    static_map(pre)
    results=[]
    for i in range(3):
        results.append(one([V441],f"V441-alone-{i+1}"))
    v431_440=[x for x in pre if 431 <= (vnum(x) or -1) <= 440]
    results.append(one(v431_440+[V441],"V431-V440-plus-V441"))
    active=pre[:]
    bisect=[]
    while len(active)>1:
        mid=len(active)//2
        left,right=active[:mid],active[mid:]
        a=one(left+[V441],f"bisect-left-{len(active)}")
        b=one(right+[V441],f"bisect-right-{len(active)}")
        bisect += [a,b]
        failing=[g for g,o in ((left,a),(right,b)) if o["status"]=="FAIL"]
        if len(failing)==1:
            active=failing[0]
            continue
        if len(failing)==2:
            active=min(failing,key=len)
            continue
        u=one(active+[V441],"interaction-union")
        bisect.append(u)
        break
    results += bisect
    results += [one(active+[V441],"candidate-repeat-1"),one(active+[V441],"candidate-repeat-2")]
    report={"python":sys.version,"pytest":run(PYTEST+["--version"],30),
            "v441":V441,"predecessor_count":len(pre),"predecessors":pre,
            "v431_440_count":len(v431_440),"candidate_count":len(active),
            "candidate":active,"results":results}
    Path("V441_BISECT_RESULTS.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"candidate_count":len(active),"candidate":active,
                      "results":[(r["label"],r["status"],r["count"]) for r in results]},indent=2))

if __name__=="__main__":
    main()
