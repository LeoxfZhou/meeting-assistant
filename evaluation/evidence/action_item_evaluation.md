# Action Item Evaluation — frozen small holdout

30 Test1 meetings; seed 20261119; 6 strata (empty / 1–2 / >2 action IDs × shorter / longer than eligible median sentence count), 5 per stratum. This deliberately balanced diagnostic sample is not a representative population estimate. Candidate pool is 77 Test1 meetings after excluding five previously inspected smoke meetings. Those five are development-only: ['M2777', 'M2992', 'M3322', 'M2999', 'M3229'].

Known leakage: Train M3298 is excluded; Dev M8016 retained (40 shared long sentences, SequenceMatcher 0.877). Raw archive unchanged; clean split Train294/Dev65/Test1 82. Other semantic near-duplicates have not been exhaustively excluded. No AliMeeting data entered RAG. Five clean Train meetings were used for smoke; final Test1 prompts/code were frozen before inference and not tuned on final scores.

## Measured result

TP=31, FP=616, FN=40.
Micro Precision=0.04791345, Recall=0.43661972, F1=0.08635097.
Failed meetings=2; HTTP attempts=75; failed transport/non-200 attempts=11; retries=9.
Input/output/total reported tokens=301895/78886/380781; sum HTTP latency=1097247ms; estimated_cost=null. Failed requests without usage may still have unknown provider-side cost. Model: gpt-6-luna.

## Metric and alignment

Identity is (meeting_id, sentence_id). TP=predicted∩gold; FP=predicted−gold; FN=gold−predicted. P=TP/(TP+FP), R=TP/(TP+FN), F1=2PR/(P+R); zero denominator gives zero. Explicit empty-label meetings remain in evaluation; extra predictions count FP. A failed meeting counts empty predictions, never removed from the denominator.

Production app.llm.extraction.extract uses 6000-character windows / 300 overlap. Prompt numbers lines; validated inclusive start/end reconstruct exact original evidence, not model-written quotes. Legacy quotes can only restore whitespace when uniquely matched, never fuzzy words; one bounded evidence correction allowed. All surviving evidence is matched exactly against newline-joined original sentences; every overlapping sentence at every exact occurrence is included, then IDs deduplicated per meeting. Broad evidence can increase FP; this is a known conservative alignment limitation, not manually adjudicated accuracy.

No reliable task/assignee/deadline Gold exists: no field accuracy is reported. Qualitative review remains separate. The observed scores describe this model, prompt, subset and alignment only; they do not establish general meeting understanding or business impact.

## Reproduction

Acquire the same dataset lawfully; archive SHA256=666899476df91a0791b3b5e83994463c2a40e83d6d02e2b50cf2d32a556fec70.
Run scripts.clean_split; inspect evaluation/action_item_eval_manifest.jsonl (SHA256=556015ad80551699964b67ca51079ccd2d7d0d2513fe54f74b545ce1f2daf367). scripts.finalize_evaluation --stage select validates selection; --stage smoke runs Train, --stage final requires successful smoke and resumes missing meetings only. Existing results are not overwritten. To reproduce new stochastic inference, use a fresh output copy, preserve prior evidence, and expect nonidentical predictions.
Run `python -m scripts.report_final_evaluation` to recompute saved ID metrics without API calls. Provider requests/quotes remain local under outputs/evaluations; public evidence contains only counts, IDs and hashes. Source extraction SHA256=70570a5f808ae1b122458d6f50c2c944e51e182f60ed823797cd73e6663ac189.

## Development failures retained

Original 5 Test1 smoke meetings all failed evidence validation and were removed from final eligibility; whitespace/repair-only Train experiment still had failures. Final line-ID design passed 5 Train smoke meetings. These runs are not part of final30 and their token usage is reported separately in run_accounting.json. No test-set result was silently rerun to inflate F1.
