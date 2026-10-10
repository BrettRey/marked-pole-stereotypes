"""The fixed pilot pair rerun after identifying v1 reading/source overclaims."""
import concurrent.futures
import copy
import json
from code_pilot import HERE, OUT, PACKET, PAIR_SCHEMA, MODELS, call, enum
from import_sources import published_source, write_json

if __name__=='__main__':
    commit=published_source()
    records=json.loads((PACKET/'terms.json').read_text())
    schema=copy.deepcopy(PAIR_SCHEMA)
    alignment=schema['properties']['analyses']['items']['properties']['possible_sense_alignments']['items']
    for key in ('can_neither','can_both'):
        alignment['properties'][key]=enum('yes','no','undetermined')
        alignment['required'].append(key)
    prompt=OUT/'pair-prompt-v2.txt'
    if prompt.exists(): raise FileExistsError('Preserve original rerun prompt and outputs')
    prompt.write_text((HERE/'pair-prompt.txt').read_text()+'\n\n'+(HERE/'pair-recheck-addendum.txt').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures={family:pool.submit(call,family,'independent-pairs-v2',records,'pair',commit,prompt,schema) for family in MODELS}
        results={family:f.result() for family,f in futures.items()}
    write_json(OUT/'pair-recheck-summary.json',results)
