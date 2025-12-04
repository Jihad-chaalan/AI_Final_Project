def retrieve_relevant_chunks(query_embedding, collection, top_k=3):
    """
    Search vector database for most relevant chunks.
    Args:
        query_embedding: Query vector
        collection: ChromaDB collection
        top_k: Number of results to return
    Returns: Dictionary with retrieved documents, distances, and metadata
    """
    print("\n" + "=" * 25)
    print("STEP 6: Retrieve Relevant Chunks")
    print("=" * 25)
    print(f"Searching for top {top_k} most relevant chunks...")
    
    # Query the collection
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    
    print(f"✓ Retrieved {len(results['documents'][0])} chunks")
    print("\nRetrieved chunks (ranked by relevance):")
    print("-" * 60)
    
    for i, (doc, distance, metadata) in enumerate(zip(
        results['documents'][0],
        results['distances'][0],
        results['metadatas'][0]
    )):
        similarity = 1 - distance  # Convert distance to similarity
        
        print(f"\nChunk {i + 1} (Similarity: {similarity:.3f})")
        print(f"Source: {metadata['source']}")
        print(f"Preview: {doc[:150]}...")
        print("-" * 60)
    
    return results