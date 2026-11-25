from app.ingest.chunker import chunk_file


def test_chunk_coverage_overlap_and_no_empty_chunks():
    content = "\n".join(f"line {i}" for i in range(1, 181))
    chunks = chunk_file(content)
    assert chunks[0][0] == 1
    assert chunks[-1][1] == 180
    assert all(start <= end for start, end, text in chunks)
    assert all(text for _, _, text in chunks)
    assert chunks[1][0] == 66
    assert chunks[0][1] == 80
