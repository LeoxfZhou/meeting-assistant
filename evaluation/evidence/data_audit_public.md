# AliMeeting4MUG P0 public summary

Read-only audit: 442 meetings, 302332 sentences, 1472 action IDs, 109 explicitly empty labels.

| Split | Meetings | Sentences | Action IDs | Empty |
|---|---:|---:|---:|---:|
| Train |295|213235|1014|67|
| Dev |65|45869|222|10|
| Test1 |82|43228|236|32|

Archive SHA256: 666899476df91a0791b3b5e83994463c2a40e83d6d02e2b50cf2d32a556fec70.
Outer ZIP contains three ZIP/TSV/JSON partitions. CRC and schema validation passed; no missing action sentence IDs or exact duplicate transcripts. Train M3298 and Dev M8016 share 40 long sentences, SequenceMatcher similarity 0.877. Derived clean manifest excludes Train M3298, retains Dev M8016; raw unchanged. Other semantic near-duplicates not exhaustively ruled out.

Reproduce using scripts/audit_alimeeting4mug.py and scripts/clean_split.py with a lawfully obtained matching archive. This summary contains no original transcript. Full audit and dataset remain ignored. Dataset redistribution license requires manual verification before repository is made public.
