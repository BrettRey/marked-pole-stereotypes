"""Encode the existing pilot's provenance/identity/target layers without new ratings.

This preserves original sense decisions and both model groupings. Primary
interpretation groupings are auditable operational proposals, not a claim to
resolved lexical homonymy/polysemy or a new set of independent observations.
"""
import json
from collections import Counter
from import_sources import PRIVATE, ROOT, now, published_source, sha, write_json

SOURCE=PRIVATE/'pilot-20261010-v2'
AUDIT=PRIVATE/'audit-20261010'
OUT=PRIVATE/'six-pair-20261011'

# Each row: interpretation label, source-sense suffixes. Every eligible or
# unresolved old sense must be covered; one sense can support a deliberate split.
GROUPS={
'angry':[('experienced anger',['00114629'])],
'attentive':[('cognitive attention and heed',['00164857','01198026']),
             ('care directed toward another person',['00164857'])],
'careful':[('caution and heedful consideration',['00309819','01984552']),
           ('financial prudence',['01901166']),('anxiety',['02465750']),
           ('measured movement: psychological scope unresolved',['01275071'])],
'careless':[('deficient attention or consideration',['00312461','01197642'])],
'changeable':[('tendency toward changing behaviour or moods',['00345024']),
              ('generic mutability: psychological scope unresolved',['00357450'])],
'cold':[('emotional distance',['01260684']),('unconsciousness: scope unresolved',['00574324']),
        ('lack of enthusiasm',['00890609']),('lack of compunction',['01267081']),
        ('sexual unresponsiveness',['01469690']),('intense fury: construction mapping unresolved',['01514641']),
        ('mastery: construction mapping unresolved',['01754740'])],
'friendly':[('friendlike interpersonal disposition',['01078338']),
            ('supportive rather than antagonistic orientation',['01249700'])],
'happy':[('experienced joy or pleasure',['01151786']),('willingness to act or help',['02576313'])],
'high-spirited':[('joyous lack of restraint',['02287457'])],
'impatient':[('irritability under delay or opposition',['01741490']),('eagerness to begin',['00815105'])],
'inattentive':[('deficient attention or care',['00166125','00759397'])],
'kind':[('considerate and helpful nature',['01374976']),('forgiveness under provocation',['01044891'])],
'meditative':[('serious thoughtfulness',['02428209'])],
'methodical':[('method and orderliness',['01672820'])],
'patient':[('even-tempered endurance',['01739985'])],
'profane':[('nonreligious orientation: psychological scope unresolved',['02064284']),
           ('profanity in speech',['00426521']),('irreverence toward the sacred',['02019844'])],
'prompt':[('quick response: enduring-person mapping unresolved',['00981945']),
          ('punctuality: person mapping unresolved',['01906742']),
          ('readiness to act or help',['01938075'])],
'religious':[('religious belief and reverence',['01787685']),('scrupulous conscientiousness',['02092886'])],
'responsible':[('personal trustworthiness',['02003477']),('assigned accountability only',['02003477'])],
'smart':[('mental alertness and resourcefulness',['00440447']),
         ('impertinent conduct',['00206887']),('quick and easy learning',['01338411'])],
'unattentive':[('lack of attentiveness: subtype to be aligned',['wikt:93149049:en:a:1'])],
'uncouth':[('unrefined manners',['01957020'])],
'unfriendly':[('unfriendly interpersonal orientation',['01080481','01249262'])],
'unhappy':[('experienced distress or sadness',['00912446','01152997']),
           ('discontent about a specified respect',['01152997']),
           ('unfortunate circumstances: psychological scope unresolved',['01055513'])],
'uniform':[('generic sameness of character: psychological scope unresolved',['01973553'])],
'unkind':[('deficient kindness or humane feeling',['01376655','01267289'])],
'valuable':[('unspecified personal worth: psychological scope unresolved',['02598053'])]}

def build(terms, audits, model_senses):
    records=[]
    for term in terms:
        word=term['word']; old=audits[word]; fid=term['form_id']
        senses={s['sense_id']:s for s in old['senses']}
        interpretations=[]
        for n,(label,keys) in enumerate(GROUPS.get(word,[]),1):
            ids=[]
            for key in keys:
                matches=[sid for sid in senses if sid==key or sid.endswith(':'+key)]
                if len(matches)!=1: raise ValueError((word,key,matches))
                ids+=matches
            statuses={senses[sid]['audited_status'] for sid in ids}
            status='eligible' if 'eligible' in statuses else 'unresolved'
            if label=='assigned accountability only': status='ineligible'
            iid=f'{fid}:adj:interpretation-{n:02}'
            temporal={family:{sid:model_senses[family].get((word,sid),{}).get('temporal','unresolved')
                              for sid in ids} for family in model_senses}
            interpretations.append({'interpretation_id':iid,'lexical_identity_record':fid+':adj:identity',
                'label':label,'source_sense_ids':ids,'eligibility':status,
                'grouping_status':'primary-agent operational proposal; original model alternatives preserved',
                'prior_temporal_labels':temporal,
                'judgment_targets':[{'target_id':iid+':target-pending',
                    'status':'not_released; temporal interpretation and application domain require explicit assignment',
                    'population':'US residents of all ages','reference_year':2026,
                    'temporal':None,'application_domain':None,
                    'allowed_temporal_values':['characteristic_capacity','temporary_state'],
                    'denominator_rule':'population or equal-person then uniform waking moment, including unusual situations',
                    'presentation_ids':[]}] if status=='eligible' else []})
        covered={sid for r in interpretations for sid in r['source_sense_ids']}
        required={sid for sid,s in senses.items() if s['audited_status']!='ineligible'}
        if covered!=required: raise ValueError(('interpretation accounting',word,covered^required))
        cats=sorted({'adjective' if x['pos'] in ('a','s') else {'n':'noun','v':'verb','r':'adverb'}[x['pos']]
                     for x in term['dictionary_senses']})
        identity=[]
        if 'adjective' in cats:
            identity=[{'lexical_identity_record_id':fid+':adj:identity','category':'adjective',
                'status':'provisional; this is an identity-resolution record, not a settled independent unit',
                'sense_to_interpretation_ids':[r['interpretation_id'] for r in interpretations],
                'homonymy_polysemy_status':'not resolved by form hash or source synsets',
                'analysis_weight':None,'release_blocker':'fix grouping/identity specification before analysis',
                'word_analysis_rule':'one unit per resolved lexical item within a specification',
                'pair_analysis_rule':'separate weighting estimand outstanding; shared members preserved'}]
        other_no_scope=not any(s['audited_status']=='eligible' for s in senses.values())
        unresolved=any(s['audited_status']=='unresolved' for s in senses.values())
        already=bool(term['supplement']) or word in {'attentive','friendly','happy','impatient','inattentive','kind','patient','unfriendly','unhappy','unkind'}
        records.append({'word':word,'form_id':fid,'source_entry_ids':term['source_entries'],
            'original_spellings':term['original_spellings'],'attested_categories':cats,
            'old_form_specification':old['resource_attested_specification'],
            'lexical_identity_records':identity,'interpretations':interpretations,
            'original_sense_audit':old['senses'],
            'original_family_interpretation_groups':old['original_interpretation_groupings'],
            'word_cue_presentation':{'presentation_id':fid+':unglossed-cue','cue':word,
                'attaches_to':'form cue; category/interpretation not resolved by a bare-word response',
                'inherits_interpretation_id':None,'observations_collected':False},
            'description_presentations':[],
            'supplement_rule_status':'fixed supplement already available' if already else
                ('triggered_for_full_pass; not retrieved in six-pair stage' if other_no_scope or unresolved else 'no current word-level trigger'),
            'pair_review_attachment':'six-pair-20261011; supplementary interpretations retained in pair audit' if word in
                {'attentive','inattentive','unattentive','kind','unkind','friendly','unfriendly','patient','impatient','happy','unhappy'} else None,
            'mapping_note':old['review_note']})
    return records

def main():
    commit=published_source()
    target=OUT/'forty-form-mapping.json'
    if target.exists(): raise FileExistsError(target)
    terms=json.loads((SOURCE/'terms.json').read_text())
    audits={x['word']:x for x in json.loads((AUDIT/'word-audit.json').read_text())}
    model_senses={}
    paths=[SOURCE/'terms.json',AUDIT/'word-audit.json']
    for fam in ('codex','claude'):
        model_senses[fam]={}
        for path in sorted((PRIVATE/'coding-20261010-v1'/fam).glob('words-*/answer.json')):
            paths.append(path)
            for word in json.loads(path.read_text())['words']:
                for sense in word['senses']:model_senses[fam][word['word'],sense['sense_id']]=sense
    rows=build(terms,audits,model_senses)
    write_json(target,rows)
    summary={'created_at':now(),'source_commit':commit,'forms':len(rows),
        'source_entry_links':sum(len(x['source_entry_ids']) for x in rows),
        'old_sense_records_preserved':sum(len(x['original_sense_audit']) for x in rows),
        'provisional_adjective_identity_records':sum(len(x['lexical_identity_records']) for x in rows),
        'operational_interpretation_records':sum(len(x['interpretations']) for x in rows),
        'old_form_specifications':dict(Counter(x['old_form_specification'] for x in rows)),
        'description_presentations':0,'commonness_observations':0,'frame_frozen':False,
        'mapping_sha256':sha(target),'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths},
        'limitation':'Mapping demonstrates separate layers; lexical identity, temporal assignment and applicability outside the six reviewed pairs remain prospective release gates.'}
    write_json(ROOT/'results/lexical-frame/six-pair-20261011/mapping-summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='input_hashes'},indent=2))

if __name__=='__main__':main()
