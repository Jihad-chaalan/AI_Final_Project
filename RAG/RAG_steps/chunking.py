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


def chunk_documents(documents, chunk_size=500, overlap=50):
    print("\n" + "=" * 25)
    print("STEP 2: Chunking Documents")
    print("=" * 25)
    print(f"Chunk size: {chunk_size} characters")
    print(f"Overlap: {overlap} characters")

    all_chunks = []

    for doc_idx, doc in enumerate(documents):
        #chunk the document
        chunks = chunk_text(doc['content'], chunk_size,overlap)

        #Add metadata to each chunk

        for chunk_idx, chunk in enumerate(chunks):
           all_chunks.append({
                'text': chunk,
                'source': doc['source'],
                'doc_id': doc_idx,
                'chunk_id': chunk_idx,
                'chunk_length': len(chunk)
            })
           
        print(f"Document {doc_idx + 1}: {doc['source']}")
        print(f"  - Created {len(chunks)} chunks")

    print(f"\nTotal chunks created: {len(all_chunks)}")

    return all_chunks
    