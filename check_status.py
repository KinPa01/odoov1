# -*- coding: utf-8 -*-
import json
d = json.load(open('image_progress.json','r',encoding='utf-8'))
done = d['done']
total = d['total']
pending = [p for p in d['products'] if p['status']=='pending']
failed  = [p for p in d['products'] if p['status']=='failed']
print(f"DONE={done} PENDING={len(pending)} FAILED={len(failed)} TOTAL={total}")
if failed:
    print("FAILED LIST:")
    for p in failed:
        print(f"  ID={p['id']} NAME={p['name']}")
if len(pending) <= 10:
    print("PENDING LIST:")
    for p in pending:
        print(f"  ID={p['id']} NAME={p['name']}")
