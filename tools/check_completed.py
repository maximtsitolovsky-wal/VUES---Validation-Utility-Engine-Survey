import json
d=json.load(open('ui/survey_routing_data.json'))
rows=d.get('rows',[])
completed=[r for r in rows if r.get('survey_complete')==True]

cctv = len([r for r in completed if r.get('survey_type')=='CCTV'])
fa = len([r for r in completed if r.get('survey_type')=='FA/INTRUSION'])
both = len([r for r in completed if r.get('survey_type')=='BOTH'])
review = len([r for r in completed if r.get('survey_type') in ['REVIEW','NONE',None,'']])

print('COMPLETED BY TYPE:')
print(f'  CCTV: {cctv}')
print(f'  FA/Intrusion: {fa}')
print(f'  Both: {both}')
print(f'  Review/None: {review}')
print(f'  TOTAL: {cctv+fa+both+review}')
