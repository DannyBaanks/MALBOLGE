import sys, json, itertools
sys.path.insert(0,'.')
import readout_gen as g
CASES=[[2],[4],[5],[6],[2,4],[2,5],[4,5],[5,9],[2,5,9],[6,9],[9,9],[4,5,9]]
rows=[]
print("barrido end-to-end: readout de 5 celdas sobre cascada mod59049")
print(" T     posiciones  esperado  obtenido      pre/shift           PASS", flush=True)
for stops in CASES:
    k=len(stops)
    r0=g.run_mod59049(k,[0]*5,[0]*5,stops=stops)
    if r0["compile_rc"]!=0:
        print(f" {r0['T']:<5} COMPILE_FAIL {r0['stderr'][:60]}", flush=True); continue
    pre=[0]*5; shift=[0]*5
    for c in range(5):
        best=None
        for p_,s_ in itertools.product((0,1),(0,1)):
            pr=list(pre); sh=list(shift); pr[c]=p_; sh[c]=s_
            rr=g.run_mod59049(k,pr,sh,stops=stops)
            if rr["compile_rc"]!=0: continue
            got=rr.get("out","").replace("Z","")
            sc=(got[c]==r0["expected"][c], len(got)==5, rr.get("match"))
            if best is None or sc>best[0]: best=(sc,p_,s_,got)
        pre[c],shift[c]=best[1],best[2]
    r=g.run_mod59049(k,pre,shift,stops=stops)
    rows.append({"stops":stops,"T":r["T"],"positions":r["expected_positions"],"expected":r["expected"],
                 "out":r["out"],"match":r["match"],"pre":pre,"shift":shift,"steps":r["steps"],
                 "hell_sha256":r["hell_sha256"]})
    print(f" {r['T']:<5} {str(r['expected_positions']):12} {r['expected']}    {r['out']!r:14} {str(pre)}/{shift}  {'PASS' if r['match'] else 'FAIL'}", flush=True)
n=sum(1 for x in rows if x["match"])
print(f"\n{n}/{len(rows)} PASS", flush=True)
json.dump({"format":"malbolge-lmao-mod59049-sweep/1",
 "pregunta":"El readout de 5 celdas lee el estado real de una cascada mod59049 en multiples T?",
 "diseno":"celdas de parada de longitud {2,4,5,6,9} (unicas que LMAO acepta como ciclo xlat2); T = producto. Calibracion greedy por cadena e independiente por T porque el layout cambia con cada T.",
 "restriccion":"T con factores 3,7,8,10 no compila: 'Forced xlat cycle doesn't exist'",
 "rows":rows,"n_match":n},open("mod59049_sweep.json","w"),indent=2,ensure_ascii=False)
