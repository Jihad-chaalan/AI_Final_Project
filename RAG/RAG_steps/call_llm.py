from openai import OpenAI

def generate_answer(prompt, api_key):
    """
    Generate answer using DeepSeek API.
    Args:
        query: User's question
        retrieved_chunks: List of relevant document chunks
        api_key: DeepSeek API key  
    Returns: Generated answer from LLM
    """
    print("\n" + "=" * 25)
    print("STEP 8: Generate answer with LLM")
    print("=" * 25)
    
    # Initialize OpenAI client with DeepSeek endpoint
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    
    print("\nSending request to DeepSeek...")
    print(f"  - Prompt length: {len(prompt)} characters")
    
    # Call DeepSeek API
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        
        print("Answer generated successfully")
        print(f"  - Response length: {len(answer)} characters")
        print("Answer: \n", answer)
        return answer
        
    except Exception as e:
        error_msg = f"Error calling DeepSeek API: {e}"
        print(f"✗ {error_msg}")
        return error_msg