"""Assemble the completed pilot's source audit; preserve every original output."""
import collections
import json
import platform
import re
from pathlib import Path
from code_pilot import OUT, PACKET
from import_sources import PRIVATE, RAW, ROOT, now, published_source, sha, write_json
from wordnet_source import WordNet

def wiki_display(text):
    # Only link display text and italic/bold delimiters; no template inference.
    return re.sub(r'\[\[([^\[\]]+)\]\]',lambda m:m[1].split('|')[-1],text).replace("'''",'').replace("''",'')

def reading_errors(alignment):
    expected={'contrary':('yes','no'),'complementary':('no','no')}
    if alignment['reading'] not in expected: return []
    actual=(alignment.get('can_neither'),alignment.get('can_both'))
    return [] if actual==expected[alignment['reading']] else ['reading contradicts neither/both diagnostic']

def main():
    commit=published_source();finished=now()
    terms=json.loads((PACKET/'terms.json').read_text());byword={r['word']:r for r in terms}
    allforms={r['word']:r for r in json.loads((PACKET/'all_candidate_forms.json').read_text())}
    rules=json.loads((PRIVATE/'pilot-audit-rules.json').read_text())
    if set(rules['word_notes'])!=set(byword): raise ValueError('Incomplete primary source review')
    dictionary=WordNet(RAW/'wn3.1.dict.tar.gz')
    records={};manifests=[];quote_audit=[];pair_outputs={};reading_checks=[]
    input_paths=[PACKET/'terms.json',PACKET/'manifest.json',PRIVATE/'pilot-audit-rules.json']
    for family in ('codex','claude'):
        records[family]={}
        for label in [f'words-{n:02}' for n in range(1,5)]+['independent-pairs','independent-pairs-v2']:
            directory=OUT/family/label
            meta=json.loads((directory/'manifest.json').read_text())
            if meta['status']=='failed': raise RuntimeError('Unresolved transport failure')
            answer=json.loads((directory/'answer.json').read_text())
            manifests.append(meta);input_paths.extend([directory/'manifest.json',directory/'answer.json'])
            if label.startswith('words'):
                for row in answer['words']:
                    if row['word'] in records[family]: raise ValueError('Duplicate word judgment')
                    records[family][row['word']]=row
                evidences=[{'word':r['word'],'sense_id':s['sense_id'],'quote':s['evidence_quote']} for r in answer['words'] for s in r['senses']]
            else:
                pair_outputs[family+'/'+label]=answer
                evidences=[e for a in answer['analyses'] for e in a['evidence']]
                if label.endswith('v2'):
                    for a in answer['analyses']:
                        for alignment in a['possible_sense_alignments']:
                            errors=reading_errors(alignment)
                            reading_checks.append({'family':family,'word':a['word'],'base':a['immediate_base'],**alignment,'errors':errors})
            for e in evidences:
                sources={s['sense_id']:s for s in byword[e['word']]['dictionary_senses']}
                if e['sense_id'] not in sources: raise ValueError('Unresolved sense identifier')
                gloss=sources[e['sense_id']]['gloss']
                if e['quote'] and e['quote'] in gloss: status='exact_source_substring'
                elif e['quote'] and e['sense_id'].startswith('wikt:') and e['quote'] in wiki_display(gloss):
                    status='verified_wiki_display_substring'
                else: status='unresolved_quote'
                quote_audit.append({'family':family,'call':label,**e,'status':status,
                                    'exact_source_gloss':gloss if status!='exact_source_substring' else None})
        if set(records[family])!=set(byword): raise ValueError('Incomplete 40-word model pass')
    overrides={(r['word'],r['sense_id']):r for r in rules['sense_overrides']}
    audited=[];disagreements=[]
    for word in sorted(byword):
        term=byword[word];source_senses={s['sense_id']:s for s in term['dictionary_senses'] if s['pos'] in ('a','s')}
        codes={family:{s['sense_id']:s for s in records[family][word]['senses']} for family in records}
        for family in codes:
            if set(codes[family])!=set(source_senses): raise ValueError('Missing or extra adjective sense')
        rows=[]
        for sid,source in source_senses.items():
            statuses={family:codes[family][sid]['status'] for family in codes}
            override=overrides.get((word,sid))
            decision=override['status'] if override else codes['codex'][sid]['status']
            reason=override['reason'] if override else codes['codex'][sid]['reason']
            if len(set(statuses.values()))>1:
                disagreements.append({'word':word,'sense_id':sid,'model_statuses':statuses,'audit_status':decision})
            rows.append({'sense_id':sid,'source_gloss':source['gloss'],'model_statuses':statuses,
                         'audited_status':decision,'reason':reason,'primary_review_note':rules['word_notes'][word],
                         'explicit_override':bool(override)})
        states={r['audited_status'] for r in rows}
        status='eligible' if 'eligible' in states else ('unresolved' if not rows or 'unresolved' in states else 'ineligible')
        coverage='adjective_attested' if rows else 'supplement_checked_no_adjective_attested'
        if not rows and not (term.get('supplement') or {}).get('status')=='retrieved':
            raise ValueError('No-adjective case lacks planned supplementary source check')
        admitted='eligible' if status=='eligible' else ('not_admitted_no_attested_adjective' if not rows else status)
        audited.append({'word':word,'form_id':term['form_id'],'sources':term['sources'],'selection_stratum':term['selection_stratum'],
                        'conservative_status':status,'resource_attested_specification':admitted,'coverage':coverage,
                        'model_statuses':{family:records[family][word]['word_status'] for family in records},
                        'review_note':rules['word_notes'][word],'senses':rows,
                        'original_interpretation_groupings':{family:records[family][word]['interpretation_groups'] for family in records},
                        'target_status':'not_frozen; original groupings are evidence for alternatives, not independent lexical units'})
    wordaudit={r['word']:r for r in audited};pairs=[]
    for p in rules['primary_pair_candidates']:
        if any(wordaudit[w]['conservative_status']!='eligible' for w in (p['word'],p['base'])): raise ValueError('Primary pair lacks eligible member')
        sources={w:allforms[w]['sources'] for w in (p['word'],p['base'])}
        candidate={'word':p['word'],'base':p['base'],'primary_status':'provisionally_supported; readings/targets not frozen',
                   'source_memberships':sources,'anderson_pair':all('anderson1968' in x for x in sources.values()),
                   'warriner_pair':all('warriner2013' in x for x in sources.values()),
                   'shared_base_id':allforms[p['base']]['form_id'],'shared_word_ids':[allforms[w]['form_id'] for w in (p['word'],p['base'])],
                   'screens':{key:[a for a in value['analyses'] if a['word']==p['word'] and a['immediate_base']==p['base']] for key,value in pair_outputs.items()}}
        if any(not xs for xs in candidate['screens'].values()): raise ValueError('Provisional pair missing from a model screen')
        pairs.append(candidate)
    other=[]
    for row in rules['other_pair_analyses']:
        other.append({**row,'base_in_sources':row['base'] in allforms,'base_dictionary_evidence':dictionary.packet(row['base'])})
    detector=json.loads((PACKET/'detector_candidates.json').read_text())
    detector_edges={(word,c['base']) for word,cs in detector.items() for c in cs}
    missed_supported=[p for p in rules['primary_pair_candidates'] if (p['word'],p['base']) not in detector_edges]
    indep_words={k:set(v['apparent_negative_words_reviewed']) for k,v in pair_outputs.items()}
    all_detector_words={w for w,cs in detector.items() if cs}
    graph=collections.defaultdict(set)
    for p in pairs: graph[p['word']].add(p['base']);graph[p['base']].add(p['word'])
    seen=set();components=[]
    for word in sorted(graph):
        if word in seen: continue
        component=set();todo=[word]
        while todo:
            x=todo.pop()
            if x in component: continue
            component.add(x);todo.extend(graph[x]-component)
        seen|=component;components.append(sorted(component))
    def counts(key): return dict(collections.Counter(r[key] for r in audited))
    word_agreement=sum(records['codex'][w]['word_status']==records['claude'][w]['word_status'] for w in byword)
    group_differences=[]
    for word in byword:
        patterns={family:sorted(sorted(g['sense_ids']) for g in records[family][word]['interpretation_groups']) for family in records}
        if patterns['codex']!=patterns['claude']: group_differences.append({'word':word,'patterns':patterns})
    cost=[]
    for m in manifests:
        row={k:m.get(k) for k in ('family','label','kind','source_commit','started_at','completed_at','elapsed_seconds','requested_model','returned_model','api_equivalent_usd','usage')}
        if m['family']=='codex':
            path=OUT/m['family']/m['label']/'stderr.txt'
            matches=re.findall(r'tokens used\s*\n([\d,]+)',path.read_text())
            row['cli_reported_tokens_used']=int(matches[-1].replace(',','')) if matches else None
        cost.append(row)
    summary={'created_at':finished,'source_commit':commit,'python':platform.python_version(),'source_import':json.loads((PACKET/'manifest.json').read_text())['summary'],
        'model_word_passes':2,'words_per_pass':40,'adjective_senses_per_pass':sum(len(r['senses']) for r in audited),
        'word_status_agreement':{'agree':word_agreement,'denominator':40,'not_accuracy':True},
        'sense_status_agreement':{'agree':sum(len(r['senses']) for r in audited)-len(disagreements),'denominator':sum(len(r['senses']) for r in audited),'not_accuracy':True},
        'conservative_word_audit_counts':counts('conservative_status'),'resource_attested_specification_counts':counts('resource_attested_specification'),
        'sense_audit_counts':dict(collections.Counter(s['audited_status'] for r in audited for s in r['senses'])),
        'explicit_sense_overrides':len(overrides),'original_grouping_difference_words':len(group_differences),
        'quote_checks':dict(collections.Counter(r['status'] for r in quote_audit)),
        'reading_diagnostic_errors':sum(bool(r['errors']) for r in reading_checks),
        'primary_candidate_pairs':len(pairs),'anderson_primary_candidate_pairs':sum(p['anderson_pair'] for p in pairs),
        'warriner_primary_candidate_pairs':sum(p['warriner_pair'] for p in pairs),'unique_primary_pair_words':len(graph),'pair_graph_components':len(components),
        'other_pair_analyses':len(other),'detector_candidates':len(detector_edges),
        'independent_screen_counts':{k:len(v) for k,v in indep_words.items()},
        'detector_words_omitted_from_independent_screens':{k:sorted(all_detector_words-v) for k,v in indep_words.items()},
        'additional_supported_primary_pairs_from_independent_audit':len(missed_supported),
        'bounded_audit_not_recall_estimate':True,'model_calls':len(manifests),
        'claude_api_equivalent_usd':sum(m.get('api_equivalent_usd') or 0 for m in manifests),
        'model_call_seconds':sum(m['elapsed_seconds'] for m in manifests),'cost_by_call':cost,
        'ratings_joined':False,'commonness_judgments_collected':False,'frame_frozen':False,
        'full_vocabulary_coding_started':False,'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in input_paths},
        'audit_script_sha256':sha(Path(__file__)),
        'primary_review_timing':'Source review overlapped model execution; a separate active-review or token-cost meter was not available. Do not extrapolate model inference time as end-to-end curation cost.'}
    private_output=PRIVATE/'audit-20261010'
    write_json(private_output/'word-audit.json',audited)
    write_json(private_output/'sense-disagreements.json',disagreements)
    write_json(private_output/'grouping-differences.json',group_differences)
    write_json(private_output/'quote-audit.json',quote_audit)
    write_json(private_output/'pair-audit.json',{'primary_candidates':pairs,'other_analyses':other,'graph_components':components,'reading_checks':reading_checks,'missed_supported':missed_supported})
    if summary['quote_checks'].get('unresolved_quote',0) or summary['reading_diagnostic_errors']:
        raise ValueError('Audit contains unresolved evidence/diagnostic validation; preserve private details and inspect')
    output=ROOT/'results/lexical-frame/pilot-20261010'
    write_json(output/'SUMMARY.json',summary)
    write_json(ROOT/'logs/lexical-frame-pilot-audit-20261010.json',{'source_commit':commit,'at':finished,'summary_sha256':sha(output/'SUMMARY.json'),
                'private_artifact_hashes':{p.name:sha(p) for p in private_output.glob('*.json')}})
    print(json.dumps({k:v for k,v in summary.items() if k not in ('input_sha256','cost_by_call','source_import')},indent=2))

if __name__=='__main__': main()
