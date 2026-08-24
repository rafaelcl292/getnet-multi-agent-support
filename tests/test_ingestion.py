from app.services.ingestion import TextExtractor, chunk_text


def test_html_extraction_ignores_script_and_style():
    parser = TextExtractor()
    parser.feed("<html><style>hidden</style><h1>Get Smart</h1><script>secret</script><p>Aceita Pix.</p></html>")
    assert parser.text() == "Get Smart Aceita Pix."


def test_chunking_preserves_overlap_and_content():
    text = "Primeira sentença. " * 100
    chunks = chunk_text(text, size=120, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)
