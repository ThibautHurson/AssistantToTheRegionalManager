import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.assistant_app.utils.logger import memory_logger

class VectorStoreManager:
    def __init__(self,
                 user_id: str = None,
                 base_path="backend/assistant_app/memory/vector_stores",
                 model_name='all-MiniLM-L6-v2'):
        self.user_id = user_id
        self.base_path = base_path

        # Create user-specific paths
        if user_id:
            self.index_path = f"{base_path}/faiss_index_{user_id}.bin"
            self.mapping_path = f"{base_path}/faiss_mapping_{user_id}.json"
        else:
            # Fallback to global store for backward compatibility
            self.index_path = f"{base_path}/faiss_index.bin"
            self.mapping_path = f"{base_path}/faiss_mapping.json"

        self.model = SentenceTransformer(model_name)

        # Get the embedding dimension from the model
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        self.index = None
        self.doc_mapping = {}  # Maps index ID to document content
        self.next_doc_id = 0

        self._load()

    def _load(self):
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

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
                memory_logger.log_warning("Index found but mapping is missing, resetting index", {
                    "user_id": self.user_id
                })
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
            # Since we are using L2 distance, the smaller the distance,
            # the more similar the documents are.
            if threshold is not None and dist > threshold:
                continue  # Skip if distance is too large (not similar enough)
            results.append(self.doc_mapping[i])
        return results

    def get_all_documents(self) -> list[str]:
        return list(self.doc_mapping.values())

    def clear_user_data(self):
        """Clear all data for the current user."""
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.mapping_path):
            os.remove(self.mapping_path)
        self._reset_index()
