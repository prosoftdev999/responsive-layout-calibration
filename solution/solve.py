#!/usr/bin/env python3
import ast, itertools, json, math
from fractions import Fraction
from pathlib import Path

DATA=Path('/app/data')
OUT=Path('/app/output/layout_calibration.json')
TOKENS=('standard_breakpoint','wide_breakpoint','compact_pad','standard_pad','wide_pad','content_cap','sidebar_width','card_min','grid_gap','card_inner_pad','char_factor_milli')
NODE_ORDER=('root','app','shell','cards')

def ndjson(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
COMP=json.loads((DATA/'components.json').read_text())['cards']
RULES=ndjson(DATA/'cascade_rules.ndjson')
NODES=json.loads((DATA/'style_nodes.json').read_text())['nodes']
BASE_NODES={n['node_id']:n for n in NODES}; PARENT={n['node_id']:n['parent_id'] for n in NODES}
DOMAINS=json.loads((DATA/'lost_values.json').read_text())['domains']
LAYERS=json.loads((DATA/'layer_manifest.json').read_text())['layers']

def q(x,n,d): return math.floor(x*n/d+0.5)*d/n
def milli(x,n,d): return int(round(q(x,n,d)*1000))
def layout(c,t):
    u=c['viewport_width']-c['safe_left']-c['safe_right']-c['scrollbar_width']
    if u<t['standard_breakpoint']: pad=t['compact_pad']; wide=False
    elif u<t['wide_breakpoint']: pad=t['standard_pad']; wide=False
    else: pad=t['wide_pad']; wide=True
    raw=max(1,u-2*pad); cw=min(t['content_cap'],raw); left=c['safe_left']+pad+max(0,(raw-t['content_cap'])/2)
    main=cw-(t['sidebar_width']+23 if wide else 0)
    cols=max(1,min(4,math.floor((main+t['grid_gap'])/(t['card_min']+t['grid_gap'])))); colw=(main-(cols-1)*t['grid_gap'])/cols
    scale=c['text_scale_percent']/100; charw=15*scale*t['char_factor_milli']/1000; avail=max(80,cw-248); rows=1; used=0.0
    for chars in c['nav_item_chars']:
        w=chars*charw+20; extra=w if used==0 else 12+w
        if used and used+extra>avail+1e-9: rows+=1; used=w
        else: used+=extra
    hh=40+max(32,rows*(22*scale)+(rows-1)*6); hs=[]
    for idx in c['card_indices']:
        card=COMP[idx]; inner=t['card_inner_pad']; uw=max(8,colw-2*inner)
        bc=max(1,math.floor(uw/(14*scale*t['char_factor_milli']/1000)))
        tc=max(1,math.floor(uw/(18*scale*(t['char_factor_milli']-17)/1000)))
        hs.append(2*inner+math.ceil(card['title_chars']/tc)*(23*scale)+8+math.ceil(card['body_chars']/bc)*(20*scale)+card['meta_rows']*18+10)
    n,d=c['dpr_num'],c['dpr_den']
    return {'content_left_milli':milli(left,n,d),'content_width_milli':milli(cw,n,d),'main_width_milli':milli(main,n,d),'sidebar_present':wide,'columns':cols,'column_width_milli':milli(colw,n,d),'header_rows':rows,'header_height_milli':milli(hh,n,d),'first_card_height_milli':milli(hs[0],n,d),'tallest_card_height_milli':milli(max(hs),n,d)}

def domain(name):
    d=DOMAINS[name]
    return d['values'] if 'values' in d else range(d['min'],d['max']+1)

def stub():
    tree=ast.parse(Path('/workspace/calibrate_layout.py').read_text())
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TOKENS' for t in n.targets):
            x=ast.literal_eval(n.value)
            if set(x)==set(TOKENS): return {k:int(x[k]) for k in TOKENS}
    raise RuntimeError('missing defaults stub')

def mismatch(rows,t):
    bad=0
    for r in rows:
        got=layout(r['case'],t)
        bad+=sum(got[k]!=v for k,v in r['measurements'].items())
    return bad

def recover_base():
    rows=ndjson(DATA/'calibration_samples.ndjson')+ndjson(DATA/'identification_samples.ndjson')
    t=stub()
    for _ in range(8):
        changed=False
        for key in TOKENS:
            old=t[key]; best=None; winners=[]
            for v in domain('base_'+key):
                t[key]=v; s=mismatch(rows,t)
                if best is None or s<best: best=s; winners=[v]
                elif s==best: winners.append(v)
            nv=min(winners,key=lambda v:(abs(v-old),v));t[key]=nv;changed|=(nv!=old)
        if mismatch(rows,t)==0: break
        if not changed: raise RuntimeError('base calibration stalled')
    if mismatch(rows,t): raise RuntimeError('base calibration did not fit')
    # Every shipped domain is re-scanned at the zero-fit point. Each token must be individually pinned.
    for key in TOKENS:
        keep=t[key]; zeros=[]
        for v in domain('base_'+key):
            t[key]=v
            if mismatch(rows,t)==0: zeros.append(v)
        t[key]=keep
        if zeros!=[keep]: raise RuntimeError(f'ambiguous base {key}: {zeros[:20]}')
    return t

# selector / cascade ---------------------------------------------------------
def parse_comp(s):
    if s==':root': return (True,(),())
    cls=[];attrs=[];i=0
    while i<len(s):
        if s[i]=='.':
            j=i+1
            while j<len(s) and s[j] not in '.[': j+=1
            cls.append(s[i+1:j]);i=j
        elif s[i]=='[':
            j=s.index(']',i);a,b=s[i+1:j].split('=',1);attrs.append((a,b.strip('"')));i=j+1
        else: raise ValueError(s)
    return (False,tuple(cls),tuple(attrs))
for r in RULES:
    r['_parts']=tuple(parse_comp(x) for x in r['selector'].split())
    r['_spec']=sum(10 if x==':root' else 10*(x.count('.')+x.count('[')) for x in r['selector'].split())

def run_nodes(ctx):
    m={k:{'node_id':v['node_id'],'classes':set(v['classes']),'attrs':dict(v['attrs'])} for k,v in BASE_NODES.items()}
    m['app']['attrs'].update({'data-density':ctx['density'],'data-tenant':ctx['tenant']});m['shell']['attrs']['data-mode']=ctx['mode'];m['cards']['attrs']['data-exp']=ctx['exp']
    if ctx['direction']=='rtl':m['root']['classes'].add('rtl')
    return m

def cm(c,node):
    root,cls,attrs=c
    return (not root or node['node_id']=='root') and all(x in node['classes'] for x in cls) and all(node['attrs'].get(a)==b for a,b in attrs)
def selmatch(r,nid,m):
    parts=r['_parts'];cur=nid
    if not cm(parts[-1],m[cur]):return False
    for part in reversed(parts[:-1]):
        cur=PARENT[cur]
        while cur is not None and not cm(part,m[cur]):cur=PARENT[cur]
        if cur is None:return False
    return True
def cond(r,c):
    w=r['when']
    if 'build_in' in w and c['build'] not in w['build_in']:return False
    if 'min_viewport' in w and c['viewport_width']<w['min_viewport']:return False
    if 'max_viewport' in w and c['viewport_width']>w['max_viewport']:return False
    if 'min_container' in w and c['container_width']<w['min_container']:return False
    if 'max_container' in w and c['container_width']>w['max_container']:return False
    return True
def applicable(ctx):
    m=run_nodes(ctx);out={n:[] for n in NODE_ORDER}
    for nid in NODE_ORDER:
        for r in RULES:
            if cond(r,ctx) and selmatch(r,nid,m):
                for d in r['declarations']:out[nid].append((r['layer'],r['_spec'],r['source_order'],d['important'],d['property'],d['value']))
    return out

def raw_cascade(per,order,wrong_important=False,ignore_specificity=False,no_inherit=False):
    rank={x:i for i,x in enumerate(order)};computed={}
    for nid in NODE_ORDER:
        out={} if no_inherit or PARENT[nid] is None else dict(computed[PARENT[nid]]);wins={}
        for lay,sp,src,imp,p,v in per[nid]:
            layer_key=rank[lay] if (not imp or wrong_important) else -rank[lay]
            key=(int(imp),layer_key,0 if ignore_specificity else sp,src)
            if p not in wins or key>wins[p][0]:wins[p]=(key,v)
        out.update({p:v for p,(_,v) in wins.items()});computed[nid]=out
    return computed['cards']
def deps(raw,p,trail=()):
    if p not in raw:return set()
    v=raw[p]
    if isinstance(v,int):return set()
    if isinstance(v,str) and v.startswith('lost:'):return {v[5:]}
    if isinstance(v,dict):
        if p in trail:raise RuntimeError('var cycle')
        return deps(raw,v['var'],trail+(p,)) if v['var'] in raw else set()
    raise ValueError(v)
def effective(per,order,values,**kw):
    raw=raw_cascade(per,order,**kw);memo={}
    def resolve(p,trail=()):
        if p in memo:return memo[p]
        if p not in raw:raise KeyError(p)
        v=raw[p]
        if isinstance(v,int):x=v
        elif isinstance(v,str) and v.startswith('lost:'):x=values[v[5:]]
        elif isinstance(v,dict):
            if p in trail:raise RuntimeError('var cycle')
            x=resolve(v['var'],trail+(p,)) if v['var'] in raw else v['fallback']
        else:raise ValueError(v)
        memo[p]=x;return x
    return {k:int(resolve('--'+k)) for k in TOKENS}
def row_bad(s,per,order,values,**kw):
    got=layout(s['case'],effective(per,order,values,**kw))
    return sum(got[k]!=v for k,v in s['measurements'].items())

def recover_order(samples,basevals):
    prepared=[(s,applicable(s['context'])) for s in samples];clean=[]
    for s,per in prepared:
        nonbase=set()
        for ds in per.values():
            for *_,v in ds:
                if isinstance(v,str) and v.startswith('lost:') and not v[5:].startswith('base_'):nonbase.add(v[5:])
        if not nonbase:clean.append((s,per))
    best=None;wins=[]
    for order in itertools.permutations(LAYERS):
        bad=0
        for s,per in clean:
            bad+=row_bad(s,per,order,basevals)
            if best is not None and bad>best:break
        if best is None or bad<best:best=bad;wins=[order]
        elif bad==best:wins.append(order)
    if best!=0 or len(wins)!=1:raise RuntimeError(f'layer order ambiguous: best={best}, survivors={len(wins)}')
    return list(wins[0]),prepared

def recover_overrides(prepared,order,values):
    names=[x for x in DOMAINS if not x.startswith('base_')];found={}
    for name in names:
        useful=[]
        for s,per in prepared:
            raw=raw_cascade(per,order);d=set()
            for k in TOKENS:d|={x for x in deps(raw,'--'+k) if not x.startswith('base_')}
            if d=={name}:useful.append((s,per))
        if not useful:raise RuntimeError(f'no isolated evidence for {name}')
        winners=[]
        for v in domain(name):
            trial=dict(values);trial.update(found);trial[name]=v
            if sum(row_bad(s,per,order,trial) for s,per in useful)==0:winners.append(v)
        if len(winners)!=1:raise RuntimeError(f'ambiguous {name}: {winners}')
        found[name]=winners[0]
    return found


# incremental history ---------------------------------------------------------
HSESS={x["session_id"]:x for x in json.loads((DATA/"history_sessions.json").read_text())["sessions"]}
HEVENTS={}
for e in ndjson(DATA/"history_events.ndjson"):
    HEVENTS.setdefault(e["session_id"],[]).append(e)
for v in HEVENTS.values(): v.sort(key=lambda x:x["seq"])
HSHEETS={x["sheet_id"]:x for x in json.loads((DATA/"history_sheets.json").read_text())["sheets"]}
CAT_FIELDS=("density","tenant","mode","exp","direction","build")

def _apply_hist_op(state,e):
    if e["op"]=="set_context":
        state["context"][e["field"]]=e["value"]
    elif e["op"]=="adopt":
        sh=e["sheet_id"]
        if sh not in state["sheets"]: state["sheets"].append(sh)
    elif e["op"]=="remove":
        sh=e["sheet_id"]
        if sh in state["sheets"]: state["sheets"].remove(sh)
    elif e["op"]=="move":
        sh=e["sheet_id"]
        if sh in state["sheets"]:
            state["sheets"].remove(sh); idx=max(0,min(int(e["index"]),len(state["sheets"]))); state["sheets"].insert(idx,sh)
    else: raise RuntimeError(e["op"])

def history_state(session_id,seq,memo):
    key=(session_id,seq)
    if key in memo: return copy_state(memo[key])
    meta=HSESS[session_id]
    if meta["parent_session"] is None:
        state={"context":dict(meta["base_context"]),"sheets":[]}
    else:
        state=history_state(meta["parent_session"],int(meta["fork_seq"]),memo)
    batch=None; buffered=[]
    for e in HEVENTS.get(session_id,[]):
        if e["seq"]>seq: break
        op=e["op"]
        if op=="begin": batch=e["batch_id"]; buffered=[]
        elif op=="commit":
            if batch!=e["batch_id"]: raise RuntimeError("bad batch commit")
            for b in buffered: _apply_hist_op(state,b)
            batch=None; buffered=[]
        elif op=="abort":
            if batch!=e["batch_id"]: raise RuntimeError("bad batch abort")
            batch=None; buffered=[]
        elif batch is not None: buffered.append(e)
        else: _apply_hist_op(state,e)
    memo[key]=copy_state(state); return state

def copy_state(s): return {"context":dict(s["context"]),"sheets":list(s["sheets"])}

def applicable_history(ctx,sheet_ids):
    per=applicable(ctx)
    # adopted sheets are later author rules; list order is their source order
    for i,shid in enumerate(sheet_ids):
        sh=HSHEETS[shid]
        for d in sh["declarations"]:
            per["cards"].append((sh["layer"],10,10000+i,d["important"],d["property"],d["value"]))
    return per

def history_predictions(order,values):
    memo={}; out=[]
    for qrow in ndjson(DATA/"history_queries.ndjson"):
        st=history_state(qrow["session_id"],int(qrow["seq"]),memo)
        ctx=dict(qrow["seed_context"]); ctx.update(st["context"])
        toks=effective(applicable_history(ctx,st["sheets"]),order,values)
        out.append({"query_id":qrow["query_id"],**layout(qrow["case"],toks)})
    return out



# nested flex-flow reconstruction ---------------------------------------------
FLOW_CASES = ndjson(DATA/'flow_cases.ndjson')
_RENDER_BY_ID = {r['request_id']: r for r in ndjson(DATA/'render_requests.ndjson')}
_HQUERY_BY_ID = {r['query_id']: r for r in ndjson(DATA/'history_queries.ndjson')}


def _F(value):
    return value if isinstance(value, Fraction) else Fraction(value)


def _painted_milli_exact(css_px, dpr_num, dpr_den):
    """Apply the documented device-pixel half-up rule without float drift."""
    device = _F(css_px) * dpr_num / dpr_den
    device_px = (device + Fraction(1, 2)).numerator // (device + Fraction(1, 2)).denominator
    painted_milli = Fraction(device_px * dpr_den * 1000, dpr_num)
    return int(round(painted_milli))


def _unrounded_main(c,t):
    usable=c['viewport_width']-c['safe_left']-c['safe_right']-c['scrollbar_width']
    if usable<t['standard_breakpoint']:
        pad=t['compact_pad']; wide=False
    elif usable<t['wide_breakpoint']:
        pad=t['standard_pad']; wide=False
    else:
        pad=t['wide_pad']; wide=True
    raw=max(1,usable-2*pad)
    content=min(t['content_cap'],raw)
    return content-(t['sidebar_width']+23 if wide else 0)


def _source_state(source, order, values, hist_memo):
    if source['kind']=='render':
        row=_RENDER_BY_ID[source['id']]
        ctx=dict(row['context'])
        toks=effective(applicable(ctx),order,values)
        return row['case'],ctx,toks
    if source['kind']=='history':
        row=_HQUERY_BY_ID[source['id']]
        st=history_state(row['session_id'],int(row['seq']),hist_memo)
        ctx=dict(row['seed_context']);ctx.update(st['context'])
        toks=effective(applicable_history(ctx,st['sheets']),order,values)
        return row['case'],ctx,toks
    raise RuntimeError(f"unknown flow source {source}")


def _limit_size(x, lo, hi):
    if x < lo: x=lo
    if hi is not None and x > hi: x=hi
    return x


def _intrinsic(node, mode, scale, char_factor):
    if node['kind']=='leaf':
        chars=node['label_chars'] if mode=='max' else node['longest_word_chars']
        return Fraction(chars*15*char_factor,1000)*scale + node['chrome_px']
    if node['kind']!='group':
        raise RuntimeError(node['kind'])
    vals=[]
    for child in node['children']:
        item=child['item']
        b=item['basis']
        if b['kind']=='px': base=Fraction(b['value'])
        elif b['kind'] in ('auto','percent'): base=_intrinsic(child,mode,scale,char_factor)
        else: raise RuntimeError(b['kind'])
        mn=item['min']
        lo=_intrinsic(child,'min',scale,char_factor) if mn['kind']=='auto' else Fraction(mn['value'])
        hi=None if item['max'] is None else Fraction(item['max'])
        v=_limit_size(base,lo,hi)
        if item['margin_start']!='auto': v+=Fraction(item['margin_start'])
        if item['margin_end']!='auto': v+=Fraction(item['margin_end'])
        vals.append(v)
    gaps=Fraction(max(0,len(vals)-1)*node['gap'])
    pads=Fraction(node['padding_left']+node['padding_right'])
    if not vals: return pads
    if mode=='min' and node['wrap']:
        return pads+max(vals)
    return pads+sum(vals,Fraction(0))+gaps


def _item_metrics(child, inner, scale, char_factor):
    item=child['item']; b=item['basis']
    if b['kind']=='auto': base=_intrinsic(child,'max',scale,char_factor)
    elif b['kind']=='px': base=Fraction(b['value'])
    elif b['kind']=='percent': base=inner*Fraction(b['milli'],1000)
    else: raise RuntimeError(b['kind'])
    mn=item['min']
    lo=_intrinsic(child,'min',scale,char_factor) if mn['kind']=='auto' else Fraction(mn['value'])
    hi=None if item['max'] is None else Fraction(item['max'])
    hyp=_limit_size(base,lo,hi)
    ms=Fraction(0) if item['margin_start']=='auto' else Fraction(item['margin_start'])
    me=Fraction(0) if item['margin_end']=='auto' else Fraction(item['margin_end'])
    return {'node':child,'item':item,'base':base,'lo':lo,'hi':hi,'hyp':hyp,'ms':ms,'me':me,
            'auto_start':item['margin_start']=='auto','auto_end':item['margin_end']=='auto'}


def _collect_lines(node, inner, scale, char_factor):
    ordered=[c for _,c in sorted(enumerate(node['children']),key=lambda z:(z[1]['item']['order'],z[0]))]
    metrics=[_item_metrics(c,inner,scale,char_factor) for c in ordered]
    if not node['wrap'] or not metrics: return [metrics]
    lines=[];cur=[];used=Fraction(0)
    for m in metrics:
        outer=m['hyp']+m['ms']+m['me']
        extra=outer if not cur else Fraction(node['gap'])+outer
        if cur and used+extra>inner:
            lines.append(cur);cur=[m];used=outer
        else:
            cur.append(m);used+=extra
    if cur: lines.append(cur)
    return lines


def _flex_line(line, inner, base_gap):
    if not line: return []
    gap_total=Fraction(base_gap*max(0,len(line)-1))
    fixed_margins=sum((m['ms']+m['me'] for m in line),Fraction(0))
    use_grow=(sum((m['hyp']+m['ms']+m['me'] for m in line),Fraction(0))+gap_total) < inner
    for m in line:
        m['target']=m['base'];m['frozen']=False
        factor=m['item']['grow'] if use_grow else m['item']['shrink']
        if factor==0 or (use_grow and m['base']>m['hyp']) or ((not use_grow) and m['base']<m['hyp']):
            m['target']=m['hyp'];m['frozen']=True
    guard=0
    while any(not m['frozen'] for m in line):
        guard+=1
        if guard>64: raise RuntimeError('flex freeze loop did not converge')
        used=gap_total+fixed_margins
        for m in line: used += m['target'] if m['frozen'] else m['base']
        free=inner-used
        unf=[m for m in line if not m['frozen']]
        weights=[]
        for m in unf:
            if use_grow: w=Fraction(m['item']['grow'])
            else: w=Fraction(m['item']['shrink'])*m['base']
            weights.append(w)
        total=sum(weights,Fraction(0))
        for m,w in zip(unf,weights):
            tentative=m['base']+(free*w/total if total else Fraction(0))
            clamped=_limit_size(tentative,m['lo'],m['hi'])
            m['_tentative']=tentative;m['_next']=clamped;m['_violation']=clamped-tentative
        tv=sum((m['_violation'] for m in unf),Fraction(0))
        if tv==0:
            freeze=unf
        elif tv>0:
            freeze=[m for m in unf if m['_violation']>0]
        else:
            freeze=[m for m in unf if m['_violation']<0]
        if not freeze:
            freeze=unf
        for m in unf: m['target']=m['_next']
        for m in freeze: m['frozen']=True
    return line


def _justify(node, line, inner):
    n=len(line)
    if not n: return Fraction(0),Fraction(0)
    gaps=Fraction(node['gap']*max(0,n-1))
    used=gaps+sum((m['target']+m['ms']+m['me'] for m in line),Fraction(0))
    free=inner-used
    auto_slots=sum(int(m['auto_start'])+int(m['auto_end']) for m in line)
    auto_share=(free/auto_slots) if free>0 and auto_slots else Fraction(0)
    if auto_share:
        for m in line:
            if m['auto_start']: m['ms']=auto_share
            if m['auto_end']: m['me']=auto_share
        free=Fraction(0)
    if free<0: free=Fraction(0)
    j=node['justify_content']
    if j=='start': return Fraction(0),Fraction(0)
    if j=='end': return free,Fraction(0)
    if j=='center': return free/2,Fraction(0)
    if j=='space-between': return (Fraction(0), free/(n-1)) if n>1 else (Fraction(0),Fraction(0))
    if j=='space-around': return free/(2*n), free/n
    if j=='space-evenly': return free/(n+1), free/(n+1)
    raise RuntimeError(j)


def _layout_flow_group(node, left, width, inherited_dir, scale, char_factor, dpr_num, dpr_den, probes, out, is_root=False):
    left=_F(left);width=_F(width)
    direction=node['direction_override'] or inherited_dir
    inner_left=left+node['padding_left'];inner=max(Fraction(0),width-node['padding_left']-node['padding_right'])
    lines=_collect_lines(node,inner,scale,char_factor)
    axis_lr=(direction=='ltr') ^ (node['flex_direction']=='row-reverse')
    for line in lines:
        _flex_line(line,inner,node['gap'])
        offset,extra_gap=_justify(node,line,inner)
        cursor=offset
        for idx,m in enumerate(line):
            logical=cursor+m['ms']
            phys=inner_left+logical if axis_lr else inner_left+inner-logical-m['target']
            child=m['node']; nid=child['node_id']
            if nid in probes:
                out[nid]={'node_id':nid,'left_milli':_painted_milli_exact(phys,dpr_num,dpr_den),'width_milli':_painted_milli_exact(m['target'],dpr_num,dpr_den)}
            if child['kind']=='group':
                _layout_flow_group(child,phys,m['target'],direction,scale,char_factor,dpr_num,dpr_den,probes,out,False)
            cursor=logical+m['target']+m['me']
            if idx+1<len(line): cursor+=node['gap']+extra_gap
    return len(lines)


def flow_predictions(order, values):
    hist_memo={}; ans=[]
    for row in FLOW_CASES:
        case,ctx,toks=_source_state(row['source'],order,values,hist_memo)
        width=Fraction(_unrounded_main(case,toks))
        scale=Fraction(case['text_scale_percent'],100)
        probes=set(row['probes']); got={}
        line_count=_layout_flow_group(row['tree'],Fraction(0),width,ctx['direction'],scale,toks['char_factor_milli'],case['dpr_num'],case['dpr_den'],probes,got,True)
        if set(got)!=probes: raise RuntimeError(f"missing flow probes for {row['flow_id']}")
        ans.append({'flow_id':row['flow_id'],'root_line_count':line_count,'probes':[got[k] for k in sorted(got)]})
    return ans

def main():
    base=recover_base();values={'base_'+k:v for k,v in base.items()};samples=ndjson(DATA/'cascade_samples.ndjson')
    order,prepared=recover_order(samples,values);found=recover_overrides(prepared,order,values);values.update(found)
    bad=sum(row_bad(s,per,order,values) for s,per in prepared)
    if bad:raise RuntimeError(f'{bad} cascade measurements still disagree')
    predictions=[]
    for r in ndjson(DATA/'render_requests.ndjson'):
        predictions.append({'request_id':r['request_id'],**layout(r['case'],effective(applicable(r['context']),order,values))})
    hp=history_predictions(order,values)
    fp=flow_predictions(order,values)
    payload={'base_tokens':base,'layer_order':order,'recovered_values':{k:found[k] for k in sorted(found)},'predictions':predictions,'history_predictions':hp,'flow_predictions':fp}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
