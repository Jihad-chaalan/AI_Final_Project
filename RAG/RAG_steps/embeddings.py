from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_embedder(model_name="all-MiniLM-L6-v2"):
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model

def embed_texts(texts):
    """Return list of vectors (numpy arrays) for a list of texts."""

    model = get_embedder()

    # Create embeddings
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32
        )
    
    # print(f"✓ Embeddings created")
    # print(f"  - Shape: {embeddings.shape}")
    # print(f"  - Each chunk is now a {embeddings.shape[1]}-dimensional vector")
    
    return embeddings