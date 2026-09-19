# Grounded-answer replay fixtures

`grounded-qa-v1.json` contains structured answers for synthetic or reviewed public passages only.
Records are keyed by the stable SHA-256 fingerprint produced by the application; raw questions
and passages are not duplicated in the fixture. Replay responses are always labelled as replay
data by the provider result and must never be presented as a live answer.
