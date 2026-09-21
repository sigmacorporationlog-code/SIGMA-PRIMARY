"""Repeatable SIGMA HTTP benchmark suite.

Runs a small set of read-only endpoints and writes a machine-readable report.
It never claims a capacity limit; the report is evidence for qualification.
"""
from __future__ import annotations
import argparse, concurrent.futures, json, statistics, time, urllib.error, urllib.request
from pathlib import Path

def request(url: str, timeout: float):
    t=time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read(4096)
            return r.status,(time.perf_counter()-t)*1000,None
    except urllib.error.HTTPError as e:
        return e.code,(time.perf_counter()-t)*1000,str(e)
    except Exception as e:
        return 0,(time.perf_counter()-t)*1000,str(e)

def percentile(values, p):
    if not values:return 0.0
    values=sorted(values)
    return round(values[min(len(values)-1,int((len(values)-1)*p))],2)

def run_case(name,url,requests,concurrency,timeout):
    started=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        results=list(ex.map(lambda _:request(url,timeout), range(requests)))
    elapsed=time.perf_counter()-started
    lat=[x[1] for x in results]
    ok=sum(200<=x[0]<400 for x in results)
    return {"name":name,"url":url,"requests":requests,"concurrency":concurrency,
            "elapsed_seconds":round(elapsed,3),"requests_per_second":round(requests/elapsed,2) if elapsed else 0,
            "success":ok,"errors":requests-ok,"error_rate_percent":round((requests-ok)/requests*100,2),
            "latency_ms":{"p50":percentile(lat,.50),"p95":percentile(lat,.95),"p99":percentile(lat,.99),"max":round(max(lat),2) if lat else 0}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base-url',default='http://127.0.0.1:8000')
    ap.add_argument('--requests',type=int,default=200)
    ap.add_argument('--concurrency',type=int,default=20)
    ap.add_argument('--timeout',type=float,default=10)
    ap.add_argument('--output',default='benchmark_report.json')
    args=ap.parse_args()
    if args.requests<1 or args.concurrency<1: ap.error('requests et concurrency doivent être positifs')
    cases=[('live',args.base_url.rstrip('/')+'/api/health/live'),('ready',args.base_url.rstrip('/')+'/api/health/ready')]
    results=[run_case(n,u,args.requests,args.concurrency,args.timeout) for n,u in cases]
    report={'tool':'sigma-benchmark-suite','version':'4.36.0','timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cases':results}
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if all(x['errors']==0 for x in results) else 2
if __name__=='__main__': raise SystemExit(main())
