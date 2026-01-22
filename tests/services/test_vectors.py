"""Tests for the vectors service."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


class TestVectorStore:
    """Tests for vector store operations."""

    @pytest.fixture
    def mock_chroma(self):
        """Create mock Chroma vector store."""
        mock = MagicMock()
        mock.add_documents = MagicMock()
        mock.delete = MagicMock()
        mock.get = MagicMock(return_value={"ids": []})
        mock.similarity_search_with_score = MagicMock(return_value=[])
        mock._collection = MagicMock()
        mock._collection.count = MagicMock(return_value=10)
        return mock

    @pytest.fixture
    def mock_embeddings(self):
        """Create mock embeddings."""
        mock = MagicMock()
        mock.embed_documents = MagicMock(return_value=[[0.1, 0.2, 0.3]])
        mock.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3])
        return mock

    def test_get_embeddings(self):
        """Test getting embeddings model."""
        with patch("services.vectors.OpenAIEmbeddings") as mock_embeddings_class:
            from services.vectors import get_embeddings

            get_embeddings()
            mock_embeddings_class.assert_called_once()

    def test_get_vector_store(self, mock_chroma):
        """Test getting vector store."""
        with patch("services.vectors.Chroma", return_value=mock_chroma):
            with patch("services.vectors.get_embeddings"):
                with patch("os.makedirs"):
                    from services.vectors import get_vector_store

                    store = get_vector_store()
                    assert store is not None

    def test_get_text_splitter(self):
        """Test getting text splitter."""
        from services.vectors import get_text_splitter

        splitter = get_text_splitter()
        assert splitter is not None
        assert splitter._chunk_size == 1000
        assert splitter._chunk_overlap == 200


class TestIngestDocument:
    """Tests for document ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_document(self, mock_vector_store):
        """Test ingesting a document."""
        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import ingest_document

            content = "# Test Document\n\nThis is test content for the document."
            result = await ingest_document(
                content=content,
                source_path="PersonalAI/Diary/2024-01-15.md",
                metadata={"folder": "Diary", "filename": "2024-01-15.md"},
            )

            # Should return number of chunks
            assert isinstance(result, int)
            assert result >= 0

    @pytest.mark.asyncio
    async def test_ingest_document_replaces_existing(self, mock_vector_store):
        """Test that ingesting replaces existing document."""
        # Mock existing documents
        mock_vector_store.get = MagicMock(return_value={"ids": ["existing-id-1", "existing-id-2"]})

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import ingest_document

            await ingest_document(
                content="New content",
                source_path="PersonalAI/Diary/existing.md",
            )

            # Should delete existing documents first
            mock_vector_store.delete.assert_called_once()


class TestDeleteDocument:
    """Tests for document deletion."""

    @pytest.mark.asyncio
    async def test_delete_existing_document(self, mock_vector_store):
        """Test deleting an existing document."""
        mock_vector_store.get = MagicMock(return_value={"ids": ["doc-id-1", "doc-id-2"]})

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import delete_document

            result = await delete_document("PersonalAI/Diary/to-delete.md")

            assert result is True
            mock_vector_store.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, mock_vector_store):
        """Test deleting a non-existent document."""
        mock_vector_store.get = MagicMock(return_value={"ids": []})

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import delete_document

            result = await delete_document("PersonalAI/nonexistent.md")

            assert result is False


class TestSearchDocuments:
    """Tests for document search."""

    @pytest.mark.asyncio
    async def test_search_documents(self, mock_vector_store):
        """Test searching documents."""
        # Mock search results
        mock_doc = Document(
            page_content="This is relevant content",
            metadata={"source": "PersonalAI/Diary/2024-01-15.md", "folder": "Diary"},
        )
        mock_vector_store.similarity_search_with_score = MagicMock(return_value=[(mock_doc, 0.85)])

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import search_documents

            results = await search_documents("test query", k=5)

            assert len(results) == 1
            assert results[0]["content"] == "This is relevant content"
            assert results[0]["source"] == "PersonalAI/Diary/2024-01-15.md"
            assert results[0]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_search_documents_empty_results(self, mock_vector_store):
        """Test searching with no results."""
        mock_vector_store.similarity_search_with_score = MagicMock(return_value=[])

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import search_documents

            results = await search_documents("obscure query", k=5)

            assert len(results) == 0


class TestGetContextForQuery:
    """Tests for context retrieval."""

    @pytest.mark.asyncio
    async def test_get_context_for_query(self, mock_vector_store):
        """Test getting formatted context for query."""
        mock_doc = Document(
            page_content="Relevant information here",
            metadata={"source": "PersonalAI/Study/topic.md"},
        )
        mock_vector_store.similarity_search_with_score = MagicMock(return_value=[(mock_doc, 0.9)])

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import get_context_for_query

            context = await get_context_for_query("my question", k=3)

            assert "Relevant information here" in context
            assert "PersonalAI/Study/topic.md" in context

    @pytest.mark.asyncio
    async def test_get_context_for_query_no_results(self, mock_vector_store):
        """Test getting context with no results."""
        mock_vector_store.similarity_search_with_score = MagicMock(return_value=[])

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import get_context_for_query

            context = await get_context_for_query("obscure question")

            assert context == ""


class TestCollectionStats:
    """Tests for collection statistics."""

    @pytest.mark.asyncio
    async def test_get_collection_stats(self, mock_vector_store):
        """Test getting collection statistics."""
        mock_vector_store._collection.count = MagicMock(return_value=42)

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import get_collection_stats

            stats = await get_collection_stats()

            assert stats["total_chunks"] == 42
            assert "persist_directory" in stats

    @pytest.mark.asyncio
    async def test_get_collection_stats_error(self, mock_vector_store):
        """Test getting stats when collection errors."""
        mock_vector_store._collection.count = MagicMock(side_effect=Exception("DB error"))

        with patch("services.vectors.get_vector_store", return_value=mock_vector_store):
            from services.vectors import get_collection_stats

            stats = await get_collection_stats()

            assert "error" in stats
            assert stats["total_chunks"] == 0
