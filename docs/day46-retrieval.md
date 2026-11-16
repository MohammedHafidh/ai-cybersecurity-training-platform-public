# Day 46 semantic retrieval

The retriever uses the six frozen [Day 45 corpus chunks](day45-rag-corpus.md). The [all-MiniLM-L6-v2 Sentence Transformer](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) embeds each chunk's title, section and text on CPU into a normalized 384-dimensional vector. FAISS performs exact inner-product search, equivalent to cosine ranking over these normalized vectors.

The saved [index metadata](../data/knowledge/day46/index.json) pins the model revision, corpus hash, index hash and ordered chunk IDs. A row maps back to the corresponding frozen chunk. Results include the chunk ID, scenario, section, text, similarity score and source references. Similarity scores rank the training notes. They are independent of the rule and ML predictions.

From the repository root, in a Python environment set up for retrieval:

```text
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.15.0+cpu
python -m pip install -r requirements/day46.txt pytest
python scripts/day46_retrieval.py build
python scripts/day46_retrieval.py search "Could repeated failed SSH password logins point to brute force?" --top-k 2
python -m pytest -q backend/tests/test_day46_retrieval.py
```

The build downloads the pinned embedding model on first use. Searching uses the cached model and the saved index. The default is two results, bounded by corpus size. Keep the index and metadata together and use the repository's trusted artifacts.

Hosted CI rebuilds a temporary index, compares the vectors with the saved index, and checks ranking and citations for the three lab scenarios. Retrieval runs independently of Ollama. Day 46 exposes retrieval through the local CLI and Python class. The explanation endpoint continues to use stored detection evidence.

## Solo relevance review

| Query | Top two chunks in order | Why they help |
| --- | --- | --- |
| Could repeated failed SSH password logins point to brute force? | `brute_force:01`, `brute_force:02` | Defines online guessing, then connects failures to the lab rule and its limitations. |
| Do SQL injection token matches prove that a database query changed? | `sql_injection:02`, `sql_injection:01` | Gives the rule's evidence limit first, then explains how SQL injection relates to query meaning. |
| What do connections to several destination ports indicate during network service discovery? | `reconnaissance:01`, `reconnaissance:02` | Gives discovery context and then explains the logged-port threshold and visibility limits. |

Both results matched the intended scenario in all three checks. This is a relevance smoke test over six English chunks. The retriever ranks the nearest chunks even when the query is outside the corpus scope.
