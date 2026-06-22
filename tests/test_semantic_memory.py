import pytest

from services.semantic_memory import SemanticMemory


class StubEmbeddingClient:
    def __init__(self, vectors):
        self.vectors = vectors
        self.embeddings = self

    def create(self, model, input):
        vector = self.vectors[input]

        class Item:
            embedding = vector

        class Response:
            data = [Item()]

        return Response()


class FailingEmbeddingClient:
    embeddings = None

    def __init__(self):
        self.embeddings = self

    def create(self, model, input):
        raise RuntimeError("embedding unavailable")


def test_normalize_vector_and_cosine_similarity():
    memory = SemanticMemory(client=None)

    normalized = memory.normalize_vector([3, 4])
    assert normalized == [0.6, 0.8]
    assert memory.cosine_similarity([1, 0], [1, 0]) == 1
    assert memory.cosine_similarity([1, 0], [0, 1]) == 0


def test_embedding_generation_uses_stub_client():
    memory = SemanticMemory(
        client=StubEmbeddingClient({"ticket per stato": [3, 4]}),
        embedding_model="test-model",
    )

    assert memory.embed_text("ticket per stato") == [0.6, 0.8]


def test_embedding_fallback_returns_none_when_client_fails():
    memory = SemanticMemory(client=FailingEmbeddingClient())

    assert memory.embed_text("ticket per stato") is None
    assert memory.text_similarity("ticket per stato", "ticket per stato") == pytest.approx(1.0)
