def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0

    while start < len(text):
        #GEt chunk
        end = start + chunk_size
        chunk = text[start:end]

        chunks.append(chunk.strip())
        start = end - overlap 

    return chunks