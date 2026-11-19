# PUBLIC RELEASE AUDIT — 2026-11-19

PUBLIC_READY = NO
DATASET_LICENSE_VERIFIED = NO

## Security / history

Current tracked tree and all reachable Git history checked (209 distinct pre-change blobs), including tags. Known local secret values checked in memory without printing them; private-key/OpenAI/AWS/Alibaba/GitHub credential patterns, private paths and large blobs scanned. No real secret found. Keyword review distinguishes CI ephemeral credentials, example placeholders, runtime Authorization construction and synthetic test values from real credentials. Supplemental private-key hit in scripts/audit_public_repo.py is its scanner regex, not a key. No rotation or history rewrite indicated by these findings. Detection is not a guarantee against unknown secrets.

.env is ignored and not tracked; raw/processed/outputs/models/virtualenv/cache/DB files are excluded. No SSH private key, cloud credential, personal email outside author metadata or public server IPv4 found. Current Markdown local-link targets resolve. External URL availability is not claimed as exhaustively verified; localhost links are explicitly local quick-start instructions.

## Privacy

Historical docs/MASTER_GOAL.md visible in commit 0783cc491ef67cb6e3c9d457fe98352cd5d0f1ad contains a personal local project path. Current tree has removed it. This path is not a credential; do not rewrite the entire history solely for this non-secret development-path disclosure. Public GitHub identity and non-secret SSH alias are intentional; /opt/meeting-assistant is a generic deployment path.

## Dataset / outputs

No raw ZIP/CSV/JSON, models, dumps, large logs or restricted processed dataset tracked in tree/history. Exact AliMeeting sentence >=40-character matching across history found none; partial/semantic copying is not exhaustively detected. Original P0 audit and complete predictions/bad cases remain local and ignored, never deleted. README links evaluation/evidence/data_audit_public.md; safe bad-case index contains IDs/counts/analysis, not transcript quotes. outputs/audits/data_audit_public.md also remains available locally.

Existing project materials do not reliably establish dataset source revision/license/redistribution terms. Raw data is not redistributed and MIT does not license it. Remaining blocker: resolve the declared dataset provenance/license review before clearing the repository's public-release gate. Do not guess a dataset license.

## License / claims

Added MIT for original repository code and original synthetic documents, Copyright 2026 LeoxfZhou. No conflicting notice identified in project source; third-party packages/models retain their own licenses. This is not a comprehensive legal opinion about all transitive dependencies.

README remains recruiter-oriented and retains actual P/R/F1 (4.79%/43.66%/8.64%), N30, Synthetic RAG N25/answerable22, Hit@5=Recall@5=1 and MRR0.893939. P0 counts442/302332/1472 and tests82 are evidence-backed. No production/HTTPS/always-online or ECS OpenAI success claim. ECS project was intentionally removed while Ubuntu/Docker/Git/SSH/Swap remained.

## Validation

Full pytest and synthetic RAG reproduction rerun without cloud LLM calls; detailed fresh results recorded below after execution. Dataset audit rerun to separate outputs/checks paths, preserving original evidence. No paid Generation calls made. GitHub PR/CI are the final merge gate. Existing v0.9.0-interview-demo tag must remain at d534c85154bb0e3de108edcaa8d0466f7253fecc; newer MIT/public-audit changes are on main only.

Fresh validation: 82 passed in17.92s; regenerated442-meeting inventory equals preserved P0 inventory; Synthetic RAG report equals frozen evidence (N25/22 answerable, Hit@5=Recall@5=1, MRR0.893939). Current Markdown local-link check found no broken target.
