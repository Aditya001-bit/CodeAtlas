import os

import numpy as np
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from google import genai

load_dotenv()

GEMINI_MODEL = "gemini-embedding-001"


class CodeRetriever:

    def __init__(self, chunks, prefer_gemini=True):
        self.chunks = chunks
        self.prefer_gemini = prefer_gemini

        self.backend = None
        self.vectors = None
        self.tfidf = None
        self.gemini_client = None

    def _normalize(self, vectors):
        vectors = np.asarray(
            vectors,
            dtype=np.float32
        )

        norms = np.linalg.norm(
            vectors,
            axis=1,
            keepdims=True
        )

        norms[norms == 0] = 1.0

        return vectors / norms

    def _get_gemini_client(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set."
            )

        if self.gemini_client is None:
            self.gemini_client = genai.Client(
                api_key=api_key
            )

        return self.gemini_client

    def _gemini_embeddings(
        self,
        texts,
        task_type
    ):
        client = self._get_gemini_client()

        embeddings = []

        for text in texts:
            response = client.models.embed_content(
                model=GEMINI_MODEL,
                contents=text,
                config={
                    "task_type": task_type
                }
            )

            embeddings.append(
                response.embeddings[0].values
            )

        return self._normalize(embeddings)

    def _build_gemini(self):

        texts = [
            chunk["search_text"]
            for chunk in self.chunks
        ]

        self.vectors = self._gemini_embeddings(
            texts,
            "RETRIEVAL_DOCUMENT"
        )

        self.backend = "gemini"

    def _build_tfidf(self):

        texts = [
            chunk["search_text"]
            for chunk in self.chunks
        ]

        self.tfidf = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=20000
        )

        matrix = self.tfidf.fit_transform(texts)

        self.vectors = matrix.toarray().astype(
            np.float32
        )

        self.vectors = self._normalize(
            self.vectors
        )

        self.backend = "tfidf"

    def build(self):

        if not self.chunks:
            raise ValueError(
                "No chunks available for retrieval."
            )

        if self.prefer_gemini:

            try:
                self._build_gemini()
                return

            except Exception as error:
                print(
                    "Gemini embeddings unavailable. "
                    "Using TF-IDF fallback. "
                    f"Reason: {error}"
                )

        self._build_tfidf()

    def _keyword_score(self, query, chunk):

        query_text = (
            query
            .lower()
            .replace("_", " ")
        )

        chunk_text = (
            chunk.get("search_text", "")
            .lower()
            .replace("_", " ")
        )

        query_words = set(
            query_text.split()
        )

        if not query_words:
            return 0

        score = 0

        for word in query_words:

            if word in chunk_text:
                score += 1

        return score

    def _keyword_search(
        self,
        query,
        top_k
    ):

        results = []

        for chunk in self.chunks:

            score = self._keyword_score(
                query,
                chunk
            )

            if score > 0:

                item = dict(chunk)
                item["score"] = float(score)

                results.append(item)

        results.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return results[:top_k]

    def search(
        self,
        query,
        top_k=5
    ):

        if self.vectors is None:
            self.build()

        if self.backend == "gemini":

            query_vector = self._gemini_embeddings(
                [query],
                "RETRIEVAL_QUERY"
            )[0]

        else:

            query_matrix = self.tfidf.transform(
                [query]
            )

            query_vector = (
                query_matrix
                .toarray()[0]
                .astype(np.float32)
            )

            norm = np.linalg.norm(
                query_vector
            )

            if norm != 0:
                query_vector = (
                    query_vector / norm
                )

        semantic_scores = (
            self.vectors @ query_vector
        )

        keyword_results = self._keyword_search(
            query,
            top_k=max(top_k * 3, 10)
        )

        keyword_scores = {
            item["chunk_id"]: item["score"]
            for item in keyword_results
        }

        combined = []

        for index, chunk in enumerate(
            self.chunks
        ):

            semantic_score = float(
                semantic_scores[index]
            )

            keyword_score = keyword_scores.get(
                chunk["chunk_id"],
                0
            )

            if keyword_score > 0:

                keyword_bonus = min(
                    keyword_score / 5,
                    1.0
                )

            else:
                keyword_bonus = 0

            final_score = (
                0.7 * semantic_score
                + 0.3 * keyword_bonus
            )

            if final_score <= 0:
                continue

            item = dict(chunk)

            item["score"] = float(
                final_score
            )

            item["semantic_score"] = (
                semantic_score
            )

            item["keyword_score"] = (
                keyword_score
            )

            combined.append(item)

        combined.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return combined[:top_k]

    def info(self):

        dimensions = 0

        if (
            self.vectors is not None
            and len(self.vectors) > 0
        ):
            dimensions = int(
                self.vectors.shape[1]
            )

        return {
            "backend": self.backend,
            "chunks": len(self.chunks),
            "dimensions": dimensions
        }


def build_retriever(
    chunks,
    prefer_gemini=True
):

    retriever = CodeRetriever(
        chunks=chunks,
        prefer_gemini=prefer_gemini
    )

    retriever.build()

    return retriever