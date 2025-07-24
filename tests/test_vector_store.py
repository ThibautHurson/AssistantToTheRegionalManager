import os
import shutil
import tempfile
import pytest
from backend.assistant_app.memory.faiss_vector_store import VectorStoreManager


class TestVectorStoreManager:
    """Test cases for VectorStoreManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_vector_store_setup(self, mock_sentence_transformer, mock_faiss_index,
                               temp_dir, sample_user_email):
        """Setup mock vector store with common configuration."""
        # Configure mocks
        mock_sentence_transformer.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.encode.return_value = [[0.1] * 384, [0.2] * 384]
        mock_faiss_index.ntotal = 2
        mock_faiss_index.search.return_value = ([[0.5, 0.8]], [[0, 1]])
        return {
            'temp_dir': temp_dir,
            'user_email': sample_user_email,
            'mock_model': mock_sentence_transformer,
            'mock_index': mock_faiss_index
        }

    @pytest.mark.unit
    def test_vector_store_initialization(self, mock_sentence_transformer,
                                       mock_faiss_index, temp_dir,
                                       sample_user_email):
        """Test VectorStoreManager initialization."""
        # Setup mocks
        mock_sentence_transformer.get_sentence_embedding_dimension.return_value = 384
        # Simulate new index
        mock_faiss_index.read_index.side_effect = FileNotFoundError()
        # Execute
        vs_manager = VectorStoreManager(user_id=sample_user_email,
                                      base_path=temp_dir)
        # Assert
        assert vs_manager.user_id == sample_user_email
        assert vs_manager.embedding_dim == 384
        assert vs_manager.next_doc_id == 0
        assert vs_manager.doc_mapping == {}

    @pytest.mark.unit
    def test_add_documents(self, mock_vector_store_setup):
        """Test adding documents to vector store."""
        setup = mock_vector_store_setup
        setup['mock_index'].read_index.side_effect = FileNotFoundError()
        # Execute
        vs_manager = VectorStoreManager(user_id=setup['user_email'],
                                      base_path=setup['temp_dir'])
        documents = ["Test document 1", "Test document 2"]
        vs_manager.add_documents(documents)
        # Assert
        assert len(vs_manager.doc_mapping) == 2
        assert vs_manager.doc_mapping[0] == "Test document 1"
        assert vs_manager.doc_mapping[1] == "Test document 2"
        assert vs_manager.next_doc_id == 2
        setup['mock_index'].add.assert_called_once()

    @pytest.mark.unit
    def test_search_documents(self, mock_vector_store_setup):
        """Test searching documents in vector store."""
        setup = mock_vector_store_setup
        setup['mock_index'].read_index.side_effect = FileNotFoundError()
        # Execute
        vs_manager = VectorStoreManager(user_id=setup['user_email'],
                                      base_path=setup['temp_dir'])
        vs_manager.doc_mapping = {0: "Test doc 1", 1: "Test doc 2"}
        results = vs_manager.search("test query", k=2)
        # Assert
        assert len(results) == 2
        assert "Test doc 1" in results
        assert "Test doc 2" in results
        setup['mock_index'].search.assert_called_once()

    @pytest.mark.unit
    def test_search_empty_index(self, mock_sentence_transformer, mock_faiss_index,
                               temp_dir, sample_user_email):
        """Test searching empty vector store."""
        # Setup mocks
        mock_sentence_transformer.get_sentence_embedding_dimension.return_value = 384
        mock_faiss_index.ntotal = 0  # Empty index
        mock_faiss_index.read_index.side_effect = FileNotFoundError()
        # Execute
        vs_manager = VectorStoreManager(user_id=sample_user_email, base_path=temp_dir)
        results = vs_manager.search("test query")
        # Assert
        assert not results
        mock_faiss_index.search.assert_not_called()

    @pytest.mark.unit
    def test_clear_user_data(self, mock_sentence_transformer, mock_faiss_index,
                            temp_dir, sample_user_email):
        """Test clearing user data from vector store."""
        # Setup mocks
        mock_sentence_transformer.get_sentence_embedding_dimension.return_value = 384
        # Create temporary files to simulate existing index
        index_path = os.path.join(temp_dir, f"faiss_index_{sample_user_email}.bin")
        mapping_path = os.path.join(temp_dir, f"faiss_mapping_{sample_user_email}.json")
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("mock index data")
        with open(mapping_path, 'w', encoding='utf-8') as f:
            f.write('{"0": "test doc"}')
        # Configure mock to return the index when files exist
        mock_faiss_index.read_index.return_value = mock_faiss_index
        # Execute
        vs_manager = VectorStoreManager(user_id=sample_user_email, base_path=temp_dir)
        vs_manager.clear_user_data()
        # Assert
        assert not os.path.exists(index_path)
        assert not os.path.exists(mapping_path)
        assert vs_manager.doc_mapping == {}
        assert vs_manager.next_doc_id == 0

    @pytest.mark.unit
    def test_get_all_documents(self, mock_sentence_transformer, mock_faiss_index,
                              temp_dir, sample_user_email):
        """Test getting all documents from vector store."""
        # Setup mocks
        mock_sentence_transformer.get_sentence_embedding_dimension.return_value = 384
        mock_faiss_index.read_index.side_effect = FileNotFoundError()
        # Execute
        vs_manager = VectorStoreManager(user_id=sample_user_email, base_path=temp_dir)
        vs_manager.doc_mapping = {0: "Doc 1", 1: "Doc 2", 2: "Doc 3"}
        all_docs = vs_manager.get_all_documents()
        # Assert
        assert len(all_docs) == 3
        assert "Doc 1" in all_docs
        assert "Doc 2" in all_docs
        assert "Doc 3" in all_docs
