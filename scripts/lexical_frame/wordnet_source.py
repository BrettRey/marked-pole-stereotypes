"""Read pinned WordNet bytes directly; omit sense ranks and usage counts."""
from __future__ import annotations

import re
import tarfile
from collections import defaultdict


class WordNet:
    def __init__(self, archive_path):
        self.senses = {}
        self.by_lemma = defaultdict(list)
        self.license = ''
        with tarfile.open(archive_path) as archive:
            for part in ('adj', 'noun', 'verb', 'adv'):
                text = archive.extractfile(f'dict/data.{part}').read().decode('utf-8')
                if part == 'adj':
                    self.license = '\n'.join(re.sub(r'^\s+\d+\s?', '', l) for l in text.splitlines() if l.startswith('  '))
                for line in text.splitlines():
                    if not line or line.startswith('  '):
                        continue
                    structure, gloss = line.split('|', 1)
                    bits = structure.split()
                    offset, lex_file, pos = bits[:3]
                    count = int(bits[3], 16)
                    lemmas = [re.sub(r'\((?:a|p|ip)\)$', '', bits[4+2*i]) for i in range(count)]
                    cursor = 4+2*count
                    pointer_count = int(bits[cursor]); cursor += 1
                    pointers = []
                    for _ in range(pointer_count):
                        symbol, target, target_pos, member = bits[cursor:cursor+4]
                        pointers.append({'symbol': symbol, 'offset': target, 'pos': target_pos, 'source_target': member})
                        cursor += 4
                    sid = f'wn31:{pos}:{offset}'
                    record = {'sense_id': sid, 'pos': pos, 'lemmas': lemmas,
                              'gloss': gloss.strip(), 'pointers': pointers, 'lexicographer_file': lex_file}
                    self.senses[sid] = record
                    for lemma in lemmas:
                        self.by_lemma[lemma.replace('_', ' ').lower()].append(sid)

    def lookup(self, word):
        forms = {word.lower(), word.lower().replace('-', ' ')}
        ids = set()
        for form in forms:
            ids.update(self.by_lemma.get(form, []))
        # Sorting by opaque ID does not import WordNet's frequency ranking.
        return [self.senses[x] for x in sorted(ids)]

    def adjectives(self, word):
        return [x for x in self.lookup(word) if x['pos'] in ('a', 's')]

    def packet(self, word):
        return [{k: record[k] for k in ('sense_id', 'pos', 'lemmas', 'gloss')} for record in self.lookup(word)]
