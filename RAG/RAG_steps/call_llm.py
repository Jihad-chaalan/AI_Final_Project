from google import genai
from google.genai import types

def generate_answer(prompt, api_key):
    """
    Generate answer using Gemini API.
    Args:
        prompt: User's question or input text
        api_key: Gemini API key  
    Returns: Generated answer from LLM
    """
    print("\n" + "=" * 25)
    print("STEP 8: Generate answer with LLM")
    print("=" * 25)
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    print("\nSending request to Gemini...")
    print(f"  - Prompt length: {len(prompt)} characters")

    try:
        # Call Gemini API (text generation)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500
            )
        )

        # Extract the text from the response
        answer = response.text.strip() if hasattr(response, "text") else str(response)
        
        print("Answer generated successfully")
        print(f"  - Response length: {len(answer)} characters")
        print("Answer: \n", answer)
        return answer

    except Exception as e:
        error_msg = f"Error calling Gemini API: {e}"
        print(f"✗ {error_msg}")
        return error_msg
