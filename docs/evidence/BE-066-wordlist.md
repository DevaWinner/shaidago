# BE-066 evidence: passphrase word list provenance

Reporter-handle passphrases are six words drawn uniformly from the EFF long word list (7776 words, about 77.5 bits for six words).

| Field | Value |
| --- | --- |
| Source | <https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt> (Electronic Frontier Foundation, "EFF's New Wordlists for Random Passphrases") |
| Retrieved | 2026-09-19 over HTTPS (HTTP 200, 108,800 bytes) |
| SHA-256 | `addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e` |
| Committed as | `services/platform/src/shaidago/reports/wordlists/eff_large_wordlist.txt`, unmodified |
| Licence | Creative Commons Attribution 3.0 United States (CC BY 3.0 US), attribution to the Electronic Frontier Foundation |
| Structure checked | 7776 lines, dice keys `11111` to `66666` in order, 7776 distinct words, first `abacus`, last `zoom` |

The file is unmodified so its hash can be compared with a fresh download. `tests/unit/reports/test_handles.py` fails if the committed file changes, has a duplicate word, or breaks the dice-key sequence.

## Review status

Fetched and structurally checked by the AI-assisted build. **No human has reviewed the list for offensive or confusable words or confirmed the licence terms.** Until a maintainer does, treat the list as unreviewed; the handle feature stays optional and off the anonymous path.
