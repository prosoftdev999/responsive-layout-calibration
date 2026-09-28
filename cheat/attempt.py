"""Plausible shortcut: keep the abandoned defaults, trust manifest order, and ignore the cascade."""
import json, math
from pathlib import Path
TOKENS={'standard_breakpoint':768,'wide_breakpoint':1200,'compact_pad':16,'standard_pad':24,'wide_pad':32,'content_cap':1200,'sidebar_width':280,'card_min':240,'grid_gap':20,'card_inner_pad':16,'char_factor_milli':550}
COMP=json.loads(Path('/app/data/components.json').read_text())['cards']

def q(x,n,d): return math.floor(x*n/d+0.5)*d/n
def milli(x,n,d): return int(round(q(x,n,d)*1000))
def compute(c):
    u=c['viewport_width']-c['safe_left']-c['safe_right']-c['scrollbar_width']
    if u<TOKENS['standard_breakpoint']: pad=TOKENS['compact_pad'];wide=False
    elif u<TOKENS['wide_breakpoint']: pad=TOKENS['standard_pad'];wide=False
    else: pad=TOKENS['wide_pad'];wide=True
    raw=max(1,u-2*pad);cw=min(TOKENS['content_cap'],raw);left=c['safe_left']+pad+max(0,(raw-TOKENS['content_cap'])/2)
    main=cw-(TOKENS['sidebar_width']+23 if wide else 0);cols=max(1,min(4,math.floor((main+TOKENS['grid_gap'])/(TOKENS['card_min']+TOKENS['grid_gap']))));colw=(main-(cols-1)*TOKENS['grid_gap'])/cols
    scale=c['text_scale_percent']/100;charw=15*scale*TOKENS['char_factor_milli']/1000;avail=max(80,cw-248);rows=1;used=0.0
    for chars in c['nav_item_chars']:
        w=chars*charw+20;extra=w if used==0 else 12+w
        if used and used+extra>avail+1e-9: rows+=1;used=w
        else: used+=extra
    hh=40+max(32,rows*(22*scale)+(rows-1)*6);hs=[]
    for idx in c['card_indices']:
        card=COMP[idx];uw=max(8,colw-2*TOKENS['card_inner_pad'])
        bc=max(1,math.floor(uw/(14*scale*TOKENS['char_factor_milli']/1000)));tc=max(1,math.floor(uw/(18*scale*(TOKENS['char_factor_milli']-17)/1000)))
        hs.append(2*TOKENS['card_inner_pad']+math.ceil(card['title_chars']/tc)*(23*scale)+8+math.ceil(card['body_chars']/bc)*(20*scale)+card['meta_rows']*18+10)
    n,d=c['dpr_num'],c['dpr_den']
    return {'content_left_milli':milli(left,n,d),'content_width_milli':milli(cw,n,d),'main_width_milli':milli(main,n,d),'sidebar_present':wide,'columns':cols,'column_width_milli':milli(colw,n,d),'header_rows':rows,'header_height_milli':milli(hh,n,d),'first_card_height_milli':milli(hs[0],n,d),'tallest_card_height_milli':milli(max(hs),n,d)}

def main():
    domains=json.loads(Path('/app/data/lost_values.json').read_text())['domains']
    recovered={}
    for name,d in domains.items():
        if name.startswith('base_'): continue
        vals=d['values'];recovered[name]=vals[len(vals)//2]
    order=json.loads(Path('/app/data/layer_manifest.json').read_text())['layers']
    preds=[]
    for line in Path('/app/data/render_requests.ndjson').read_text().splitlines():
        r=json.loads(line);preds.append({'request_id':r['request_id'],**compute(r['case'])})
    Path('/app/output').mkdir(parents=True,exist_ok=True)
    hp=[]
    for line in Path('/app/data/history_queries.ndjson').read_text().splitlines():
        r=json.loads(line); hp.append({'query_id':r['query_id'],**compute(r['case'])})
    fp=[]
    for line in Path('/app/data/flow_cases.ndjson').read_text().splitlines():
        r=json.loads(line)
        fp.append({'flow_id':r['flow_id'],'root_line_count':1,'probes':[{'node_id':nid,'left_milli':0,'width_milli':0} for nid in r['probes']]})
    Path('/app/output/layout_calibration.json').write_text(json.dumps({'base_tokens':TOKENS,'layer_order':order,'recovered_values':recovered,'predictions':preds,'history_predictions':hp,'flow_predictions':fp},indent=2,sort_keys=True)+'\n')
if __name__=='__main__': main()
