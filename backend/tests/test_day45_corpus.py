import json
import shutil

import pytest

from scripts.build_day45_corpus import MAX_WORDS, ROOT, SCENARIOS, build_corpus, serialize, source_sections


def test_frozen_corpus_reproduces_with_traceable_sources():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    sources = {source["scenario"]: source for source in manifest["sources"]}
    corpus = build_corpus()
    assert serialize(corpus) == (ROOT / "chunks.json").read_text(encoding="utf-8")
    assert {chunk["scenario"] for chunk in corpus["chunks"]} == SCENARIOS
    assert len({chunk["chunk_id"] for chunk in corpus["chunks"]}) == len(corpus["chunks"]) == 6
    for chunk in corpus["chunks"]:
        source = sources[chunk["scenario"]]
        assert chunk["source_title"] == source["title"]
        assert chunk["source_sha256"] == source["sha256"]
        assert chunk["references"] == source["references"]
        assert chunk["references"]
        assert chunk["text"] in " ".join((ROOT / chunk["source_path"]).read_text(encoding="utf-8").split())


def test_long_sections_split_without_losing_words():
    words = [f"term-{i}" for i in range(MAX_WORDS * 2 + 1)]
    chunks = list(source_sections("# Title\n\n## Section\n\n" + " ".join(words)))
    assert [heading for heading, _ in chunks] == ["Section"] * 3
    assert [len(body.split()) for _, body in chunks] == [MAX_WORDS, MAX_WORDS, 1]
    assert [word for _, body in chunks for word in body.split()] == words


def test_corpus_rejects_unlisted_files_and_edits(tmp_path):
    root = tmp_path / "corpus"
    shutil.copytree(ROOT, root)
    extra = root / "sources" / "unrelated.md"
    extra.write_text("Unapproved text", encoding="utf-8")
    with pytest.raises(ValueError, match="source inventory"):
        build_corpus(root)
    extra.unlink()
    (root / "sources" / "brute_force.md").write_text("Edited source", encoding="utf-8")
    with pytest.raises(ValueError, match="source hash mismatch"):
        build_corpus(root)
