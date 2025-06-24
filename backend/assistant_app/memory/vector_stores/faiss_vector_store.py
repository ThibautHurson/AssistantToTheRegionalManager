import faiss
import numpy as np
import os
from sentence_transformers import SentenceTransformer
import json

class VectorStoreManager:
    def __init__(self, 
                 index_path="backend/assistant_app/memory/vector_stores/faiss_index.bin", 
                 mapping_path="backend/assistant_app/memory/vector_stores/faiss_mapping.json", 
                 model_name='all-MiniLM-L6-v2'):
        self.index_path = index_path
        self.mapping_path = mapping_path
        self.model = SentenceTransformer(model_name)
        
        # Get the embedding dimension from the model
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        self.index = None
        self.doc_mapping = {}  # Maps index ID to document content
        self.next_doc_id = 0

        self._load()

    def _load(self):
        # Load the FAISS index
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            # Load the document mapping
            if os.path.exists(self.mapping_path):
                with open(self.mapping_path, 'r') as f:
                    self.doc_mapping = {int(k): v for k, v in json.load(f).items()}
                self.next_doc_id = max(self.doc_mapping.keys()) + 1 if self.doc_mapping else 0
            else:
                # If mapping is missing, the index is out of sync. Reset.
                print("Warning: Index found but mapping is missing. Resetting index.")
                self._reset_index()
        else:
            # If index doesn't exist, create a new one
            self._reset_index()

    def _save(self):
        # Save the FAISS index
        faiss.write_index(self.index, self.index_path)
        # Save the document mapping
        with open(self.mapping_path, 'w') as f:
            json.dump(self.doc_mapping, f)

    def _reset_index(self):
        # Initializes or resets the FAISS index
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.doc_mapping = {}
        self.next_doc_id = 0

    def add_documents(self, documents: list[str]):
        if not documents:
            return
            
        # Generate embeddings
        embeddings = self.model.encode(documents, convert_to_tensor=False)
        
        # Add embeddings to FAISS index
        self.index.add(np.array(embeddings, dtype='float32'))
        
        # Update document mapping
        for doc in documents:
            self.doc_mapping[self.next_doc_id] = doc
            self.next_doc_id += 1
            
        self._save()

    def search(self, query: str, k: int = 5, threshold: float = 0.9) -> list[str]:
        if not query or self.index.ntotal == 0:
            return []
        query_embedding = self.model.encode([query], convert_to_tensor=False)
        distances, indices = self.index.search(np.array(query_embedding, dtype='float32'), k)
        results = []
        for dist, i in zip(distances[0], indices[0]):
            if i == -1 or i not in self.doc_mapping:
                continue
            # Since we are using L2 distance, the smaller the distance, the more similar the documents are.
            if threshold is not None and dist > threshold:
                continue  # Skip if distance is too large (not similar enough)
            results.append(self.doc_mapping[i])
        return results

    def get_all_documents(self) -> list[str]:
        return list(self.doc_mapping.values()) 