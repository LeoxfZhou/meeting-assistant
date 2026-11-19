# Engineering Notes

## Provider compatibility

A real generation request rejected legacy `max_tokens` with HTTP400. The client defaults to `max_completion_tokens`, omits unsupported optional temperature settings and retains an explicit legacy parameter option. Mock responses alone cannot establish provider compatibility.

## Evidence reconstruction

Real conversational transcripts exposed rewritten or concatenated model quotes. Whitespace restoration alone was insufficient. The model now selects bounded source-line ranges, and the server reconstructs the original evidence; invalid ranges remain errors. Development meetings were excluded from the final holdout. Reliable source reconstruction does not remove false positives: the measured baseline remains low precision.

## RAG no-answer

A response returned `no_answer=true` with an empty answer, violating the schema. The prompt now requires a nonempty refusal explanation; the schema was not weakened. The original six-question result remains5/6, with the repaired case reported separately rather than replacing the initial measurement.

## Transactions and review

Task creation requires an authenticated review operation. Candidate revision checks, row locks and a unique source-candidate constraint prevent stale or duplicate confirmation. Database failure tests verify rollback; review state persists in PostgreSQL rather than an in-memory workflow pause.

## Deployment and persistence

Docker CLI availability did not imply a running daemon/database. Tests distinguish dependency availability from application failure. On ECS, Docker Hub connectivity failed; official-source amd64 images were transferred over SSH instead of using an unknown mirror. Named-volume survival was verified after container recreation and host reboot.

## Mainland ECS connectivity

Direct `api.openai.com:443` connections timed out without an HTTP response. This did not establish an API-key or quota error. Real generation was validated on the development Mac; mainland ECS validated infrastructure only. No region-access workaround or additional provider was introduced. The cloud demo was intentionally removed after validation.
