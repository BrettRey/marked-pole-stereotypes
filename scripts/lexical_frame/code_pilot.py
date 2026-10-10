"""Frozen, tool-free independent coding of the authorized 40-term pilot."""
from __future__ import annotations
import argparse
import concurrent.futures
import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

from import_sources import PRIVATE, ROOT, now, published_source, sha, write_json

HERE = Path(__file__).resolve().parent
PACKET = PRIVATE / 'pilot-20261010-v2'
OUT = PRIVATE / 'coding-20261010-v1'
MODELS = {'codex': 'gpt-6.1-sol', 'claude': 'claude-sonnet-4-6'}

def obj(props):
    return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
def arr(item): return {'type':'array','items':item}
STR = {'type':'string'}
def enum(*xs): return {'type':'string','enum':list(xs)}
SENSE = obj({'sense_id':STR,'status':enum('eligible','ineligible','unresolved'),
 'domain':enum('personality','interpersonal','psychological_state','psychological_capacity','psychological_disposition','physical','object','membership','institutional_status','record','other','unresolved'),
 'temporal':enum('stable','temporary','both','not_applicable','unresolved'),'evidence_quote':STR,'reason':STR})
WORD_SCHEMA = obj({'words':arr(obj({'word':STR,'word_status':enum('eligible','ineligible','unresolved'),
 'coverage_note':STR,'senses':arr(SENSE),'interpretation_groups':arr(obj({'label':STR,'sense_ids':arr(STR)})), 'boundary_note':STR}))})
PAIR_SCHEMA = obj({'apparent_negative_words_reviewed':arr(STR),'analyses':arr(obj({
 'word':STR,'immediate_base':STR,'affix':STR,'relation_status':enum('supported','rejected','unresolved'),
 'primary_adjective_pair':enum('yes','no','unresolved'),'reason':STR,
 'evidence':arr(obj({'word':STR,'sense_id':STR,'quote':STR})),
 'possible_sense_alignments':arr(obj({'word_sense_id':STR,'base_sense_id':STR,'reading':enum('contrary','complementary','unresolved'),'reason':STR}))}))})

def stripped(records, pair=False):
    return [{'word':r['word'], **({'challenge':r['selection_stratum']=='challenge'} if pair else {}),
             'dictionary_senses':r['dictionary_senses']} for r in records]

def validate(result, records, kind):
    errors=[]; by_word={r['word']:r for r in records}
    senses={s['sense_id']:s for r in records for s in r['dictionary_senses']}
    if kind=='word':
        got=[r['word'] for r in result['words']]
        if sorted(got)!=sorted(by_word): errors.append('word accounting mismatch')
        for row in result['words']:
            if row['word'] not in by_word: continue
            expected={s['sense_id'] for s in by_word[row['word']]['dictionary_senses'] if s['pos'] in ('a','s')}
            if sorted(s['sense_id'] for s in row['senses'])!=sorted(expected): errors.append(row['word']+': adjective sense accounting mismatch')
            for s in row['senses']:
                if s['sense_id'] not in expected or not s['evidence_quote'] or s['evidence_quote'] not in senses.get(s['sense_id'],{}).get('gloss',''):
                    errors.append(row['word']+': invalid source quote '+s['sense_id'])
            eligible={s['sense_id'] for s in row['senses'] if s['status']=='eligible'}
            for group in row['interpretation_groups']:
                if not set(group['sense_ids']).issubset(eligible): errors.append(row['word']+': group references noneligible sense')
            statuses={s['status'] for s in row['senses']}
            implied='eligible' if 'eligible' in statuses else ('unresolved' if not expected or 'unresolved' in statuses else 'ineligible')
            if implied!=row['word_status']: errors.append(row['word']+': inconsistent word status')
    else:
        for row in result['analyses']:
            if row['word'] not in by_word: errors.append('unknown derived word')
            for e in row['evidence']:
                allowed={s['sense_id'] for s in by_word.get(e['word'],{}).get('dictionary_senses',[])}
                if e['sense_id'] not in allowed or not e['quote'] or e['quote'] not in senses.get(e['sense_id'],{}).get('gloss',''):
                    errors.append('invalid pair evidence '+str(e))
            for a in row['possible_sense_alignments']:
                for field, word in [('word_sense_id',row['word']),('base_sense_id',row['immediate_base'])]:
                    allowed={s['sense_id'] for s in by_word.get(word,{}).get('dictionary_senses',[])}
                    if a[field] not in allowed: errors.append('invalid alignment '+a[field])
    return errors

def call(family, label, records, kind, commit):
    directory=OUT/family/label
    if directory.exists(): raise FileExistsError(directory)
    directory.mkdir(parents=True)
    schema=WORD_SCHEMA if kind=='word' else PAIR_SCHEMA
    prompt=(HERE/('word-prompt.txt' if kind=='word' else 'pair-prompt.txt')).read_text()
    prompt+='\n'+json.dumps(stripped(records,kind=='pair'),ensure_ascii=False,sort_keys=True)+'\n'
    prompt+='\nSource licences:\n'+(PACKET/'WORDNET-LICENSE.txt').read_text()+'\n'+(PACKET/'WIKTIONARY-LICENSE.txt').read_text()
    (directory/'prompt.txt').write_text(prompt); write_json(directory/'schema.json',schema)
    started=now(); tic=time.monotonic()
    env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
    with tempfile.TemporaryDirectory(prefix='lexical-coding-neutral-') as neutral:
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
             '--json-schema',json.dumps(schema),'--max-budget-usd','5','-p',prompt]
        meta={'family':family,'requested_model':MODELS[family],'kind':kind,'label':label,'source_commit':commit,
              'started_at':started,'input_sha256':sha(directory/'prompt.txt'),'schema_sha256':sha(directory/'schema.json'),
              'source_manifest_sha256':sha(PACKET/'manifest.json'),'python':platform.python_version(),
              'platform':platform.platform(),'seed':'model seed unavailable; source selection fixed at 20261010',
              'command':command if family=='codex' else command[:-1]+['<stored prompt.txt>'],
              'rate_or_commonness_input':False,'subscription_route':True}
        write_json(directory/'started.json',meta)
        with (directory/'stdout.txt').open('w') as stdout,(directory/'stderr.txt').open('w') as stderr:
            try:
                proc=subprocess.run(command,cwd=neutral,env=env,input=prompt if family=='codex' else None,
                                    text=True,stdout=stdout,stderr=stderr,timeout=900)
                meta['exit_code']=proc.returncode
            except subprocess.TimeoutExpired:
                meta['exit_code']='timeout'
        meta.update(completed_at=now(),elapsed_seconds=time.monotonic()-tic)
    try:
        if meta['exit_code']!=0: raise RuntimeError('CLI failed')
        if family=='claude':
            events=[json.loads(x) for x in (directory/'stdout.txt').read_text().splitlines() if x.strip()]
            init=next(x for x in events if x.get('type')=='system' and x.get('subtype')=='init')
            end=next(x for x in reversed(events) if x.get('type')=='result')
            meta['returned_model']=init['model'];meta['tools']=init.get('tools')
            meta['usage']=end.get('usage');meta['model_usage']=end.get('modelUsage');meta['api_equivalent_usd']=end.get('total_cost_usd')
            if init['model']!=MODELS[family] or init.get('tools'): raise ValueError('model/tools mismatch')
            result=end.get('structured_output')
            if result is None:
                result=json.loads(end['result'])
            write_json(directory/'answer.json',result)
        else:
            transcript=(directory/'stderr.txt').read_text()
            if 'model: '+MODELS[family] not in transcript or 'reasoning effort: high' not in transcript:
                raise ValueError('Codex model/effort mismatch')
            meta['returned_model']=MODELS[family]
            meta['tokens_used_tail']=transcript[-500:]
            result=json.loads((directory/'answer.json').read_text())
        meta['validation_errors']=validate(result,records,kind)
        meta['status']='validated' if not meta['validation_errors'] else 'needs_evidence_review'
    except Exception as exc:
        meta['status']='failed';meta['error']=repr(exc)
    write_json(directory/'manifest.json',meta)
    print(f'{family} {label}: {meta["status"]}; {meta["elapsed_seconds"]:.1f}s',flush=True)
    return meta

def family_run(family, records, commit, mode):
    results=[]
    if mode=='words':
        for n in range(0,len(records),10):
            result=call(family,f'words-{n//10+1:02}',records[n:n+10],'word',commit)
            results.append(result)
            if result['status']=='failed': break
    else:
        results.append(call(family,'independent-pairs',records,'pair',commit))
    return results

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['words','pairs']);args=parser.parse_args()
    commit=published_source();records=json.loads((PACKET/'terms.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures={family:pool.submit(family_run,family,records,commit,args.mode) for family in MODELS}
        results={family:f.result() for family,f in futures.items()}
    write_json(OUT/(args.mode+'-summary.json'),results)

if __name__=='__main__': main()
