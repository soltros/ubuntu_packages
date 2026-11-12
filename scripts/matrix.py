#!/usr/bin/env python3
import json
from pathlib import Path
p=json.loads((Path(__file__).resolve().parents[1]/'packages.json').read_text())
print(json.dumps({'include':[{'package':n,'ubuntu':u,'suite':s} for n in p for u,s in [('26.10','stonking')]]}))
