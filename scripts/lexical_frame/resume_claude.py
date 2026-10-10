"""Repair a transport-only audit and resume unattempted calls; never rejudge."""
import json
import shutil
from code_pilot import OUT, PACKET, MODELS, call, validate
from import_sources import now, published_source, sha, write_json

def main():
    commit=published_source()
    records=json.loads((PACKET/'terms.json').read_text())
    tasks=[('words-01',records[:10],'word')]+[(f'words-{i//10+1:02}',records[i:i+10],'word') for i in range(10,40,10)]
    tasks.append(('independent-pairs',records,'pair'))
    for label,subset,kind in tasks:
        directory=OUT/'claude'/label
        if not directory.exists():
            result=call('claude',label,subset,kind,commit)
            if result['status']=='failed': raise RuntimeError(result)
            continue
        manifest=directory/'manifest.json'
        if not manifest.exists(): raise RuntimeError('Original call still running; wait')
        meta=json.loads(manifest.read_text())
        if meta['status']!='failed': continue
        if meta.get('error')!="ValueError('model/tools mismatch')" or meta.get('exit_code')!=0:
            raise RuntimeError('Not the documented StructuredOutput transport-only error')
        events=[json.loads(x) for x in (directory/'stdout.txt').read_text().splitlines() if x.strip()]
        init=next(x for x in events if x.get('type')=='system' and x.get('subtype')=='init')
        end=next(x for x in reversed(events) if x.get('type')=='result')
        if init['model']!=MODELS['claude'] or set(init.get('tools',[]))-{'StructuredOutput'}:
            raise RuntimeError('Unexpected actual model or tools')
        result=end.get('structured_output')
        if result is None: result=json.loads(end['result'])
        original=directory/'manifest-transport-check-v1.json'
        if original.exists(): raise FileExistsError(original)
        shutil.copy2(manifest,original)
        write_json(directory/'answer.json',result)
        meta.pop('error',None)
        meta['validation_errors']=validate(result,subset,kind)
        meta['status']='validated' if not meta['validation_errors'] else 'needs_evidence_review'
        meta['transport_revalidation']={'at':now(),'source_commit':commit,'raw_sha256':sha(directory/'stdout.txt'),
            'reason':'Allow only schema-serialization StructuredOutput; no research tools. Reparse saved result; no new model call.'}
        write_json(manifest,meta)
        print(label,meta['status'],'reparsed without inference',flush=True)

if __name__=='__main__': main()
