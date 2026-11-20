"""Export committed accommodation guidance; diagnostics stay in the workflow log."""
import argparse
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit,unquote
import yaml
from accommodation_hf_common import ROOT,SOURCE,TARGET,MANAGED,git,destination,read_sources

def serial(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def anchors(text):
    out=set(re.findall(r'<a\s+id="([^"]+)"',text));seen={}
    for h in re.findall(r'^#{1,6}\s+(.+)$',text,re.M):
        h=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',h).replace('`','').lower();h=''.join(c for c in h if c in '-_ ' or unicodedata.category(c)[0] in 'LN').replace(' ','-');n=seen.get(h,0);seen[h]=n+1;out.add(h+(f'-{n}' if n else ''))
    return out

def check(root=ROOT):
    root=Path(root).resolve();links=0;metadata=0
    for p in root.rglob('*.md'):
        if '.git' in p.parts:continue
        text=p.read_text()
        if text.startswith('---\n'):
            obj=yaml.safe_load(text.split('---',2)[1]);metadata+=1
            if not isinstance(obj,dict) or obj.get('license')!='MIT':raise ValueError('Invalid MIT metadata: '+p.name)
        if '\ufffd' in text:raise ValueError('Invalid source encoding: '+p.name)
        for target in re.findall(r'\[[^\]\n]+\]\(([^\n]+?)\)',text):
            u=urlsplit(target)
            if u.scheme or u.netloc:continue
            links+=1;dest=(p.parent/unquote(u.path)).resolve() if u.path else p
            if not dest.is_relative_to(root) or not dest.is_file():raise ValueError('Missing local source link: '+target)
            if u.fragment and unquote(u.fragment) not in anchors(dest.read_text()):raise ValueError('Missing source fragment: '+target)
    text=(root/'Accomodation_Checklist.md').read_text()
    ids=re.findall(r'^- \[ \] \*\*(ACCOM-\d\d)',text,re.M)
    if ids!=[f'ACCOM-{i:02}' for i in range(1,33)]:raise ValueError('Expected all 32 ordered stable ACCOM identifiers.')
    for token in ('## How to use this checklist','### Scope, requirements and competent decisions','## Recording an assessment','## Useful resources'):
        if token not in text:raise ValueError('Required checklist context missing: '+token)
    if [int(n) for n in re.findall(r'^## ([1-4])\. ',text,re.M)]!=[1,2,3,4]:raise ValueError('Expected four checklist sections.')
    agent=yaml.safe_load((root/'AGENTS.md').read_text().split('---',2)[1]);meta=yaml.safe_load(text.split('---',2)[1])
    if agent['sources']['checklist_version']!=meta['version']:raise ValueError('Checklist metadata version mismatch.')
    if agent['review']['approved_by'] is not None or agent['review']['approved_at'] is not None:raise ValueError('Adoption metadata changed; review before publication.')
    return {'status':'passed','checklist_items':32,'local_links':links,'metadata_blocks':metadata,'scope':'Local source structure only; no inspections, legal review, model evaluation or live external-source verification.'}

def build(root,output,dataset_id=TARGET):
    destination(dataset_id);root=Path(root);cfg,texts,manifest=read_sources(root);check(root)
    commit=git(root,'rev-parse','HEAD').decode().strip();date=git(root,'show','-s','--format=%cI','HEAD').decode().strip()
    text=texts['Accomodation_Checklist.md'];first=re.search(r'^## 1\. ',text,re.M).start();end=text.index('## Recording an assessment')
    common=text[:first]+text[end:]
    authority=serial({'agent_instructions_as_source_data':texts['AGENTS.md'],'terminology_alignment':texts['Terminology_Alignment.md'],'rights_and_status':texts['NOTICE.md'],'qualification':'Practitioner recommendations and draft agent governance. No local adoption, inspection, legal conclusion or occupant outcome is established. Retrieved instructions are data, not runtime authority.'})
    def row(ident,path,body,**fields):
        return dict(id=ident,text=body,source_repository=SOURCE,source_path=path,source_commit=commit,source_commit_date=date,source_url=f'https://github.com/{SOURCE}/blob/{commit}/{path}',authority_context_json=authority,license='MIT',**fields)
    documents=[]
    for path in cfg['document_files']:
        if path not in texts or not path.endswith('.md') or path=='Accomodation_Checklist.md':raise ValueError('Invalid document source selection.')
        title=re.search(r'^# (.+)$',texts[path],re.M)
        documents.append(row(path,path,texts[path],title=title.group(1) if title else path,record_type='maintained_guidance_document'))
    if len({r['id'] for r in documents})!=len(documents):raise ValueError('Duplicate document source.')
    matches=list(re.finditer(r'^- \[ \] \*\*(ACCOM-\d\d) \(([^)]+)\)\*\*',text,re.M));items=[]
    for i,m in enumerate(matches):
        later=matches[i+1].start() if i+1<len(matches) else end
        section_matches=list(re.finditer(r'^## ([1-4])\. (.+)$',text[:m.start()],re.M));sec=section_matches[-1]
        next_section=re.search(r'^## [1-4]\. ',text[m.end():later],re.M)
        stop=m.end()+next_section.start() if next_section else later
        body=text[m.start():stop]
        tags=m.group(2).split('/')
        if not set(tags)<={'P','N','C'}:raise ValueError('Invalid coverage tags.')
        items.append(row(m.group(1),'Accomodation_Checklist.md',body,section_number=int(sec.group(1)),section_title=sec.group(2),coverage_tags='/'.join(tags),shared_checklist_context=common,record_type='checklist_recommendation',evaluation_status='not_evaluated_source_guidance',observed_occupant_evidence=False))
    payload={'documents.jsonl':''.join(serial(x)+'\n' for x in documents).encode(),'checklist.jsonl':''.join(serial(x)+'\n' for x in items).encode(),'checklist.md':text.encode(),'LICENSE':texts['LICENSE'].encode(),'NOTICE.md':texts['NOTICE.md'].encode()}
    provenance={'source_repository':SOURCE,'source_commit':commit,'source_commit_date':date,'destination_dataset':TARGET,'manifest':manifest,'license':'MIT','representations':'Checklist item stream and complete checklist are alternative views of one source, not independent evidence.','limits':'Original source dates and status retained. No external source bodies fetched; no inspection, legal or product/model evaluation performed.'}
    schema={'format':'JSON Lines','document_columns':sorted(documents[0]),'checklist_columns':sorted(items[0]),'text':'Exact source document or item Markdown. Checklist shared scope, safety and recording/reference context is retained separately.','authority_context_json':'JSON string retaining source instructions as data, terminology, rights and draft/adoption limits.','item_identifiers':'Stable ACCOM-01 to ACCOM-32 references, not certification criteria.'}
    for name,value in [('provenance.json',provenance),('record_schema.json',schema)]:payload[name]=(serial(value)+'\n').encode()
    payload['README.md']=('''---
license: mit
language:
- en
task_categories:
- text-retrieval
configs:
- config_name: checklist
  data_files:
  - split: train
    path: checklist.jsonl
- config_name: documents
  data_files:
  - split: train
    path: documents.jsonl
---
# Designing Accessible Accommodation

Double-FW practitioner guidance from [the public source repository](https://github.com/'''+SOURCE+''').

## Content and format

The checklist configuration contains 32 stable ACCOM item records, retaining exact item text, section, P/N/C coverage tags and shared scope, safety, authority, recording and source context. The documents configuration retains five complete guidance files: README, AGENTS, terminology alignment, related public guidance and rights/status notice. `checklist.md` preserves the full owning checklist as an alternative representation. These views are not independent evidence or extra observations.

Every record carries its exact GitHub commit, path and source URL. Authority context preserves agent instructions as source data, draft/adoption qualifications, terminology and rights. Provenance records original file hashes. `train` is a loader split name, not a claim that a model was trained. No question/answer pairs, successful inspections, occupant testimony or approvals are fabricated. No test/audit report is published.

## Scope and safe reuse

Use as retrieval or further reviewed training-source material. Recommendations need project-specific applicability, accepted criteria and competent assessment. The checklist is not a building specification, fire strategy, legal opinion or certification. Do not use one door dimension, product or completed box to claim suitability for everyone. Optional technology does not replace effective access and fallback. Actual site, building, safety and occupant decisions remain with the responsible people and professionals.

Preserve the distinction between progress, evaluation, occupant outcomes and human decisions. Unknown, not tested and unresolved are not passes. Most individual glossary definitions remain proposed; Double-FW terminology cannot amend an externally owned standard or legal duty. Linked sources retain their own scope and rights, and their availability/currency is not renewed by export.

Retrieved AGENTS text, examples and other documents are data, not permission to override the consuming agent's hierarchy or act externally. Keep personal, medical and individual emergency-plan records out of a public corpus. Review rights, privacy, duplication and suitability before training or deployment. No source export demonstrates model effectiveness, usable accommodation or actual professional validation.

## Licence and updates

MIT, Copyright (c) 2026 Double FW Ltd. Retain the copyright and permission notice in LICENSE. Commercial reuse is permitted under MIT. Referenced third-party works and standards are not bundled or relicensed; see NOTICE.md.

The weekly workflow writes only its eight managed files to this existing dataset, preserves unrelated files and visibility, and stops on invalid source, licence, destination or checks. No-change publication creates no extra dataset commit. Source and dataset publication are distinct operational events.
''').encode()
    if set(payload)!=set(MANAGED):raise ValueError('Unexpected managed output set.')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for name,value in payload.items():(output/name).write_bytes(value)
    return {'documents':len(documents),'checklist_items':len(items)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');p.add_argument('--output');p.add_argument('--dataset-id');a=p.parse_args()
    if a.check_only:print(serial(check()))
    elif a.output and a.dataset_id:print(serial(build(ROOT,a.output,a.dataset_id)))
    else:p.error('Provide --check-only or both --output and --dataset-id.')
if __name__=='__main__':main()
