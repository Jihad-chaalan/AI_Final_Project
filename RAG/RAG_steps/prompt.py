def prepare_prompt(query, retrieved_chunks):
    """
    Prepare a prompt
    Args:
        query: User's question
        retrieved_chunks: List of relevant document chunks
    Returns: Prompt
    """
    print("\n" + "=" * 25)
    print("STEP 7: Prepare a prompt")
    print("=" * 25)
    
    # Build context from retrieved chunks
    context = ""
    for i, chunk in enumerate(retrieved_chunks):
        context = context + "\n\n" + f"[Context {i+1}]:\n{chunk}"
    
    # Create prompt
    prompt = f"""You are a helpful AI assistant that answers questions based on the provided context.
        Context:
        {context}

        Question: {query}

        Instructions:
        - Answer the question based ONLY on the information in the context above
        - If the context doesn't contain enough information to answer the question, say so honestly
        - Be concise and accurate
        - Cite which context section(s) you used (e.g., [Context 1], [Context 2])
        - Do not make up information that is not in the context

        Answer:
        """
    
    print("Prompt: \n", prompt)
    return prompt