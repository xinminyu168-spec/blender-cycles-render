"""Time-budgeted P23 high-resolution validation; does not change art direction."""
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text(encoding="utf-8")
old="sc.cycles.use_denoising=True;sc.cycles.max_bounces=bounces"
assert s.count(old)==1
s=s.replace(old,old+"\nif args.quality=='high':\n    sc.cycles.time_limit=3600.0\n    print('P23: 1024 maximum samples, 3600-second per-frame sampling limit',flush=True)")
old2="qa_path=outdir/'runtime_qa.json'"
assert s.count(old2)==1
s=s.replace(old2,"qa['sampling_time_limit_seconds']=float(sc.cycles.time_limit)\nqa['samples_are_maximum']=True\n"+old2)
compile(s,str(p),'exec')
p.write_text(s,encoding="utf-8")
