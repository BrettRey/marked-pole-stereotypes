"""Submit Claude's remaining independent batches, two concurrent calls."""
import concurrent.futures
import json
from code_pilot import OUT, PACKET, call
from import_sources import published_source

if __name__=='__main__':
    commit=published_source()
    records=json.loads((PACKET/'terms.json').read_text())
    pending=[]
    for i in range(10,40,10):
        label=f'words-{i//10+1:02}'
        if (OUT/'claude'/label).exists():
            raise FileExistsError('Do not repeat or overwrite an attempted call: '+label)
        pending.append((label,records[i:i+10]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(call,'claude',label,subset,'word',commit) for label,subset in pending]
        for future in concurrent.futures.as_completed(futures):
            print(future.result()['status'],flush=True)
