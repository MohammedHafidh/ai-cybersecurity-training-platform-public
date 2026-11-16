# Day 45 explanation corpus v1

The frozen corpus provides background for learner-facing explanations of stored detection results. It contains three project-authored notes and six chunks. The [source manifest](../data/knowledge/day45/manifest.json) freezes the source list, purpose, SHA-256 hashes and reference attribution. The [chunk snapshot](../data/knowledge/day45/chunks.json) carries the scenario, source path, title, hash, references, and section with each chunk.

| Scenario | Security review |
| --- | --- |
| Brute force | Online guessing context comes from [MITRE ATT&CK T1110](https://attack.mitre.org/techniques/T1110/). The [authentication rule](day24-auth-rule.md) supplies the lab threshold and window. Failed authentication alone cannot establish successful access. |
| SQL injection | [OWASP's SQL Injection overview](https://community.owasp.org/attacks/SQL_Injection) and [prevention cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) supply the concept and defensive context. The [web rule](day25-sqli-recon-rules.md) uses token matches as indicators. They cannot establish query modification or data access. |
| Network reconnaissance | [MITRE ATT&CK T1046](https://attack.mitre.org/techniques/T1046/) supplies service-discovery context. The [network features](day19-network-features.md) and [network rule](day25-sqli-recon-rules.md) limit claims to observed accepted connections and destination ports. Legitimate multi-service activity can also flag. |

The solo security review compared the notes with the published references and frozen rule implementation. The notes paraphrase only directly relevant concepts. Full external pages, operational attack instructions, raw logs and unrelated scenarios are outside the source inventory. The chunker reads only the three pinned notes and performs no network requests.

Run `python scripts/build_day45_corpus.py --check` from the repository root to verify the frozen snapshot. Running the command without `--check` regenerates the snapshot from the same pinned sources. The builder uses source sections and splits long sections at 120 words. It normalizes source line endings to LF for hashing, emits stable IDs, and produces reproducible JSON. Changes to the reviewed text or scope require a new corpus version.

Day 45 delivers corpus preparation. The running explanation endpoint still uses stored detection evidence. Retrieval and model grounding from this corpus are subsequent work.
