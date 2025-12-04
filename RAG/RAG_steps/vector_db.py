import chromadb

_vector_db_client = None
_my_db_collection = None

def get_vector_db_client(persist_directory = "./chroma_persist"):
    global _vector_db_client

    if _vector_db_client is None:
        _vector_db_client = chromadb.PersistentClient(path=persist_directory)

    return _vector_db_client

def get_db_collection(my_db_collection_name = "my_demo_rag_collection"):
    global _my_db_collection
    
    if _my_db_collection is None:
        client = get_vector_db_client()
        existing_collections = [c.name for c in client.list_collections()]

        # Check if it exists
        if my_db_collection_name in existing_collections:
            _my_db_collection = client.get_collection(name=my_db_collection_name)
        else:
            _my_db_collection = client.create_collection(name=my_db_collection_name)

    return _my_db_collection
