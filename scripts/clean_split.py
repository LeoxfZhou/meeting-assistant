"""Create a manifest-only derived split. Raw archives are never rewritten."""
import hashlib
import json
from pathlib import Path
from scripts.audit_alimeeting4mug import DEFAULT_ARCHIVE, inspect_archive

OUTPUT = Path('data/processed/clean_split.json')


def main():
    _, stats, _, _, inventory, _, _ = inspect_archive(DEFAULT_ARCHIVE)
    meetings = []
    for row in inventory:
        excluded = row['split']=='Train' and row['meeting_key']=='M3298'
        meetings.append({'original_split':row['split'], 'meeting_key':row['meeting_key'],
                         'included':not excluded, 'reason':'near-duplicate of Dev:M8016' if excluded else None,
                         'transcript_sha256':row['transcript_sha256']})
    manifest = {'schema_version':1,'archive_sha256':hashlib.sha256(DEFAULT_ARCHIVE.read_bytes()).hexdigest(),
        'policy':'Keep Dev M8016; exclude Train M3298 from training and prompt examples. Preserve Test1. No raw edits.',
        'evidence':{'train':'M3298','dev':'M8016','shared_long_sentences':40,'sequence_similarity':0.877,
                    'source':'outputs/audits/data_audit.md'},
        'limitations':['Other semantic near-duplicates have not been exhaustively excluded.','Explicit empty labels may require semantic review.'],
        'counts':{name:sum(m['included'] and m['original_split']==name for m in meetings) for name in stats},
        'meetings':meetings}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps({'manifest':str(OUTPUT),'counts':manifest['counts']},ensure_ascii=False))


if __name__=='__main__': main()
