"""Authorized six-pair review: pinned supplementation and 12 bounded attempts."""
from __future__ import annotations
import argparse
import concurrent.futures
import json
import os
import platform
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

import jsonschema
import requests

from code_pilot import MODELS, arr, enum, obj, STR
from import_sources import PRIVATE, RAW, ROOT, now, published_source, register, sha, source_row, write_json
from supplement_pilot import definitions

HERE = Path(__file__).resolve().parent
ORIGINAL = PRIVATE / 'pilot-20261010-v2'
AUDIT = PRIVATE / 'audit-20261010'
OUT = PRIVATE / 'six-pair-20261011'
LIMIT_SECONDS = 300
TARGET = obj({
    'temporal': enum('characteristic_capacity','temporary_state','unresolved'),
    'base_domain': STR, 'word_domain': STR,
    'domain_match': enum('same','compatible_conditional','incompatible','unresolved'),
    'shared_domain': STR, 'inapplicability_note': STR,
    'can_both': enum('yes','no','undetermined'),
    'can_neither': enum('yes','no','undetermined'),
    'opposition_reason': STR,
    'complement_scope': enum('full_reference_domain','conditional_domain','unresolved','not_complementary')})
EVIDENCE = obj({'word':STR,'sense_id':STR,'quote':STR})
ALIGNMENT = obj({'proposal_id':STR, 'base_sense_id':STR, 'word_sense_id':STR,
    'base_interpretation':STR, 'word_interpretation':STR,
    'status':enum('supported','rejected','unresolved'), 'reason':STR,
    'evidence':arr(EVIDENCE), 'targets':arr(TARGET)})
SCHEMA = obj({'pair_id':STR,'saved_alignments':arr(ALIGNMENT),
              'additional_alignments':arr(ALIGNMENT),
              'lexical_identity_note':STR,'remaining_gap':STR})

def saved_pairs():
    rows=json.loads((AUDIT/'pair-audit.json').read_text())['primary_candidates']
    result=[]
    for r in rows:
        proposals=sorted({(a['word_sense_id'],a['base_sense_id'])
            for xs in r['screens'].values() for x in xs for a in x['possible_sense_alignments']})
        pair_id=r['base']+'--'+r['word']
        result.append({'pair_id':pair_id,'base':r['base'],'word':r['word'],
            'saved_proposals':[{'proposal_id':pair_id+f':p{i+1:02}',
                               'word_sense_id':w,'base_sense_id':b}
                               for i,(w,b) in enumerate(proposals)]})
    if len(result)!=6 or sum(len(x['saved_proposals']) for x in result)!=16:
        raise ValueError('Changed authorized pair/proposal scope')
    return result

def prepare():
    commit=published_source()
    if OUT.exists(): raise FileExistsError('Preserve original six-pair preparation')
    OUT.mkdir(parents=True)
    pairs=saved_pairs(); words=sorted({x[k] for x in pairs for k in ('base','word')})
    terms={r['word']:r for r in json.loads((ORIGINAL/'terms.json').read_text())}
    sources=[]
    triggers=[{'word':w,'trigger':'relevant pair-alignment/reading evidence unresolved in previous fixed audit',
               'prior_pinned_supplement':bool(terms[w]['supplement'])} for w in words]
    write_json(OUT/'supplement-triggers.json',triggers)  # before retrieval
    requested=[w for w in words if not terms[w]['supplement']]
    params={'action':'query','prop':'revisions','rvprop':'ids|timestamp|content',
            'rvslots':'main','titles':'|'.join(requested),'format':'json','formatversion':2}
    url='https://en.wiktionary.org/w/api.php?'+urlencode(params)
    response=requests.get(url,headers={'User-Agent':'LexicalFrameReview/0.2 (academic source verification)'},timeout=45)
    response.raise_for_status()
    raw=RAW/'wiktionary-six-pair-20261011.json'
    if raw.exists(): raise FileExistsError(raw)
    raw.write_bytes(response.content)
    pages={x['title']:x for x in response.json()['query']['pages']}
    for word in requested:
        page=pages.get(word)
        if not page or 'revisions' not in page:
            sources.append({'word':word,'status':'missing','definitions':[]});continue
        revision=page['revisions'][0]
        path=RAW/'wiktionary'/f'{word}-{revision["revid"]}.json'
        write_json(path,page)
        source_url=f'https://en.wiktionary.org/w/index.php?title={word}&oldid={revision["revid"]}'
        register(source_row('lexical_wikt_'+word+'_'+str(revision['revid']),
            f'English Wiktionary {word}, pinned six-pair supplement',source_url,'',path,
            'Wiktionary text: CC BY-SA 4.0; attribution and share-alike notice',
            'Trigger recorded before retrieval: unresolved relevant pair-alignment evidence; fixed second resource, no iterative search.'))
        sources.append({'word':word,'status':'retrieved','revision_id':revision['revid'],
            'path':str(path.relative_to(ROOT)),'sha256':sha(path),'source_url':source_url,
            'definitions':definitions(page)})
    supplement={x['word']:x for x in sources}
    for p in pairs:
        p['dictionary_entries']=[]
        for word in (p['base'],p['word']):
            senses=list(terms[word]['dictionary_senses'])
            if word in supplement: senses+=supplement[word]['definitions']
            p['dictionary_entries'].append({'word':word,'dictionary_senses':
                [x for x in senses if x['pos'] in ('a','s')]})
        write_json(OUT/'packets'/f'{p["pair_id"]}.json',p)
    write_json(OUT/'supplementary-sources.json',sources)
    write_json(OUT/'schema.json',SCHEMA)
    manifest={'created_at':now(),'source_commit':commit,'pairs':len(pairs),
        'saved_proposals':16,'distinct_forms':len(words),'new_supplements':len(sources),
        'maximum_calls':12,'maximum_concurrent':2,'timeout_seconds':LIMIT_SECONDS,
        'commonness_or_ratings_input':False,'python':platform.python_version(),
        'requests_version':requests.__version__,
        'inputs':{str(p.relative_to(ROOT)):sha(p) for p in
            [ORIGINAL/'terms.json',ORIGINAL/'manifest.json',AUDIT/'pair-audit.json',raw,
             HERE/'six-pair-prompt.txt',HERE/'six_pair_review.py']},
        'packet_hashes':{p.name:sha(p) for p in sorted((OUT/'packets').glob('*.json'))}}
    write_json(OUT/'preparation.json',manifest)
    write_json(ROOT/'logs/lexical-six-pair-preparation-20261011.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('inputs','packet_hashes')}))

def validate(result, packet):
    errors=[]
    try: jsonschema.validate(result,SCHEMA)
    except jsonschema.ValidationError as exc: return ['schema: '+exc.message]
    if result['pair_id']!=packet['pair_id']: errors.append('wrong pair_id')
    expected={x['proposal_id']:x for x in packet['saved_proposals']}
    if sorted(x['proposal_id'] for x in result['saved_alignments'])!=sorted(expected):
        errors.append('saved proposal accounting')
    senses={e['word']:{s['sense_id']:s for s in e['dictionary_senses']} for e in packet['dictionary_entries']}
    ids=[]
    for row in result['saved_alignments']+result['additional_alignments']:
        ids.append(row['proposal_id'])
        old=expected.get(row['proposal_id'])
        for key,word in [('base_sense_id',packet['base']),('word_sense_id',packet['word'])]:
            if row[key] not in senses[word]: errors.append('unknown pole sense '+row[key])
            if old and row[key]!=old[key]: errors.append('mutated saved proposal '+row['proposal_id'])
            if not any(e['word']==word and e['sense_id']==row[key] for e in row['evidence']):
                errors.append('missing direct pole evidence '+row['proposal_id'])
        for e in row['evidence']:
            s=senses.get(e['word'],{}).get(e['sense_id'])
            if not s or not e['quote'] or e['quote'] not in s['gloss']:
                errors.append('invalid quote '+e['sense_id'])
        if row['status']=='rejected' and row['targets']: errors.append('rejected with targets')
        if row['status']=='supported' and not row['targets']: errors.append('supported without target')
        for t in row['targets']:
            if t['domain_match']=='incompatible' and (t['can_both']!='undetermined' or t['can_neither']!='undetermined'):
                errors.append('opposition classified across incompatible domains')
            complementary=t['can_both']=='no' and t['can_neither']=='no'
            if t['complement_scope'] in ('full_reference_domain','conditional_domain') and not complementary:
                errors.append('complement scope without complementarity')
    if len(ids)!=len(set(ids)): errors.append('duplicate proposal ids')
    return errors

def run_process(command, env, neutral, prompt, directory):
    # One CLI process per attempted call. A timeout terminates its process group,
    # preventing a CLI child from outliving the fixed five-minute allocation.
    with (directory/'stdout.txt').open('w') as out,(directory/'stderr.txt').open('w') as err:
        proc=subprocess.Popen(command,cwd=neutral,env=env,stdin=subprocess.PIPE,
            stdout=out,stderr=err,text=True,start_new_session=True)
        try:
            proc.communicate(prompt,timeout=LIMIT_SECONDS)
            return proc.returncode
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.communicate();return 'timeout'

def call(family, packet, commit):
    directory=OUT/'calls'/family/packet['pair_id']
    directory.mkdir(parents=True,exist_ok=False)
    prompt=(HERE/'six-pair-prompt.txt').read_text()+'\n'+json.dumps(packet,ensure_ascii=False,sort_keys=True)
    for licence in ('WORDNET-LICENSE.txt','WIKTIONARY-LICENSE.txt'):
        prompt+='\n'+(ORIGINAL/licence).read_text()
    (directory/'prompt.txt').write_text(prompt);write_json(directory/'schema.json',SCHEMA)
    meta={'family':family,'requested_model':MODELS[family],'pair_id':packet['pair_id'],
          'source_commit':commit,'started_at':now(),'attempt':1,'timeout_seconds':LIMIT_SECONDS,
          'prompt_sha256':sha(directory/'prompt.txt'),'schema_sha256':sha(directory/'schema.json'),
          'subscription_route':True,'commonness_or_ratings_input':False,
          'python':platform.python_version(),'platform':platform.platform(),
          'seed':'model seed unavailable; no resampling or retries'}
    tic=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='six-pair-neutral-') as neutral:
        env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
        if family=='codex':
            command=['/opt/homebrew/bin/codex','--sandbox','read-only','--ask-for-approval','never','exec',
                '--ignore-user-config','--strict-config','--ephemeral','--skip-git-repo-check','--disable','shell_tool',
                '--disable','apps','--disable','multi_agent','-c','web_search="disabled"','-c','project_doc_max_bytes=0',
                '-c','model_reasoning_effort="high"','-m',MODELS[family],'--cd',neutral,
                '--output-schema',str(directory/'schema.json'),'-o',str(directory/'answer.json'),'-']
        else:
            env.update({k:v for k,v in os.environ.items() if k in ('HOME','USER','LOGNAME','TMPDIR')})
            command=['/Users/brettreynolds/.local/bin/claude','--safe-mode','--tools','','--strict-mcp-config',
                '--mcp-config','{"mcpServers":{}}','--no-session-persistence','--setting-sources','',
                '--model',MODELS[family],'--effort','high','--output-format','stream-json','--verbose',
                '--json-schema',json.dumps(SCHEMA),'--max-budget-usd','5','-p',prompt]
        meta['command']=command if family=='codex' else command[:-1]+['<stored prompt.txt>']
        write_json(directory/'started.json',meta)
        try: meta['exit_code']=run_process(command,env,neutral,prompt if family=='codex' else None,directory)
        except Exception as exc: meta['exit_code']='launch_error';meta['error']=repr(exc)
    meta.update(completed_at=now(),elapsed_seconds=time.monotonic()-tic)
    try:
        if meta['exit_code']!=0: raise RuntimeError('CLI did not complete')
        if family=='claude':
            events=[json.loads(x) for x in (directory/'stdout.txt').read_text().splitlines() if x.strip()]
            init=next(x for x in events if x.get('type')=='system' and x.get('subtype')=='init')
            end=next(x for x in reversed(events) if x.get('type')=='result')
            meta.update(returned_model=init['model'],tools=init.get('tools'),usage=end.get('usage'),
                model_usage=end.get('modelUsage'),api_equivalent_usd=end.get('total_cost_usd'))
            if init['model']!=MODELS[family] or set(init.get('tools',[]))-{'StructuredOutput'}:
                raise ValueError('model/tools mismatch')
            result=end.get('structured_output')
            if result is None: result=json.loads(end['result'])
            write_json(directory/'answer.json',result)
        else:
            transcript=(directory/'stderr.txt').read_text()
            if 'model: '+MODELS[family] not in transcript or 'reasoning effort: high' not in transcript:
                raise ValueError('Codex model/effort mismatch')
            meta['returned_model']=MODELS[family]
            m=re.search(r'tokens used\s+([\d,]+)',transcript)
            meta['reported_tokens_used']=int(m[1].replace(',','')) if m else None
            result=json.loads((directory/'answer.json').read_text())
        meta['validation_errors']=validate(result,packet)
        meta['status']='validated' if not meta['validation_errors'] else 'needs_evidence_review'
    except Exception as exc: meta['status']='failed';meta['error']=repr(exc)
    write_json(directory/'manifest.json',meta)
    print(f'{family} {packet["pair_id"]}: {meta["status"]} {meta["elapsed_seconds"]:.1f}s',flush=True)
    return meta

def run():
    commit=published_source();prep=json.loads((OUT/'preparation.json').read_text())
    for path,digest in prep['inputs'].items():
        if sha(ROOT/path)!=digest: raise ValueError('Preparation input changed: '+path)
    packets=[]
    for name,digest in sorted(prep['packet_hashes'].items()):
        path=OUT/'packets'/name
        if sha(path)!=digest: raise ValueError('Packet changed: '+name)
        packets.append(json.loads(path.read_text()))
    # Refuse the entire run if any previous attempt exists, including partials.
    if (OUT/'calls').exists(): raise FileExistsError('Attempts already exist; no automatic rerun')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(call,f,p,commit) for p in packets for f in MODELS]
        results=[x.result() for x in futures]
    write_json(OUT/'call-summary.json',results)
    public=[{k:v for k,v in x.items() if k not in ('command','error')} for x in results]
    write_json(ROOT/'logs/lexical-six-pair-calls-20261011.json',public)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run'])
    {'prepare':prepare,'run':run}[parser.parse_args().action]()
