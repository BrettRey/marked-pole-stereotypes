"""Read-only-input assembly of the bounded review; never invokes a model."""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from import_sources import ROOT, now, published_source, sha, write_json
from six_pair_review import OUT, MODELS, validate
from audit_pilot import wiki_display

def reading(target):
    both,neither=target['can_both'],target['can_neither']
    if both=='no' and neither=='no': return 'complementary_within_recorded_domain'
    if both=='no' and neither=='yes': return 'contrary_within_recorded_domain'
    if both=='yes': return 'overlap_possible'
    return 'unresolved'

def assemble(rules):
    preparation=json.loads((OUT/'preparation.json').read_text())
    manifests=[];pair_records=[];evidence_count=0;all_saved=[];all_additional=[]
    failures=[];validation_issues=[];model_readings=Counter();quote_audit=[]
    primary={r['pair_id']:r for r in rules['pairs']}
    for name,digest in sorted(preparation['packet_hashes'].items()):
        packet_path=OUT/'packets'/name
        if sha(packet_path)!=digest: raise ValueError('Modified packet '+name)
        packet=json.loads(packet_path.read_text());pid=packet['pair_id']
        source_senses={(e['word'],s['sense_id']):s for e in packet['dictionary_entries'] for s in e['dictionary_senses']}
        adjudication=primary[pid]
        wanted={r['proposal_id'] for r in packet['saved_proposals']}
        if {r['proposal_id'] for r in adjudication['saved_proposals']}!=wanted:
            raise ValueError('Primary saved-proposal accounting: '+pid)
        record={'pair_id':pid,'packet_sha256':digest,'base':packet['base'],'word':packet['word'],
                'source_entry_relationships':adjudication['source_entry_relationships'],
                'families':{},'primary_audit':adjudication}
        for family in MODELS:
            directory=OUT/'calls'/family/pid
            meta=json.loads((directory/'manifest.json').read_text());manifests.append(meta)
            if sha(directory/'prompt.txt')!=meta['prompt_sha256']: raise ValueError('Changed prompt')
            if sha(directory/'schema.json')!=meta['schema_sha256']: raise ValueError('Changed schema')
            family_record={'attempt':1,'status':meta['status'],'exit_code':meta['exit_code'],
                'elapsed_seconds':meta['elapsed_seconds'],'manifest_sha256':sha(directory/'manifest.json')}
            if meta['status']=='failed':
                failures.append({'pair_id':pid,'family':family,'exit_code':meta['exit_code']})
            else:
                answer=json.loads((directory/'answer.json').read_text())
                errors=validate(answer,packet)
                if errors!=meta['validation_errors']:raise ValueError('Validation changed')
                if errors:validation_issues.append({'pair_id':pid,'family':family,'errors':errors})
                family_record['answer']=answer
                family_record['answer_sha256']=sha(directory/'answer.json')
                for key,rows in [('saved_alignments',all_saved),('additional_alignments',all_additional)]:
                    for a in answer[key]:
                        evidence_count+=len(a['evidence'])
                        for e in a['evidence']:
                            gloss=source_senses[e['word'],e['sense_id']]['gloss']
                            if e['quote'] and e['quote'] in gloss:kind='exact_source_substring'
                            elif e['quote'] and e['sense_id'].startswith('wikt:') and e['quote'] in wiki_display(gloss):
                                kind='verified_wiki_display_substring'
                            else:kind='unresolved_quote'
                            quote_audit.append({'family':family,'pair_id':pid,'proposal_id':a['proposal_id'],
                                **e,'audit_status':kind,'original_gloss':gloss})
                        rows.append({'family':family,'pair_id':pid,**a})
                        for t in a['targets']:model_readings[reading(t)]+=1
                additional_keys={a['proposal_id'] for a in answer['additional_alignments']}
                audited_keys={a['proposal_id'] for a in adjudication['additional_proposals'] if a['family']==family}
                if additional_keys!=audited_keys:raise ValueError('Additional proposal not audited: '+pid+'/'+family)
            record['families'][family]=family_record
        pair_records.append(record)
    if len(manifests)!=12:raise ValueError('12-attempt accounting')
    primary_saved=[a for p in rules['pairs'] for a in p['saved_proposals']]
    summary={'finished_at':now(),'pairs':6,'distinct_forms':11,'saved_candidate_alignments':16,
        'attempts':len(manifests),'attempt_statuses':dict(Counter(m['status'] for m in manifests)),
        'failures':failures,'validation_issues':validation_issues,
        'returned_saved_alignment_records':len(all_saved),'returned_additional_alignment_records':len(all_additional),
        'source_quote_references_checked':evidence_count,
        'quote_audit_counts':dict(Counter(x['audit_status'] for x in quote_audit)),
        'model_target_reading_counts_not_independent_pairs':dict(model_readings),
        'primary_saved_dispositions':dict(Counter(a['disposition'] for a in primary_saved)),
        'primary_pair_dispositions':[{k:p[k] for k in ('pair_id','disposition','summary')} for p in rules['pairs']],
        'summed_call_seconds':sum(m['elapsed_seconds'] for m in manifests),
        'inference_wall_seconds':(max(datetime.fromisoformat(m['completed_at']) for m in manifests)-
                                  min(datetime.fromisoformat(m['started_at']) for m in manifests)).total_seconds(),
        'completed_claude_api_equivalent_usd':sum(m.get('api_equivalent_usd') or 0 for m in manifests),
        'claude_cost_accounting_complete':all(m.get('api_equivalent_usd') is not None for m in manifests if m['family']=='claude'),
        'codex_reported_tokens_used':sum(m.get('reported_tokens_used') or 0 for m in manifests),
        'subscription_route':True,'purchased_api_credits':False,'hf_compute_used_for_this_stage':False,
        'primary_review_time':'unmetered; overlaps service time; not included in call-cost extrapolation',
        'commonness_observations':0,'frame_frozen':False,
        'missed_pair_recall_estimated':False,'gold_standard_claimed':False}
    return summary,{'pairs':pair_records,'summary':summary,'quote_audit':quote_audit}

def main():
    commit=published_source()
    path=OUT/'primary-audit-rules.json'
    rules=json.loads(path.read_text())
    summary,detail=assemble(rules)
    summary.update(source_commit=commit,primary_rules_sha256=sha(path),script_sha256=sha(__file__))
    target=OUT/'audited-pairs.json'
    if target.exists():raise FileExistsError(target)
    write_json(target,detail)
    write_json(ROOT/'results/lexical-frame/six-pair-20261011/SUMMARY.json',summary)
    write_json(ROOT/'logs/lexical-six-pair-audit-20261011.json',{
        'source_commit':commit,'finished_at':now(),'primary_rules_sha256':sha(path),'detail_sha256':sha(target),
        'preparation_sha256':sha(OUT/'preparation.json'),'script_sha256':sha(__file__),
        'no_model_calls':True})
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
