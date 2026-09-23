import os
import re
import string

import numpy as np
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from google import genai

load_dotenv()


GEMINI_MODEL = "gemini-embedding-001"


class CodeRetriever:

    def __init__(
        self,
        chunks,
        prefer_gemini=True
    ):

        self.chunks = chunks
        self.prefer_gemini = prefer_gemini

        self.backend = None
        self.vectors = None
        self.tfidf = None
        self.gemini_client = None

    # ========================================================
    # TEXT NORMALIZATION
    # ========================================================

    def _normalize_text(self, text):

        if not text:
            return ""

        text = str(text).lower()

        text = text.replace("\\", "/")

        text = text.replace("_", " ")

        text = re.sub(
            r"[^\w\s./-]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    def _normalize_path(self, text):

        if not text:
            return ""

        text = str(text).lower()

        text = text.replace("\\", "/")

        text = text.strip()

        text = text.strip(
            string.punctuation.replace(
                "/",
                ""
            )
        )

        return text


    def _normalize_symbol(self, text):

        if not text:
            return ""

        text = str(text).lower()

        text = text.strip()

        text = re.sub(
            r"\(\s*\)$",
            "",
            text
        )

        text = re.sub(
            r"[^\w.]",
            "",
            text
        )

        return text


    # ========================================================
    # QUERY INFORMATION EXTRACTION
    # ========================================================

    def _extract_file_candidates(self, query):

        query_lower = str(
            query or ""
        ).lower()

        query_lower = query_lower.replace(
            "\\",
            "/"
        )

        candidates = set()

        # ----------------------------------------------------
        # Explicit Python paths
        # ----------------------------------------------------

        matches = re.findall(
            r"[\w./-]+\.py",
            query_lower
        )

        for match in matches:

            match = match.strip(
                string.punctuation
            )

            if match.endswith(".py"):

                candidates.add(
                    self._normalize_path(
                        match
                    )
                )

        return candidates


    def _extract_symbol_candidates(self, query):

        query_text = str(
            query or ""
        )

        candidates = set()

        # ----------------------------------------------------
        # function()
        # ----------------------------------------------------

        matches = re.findall(
            r"\b([A-Za-z_]\w*)\s*\(\s*\)",
            query_text
        )

        for match in matches:

            candidates.add(
                self._normalize_symbol(
                    match
                )
            )

        # ----------------------------------------------------
        # Backtick symbols
        # ----------------------------------------------------

        backtick_matches = re.findall(
            r"`([^`]+)`",
            query_text
        )

        for match in backtick_matches:

            cleaned = (
                match
                .strip()
                .replace(
                    "()",
                    ""
                )
            )

            if re.match(
                r"^[A-Za-z_]\w*$",
                cleaned
            ):

                candidates.add(
                    self._normalize_symbol(
                        cleaned
                    )
                )

        return candidates


    # ========================================================
    # GEMINI CLIENT
    # ========================================================

    def _get_gemini_client(self):

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:

            raise ValueError(
                "GEMINI_API_KEY is not set."
            )

        if self.gemini_client is None:

            self.gemini_client = genai.Client(
                api_key=api_key
            )

        return self.gemini_client


    # ========================================================
    # EMBEDDINGS
    # ========================================================

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

        return self._normalize(
            embeddings
        )


    # ========================================================
    # BUILD GEMINI INDEX
    # ========================================================

    def _build_gemini(self):

        texts = [
            chunk.get(
                "search_text",
                ""
            )
            for chunk in self.chunks
        ]

        self.vectors = (
            self._gemini_embeddings(
                texts,
                "RETRIEVAL_DOCUMENT"
            )
        )

        self.backend = "gemini"


    # ========================================================
    # BUILD TF-IDF INDEX
    # ========================================================

    def _build_tfidf(self):

        texts = [
            chunk.get(
                "search_text",
                ""
            )
            for chunk in self.chunks
        ]

        self.tfidf = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=20000
        )

        matrix = self.tfidf.fit_transform(
            texts
        )

        self.vectors = (
            matrix
            .toarray()
            .astype(np.float32)
        )

        self.vectors = self._normalize(
            self.vectors
        )

        self.backend = "tfidf"


    # ========================================================
    # BUILD
    # ========================================================

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


    # ========================================================
    # EXACT FILE MATCH
    # ========================================================

    def _file_match_score(
        self,
        query,
        chunk
    ):

        query_paths = (
            self._extract_file_candidates(
                query
            )
        )

        if not query_paths:
            return 0.0

        chunk_file = self._normalize_path(
            chunk.get(
                "file",
                ""
            )
        )

        if not chunk_file:
            return 0.0

        chunk_basename = (
            os.path.basename(
                chunk_file
            )
        )

        score = 0.0

        for query_path in query_paths:

            # ------------------------------------------------
            # Exact complete repository path
            # ------------------------------------------------

            if query_path == chunk_file:

                score = max(
                    score,
                    100.0
                )

                continue

            # ------------------------------------------------
            # Path suffix match
            # ------------------------------------------------

            if chunk_file.endswith(
                "/" + query_path
            ):

                score = max(
                    score,
                    90.0
                )

                continue

            # ------------------------------------------------
            # Exact basename
            # ------------------------------------------------

            if query_path == chunk_basename:

                score = max(
                    score,
                    80.0
                )

        return score


    # ========================================================
    # EXACT SYMBOL MATCH
    # ========================================================

    def _symbol_match_score(
        self,
        query,
        chunk
    ):

        symbols = (
            self._extract_symbol_candidates(
                query
            )
        )

        if not symbols:
            return 0.0

        chunk_name = self._normalize_symbol(
            chunk.get(
                "name",
                ""
            )
        )

        if not chunk_name:
            return 0.0

        if chunk_name in symbols:

            # Function/class exact match
            return 100.0

        return 0.0


    # ========================================================
    # QUERY INTENT
    # ========================================================

    def _is_file_listing_question(
        self,
        query
    ):

        query_text = (
            self._normalize_text(
                query
            )
        )

        patterns = [

            r"\bwhat functions\b",
            r"\bwhich functions\b",
            r"\blist functions\b",
            r"\bfunctions defined\b",
            r"\bfunctions in\b",

            r"\bwhat classes\b",
            r"\bwhich classes\b",
            r"\blist classes\b",
            r"\bclasses defined\b",
            r"\bclasses in\b",

            r"\bwhat is defined\b",
            r"\bwhat are defined\b",

        ]

        return any(
            re.search(
                pattern,
                query_text
            )
            for pattern in patterns
        )


    # ========================================================
    # KEYWORD SCORE
    # ========================================================

    def _keyword_score(
        self,
        query,
        chunk
    ):

        query_text = self._normalize_text(
            query
        )

        chunk_text = self._normalize_text(
            chunk.get(
                "search_text",
                ""
            )
        )

        if not query_text or not chunk_text:
            return 0.0

        query_words = set(
            query_text.split()
        )

        chunk_words = set(
            chunk_text.split()
        )

        if not query_words:
            return 0.0

        overlap = (
            query_words
            & chunk_words
        )

        return float(
            len(overlap)
        )


    # ========================================================
    # KEYWORD SEARCH
    # ========================================================

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

                item["score"] = float(
                    score
                )

                results.append(
                    item
                )

        results.sort(
            key=lambda item:
                item["score"],
            reverse=True
        )

        return results[:top_k]


    # ========================================================
    # EXACT SEARCH
    # ========================================================

    def _exact_search(
        self,
        query,
        top_k
    ):

        results = []

        is_file_question = (
            self._is_file_listing_question(
                query
            )
        )

        for chunk in self.chunks:

            file_score = (
                self._file_match_score(
                    query,
                    chunk
                )
            )

            symbol_score = (
                self._symbol_match_score(
                    query,
                    chunk
                )
            )

            score = 0.0

            # ------------------------------------------------
            # Exact file match
            # ------------------------------------------------

            if file_score > 0:

                score = max(
                    score,
                    file_score
                )

                # File-listing questions should prefer
                # the actual FILE chunk because it contains
                # the list of functions/classes.
                if (
                    is_file_question
                    and chunk.get("type")
                    == "file"
                ):

                    score += 50.0

            # ------------------------------------------------
            # Exact symbol match
            # ------------------------------------------------

            if symbol_score > 0:

                score = max(
                    score,
                    symbol_score
                )

            if score > 0:

                item = dict(chunk)

                item["score"] = float(
                    score
                )

                item["match_type"] = (
                    "exact"
                )

                results.append(
                    item
                )

        results.sort(
            key=lambda item:
                item["score"],
            reverse=True
        )

        return results[:top_k]


    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        query,
        top_k=5
    ):

        if self.vectors is None:

            self.build()


        # ====================================================
        # STEP 1 — EXACT MATCH
        #
        # Exact file/function matches get priority.
        # ====================================================

        exact_results = (
            self._exact_search(
                query,
                top_k
            )
        )


        if exact_results:

            # ------------------------------------------------
            # If an exact file/function exists, return it
            # first. Semantic retrieval should not outrank
            # an explicitly named code entity.
            # ------------------------------------------------

            return exact_results[:top_k]


        # ====================================================
        # STEP 2 — SEMANTIC RETRIEVAL
        # ====================================================

        if self.backend == "gemini":

            try:

                query_vector = (
                    self._gemini_embeddings(
                        [query],
                        "RETRIEVAL_QUERY"
                    )[0]
                )

            except Exception as error:

                print(
                    "Gemini query embedding failed. "
                    "Falling back to TF-IDF. "
                    f"Reason: {error}"
                )

                self._build_tfidf()

                query_matrix = (
                    self.tfidf.transform(
                        [query]
                    )
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

        else:

            query_matrix = (
                self.tfidf.transform(
                    [query]
                )
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


        # ====================================================
        # STEP 3 — KEYWORD RETRIEVAL
        # ====================================================

        keyword_results = (
            self._keyword_search(
                query,
                top_k=max(
                    top_k * 3,
                    10
                )
            )
        )


        keyword_scores = {

            item["chunk_id"]:
                item["score"]

            for item in keyword_results

        }


        # ====================================================
        # STEP 4 — HYBRID SCORING
        # ====================================================

        combined = []

        for index, chunk in enumerate(
            self.chunks
        ):

            semantic_score = float(
                semantic_scores[index]
            )

            keyword_score = (
                keyword_scores.get(
                    chunk["chunk_id"],
                    0.0
                )
            )


            if keyword_score > 0:

                keyword_bonus = min(
                    keyword_score / 5.0,
                    1.0
                )

            else:

                keyword_bonus = 0.0


            final_score = (
                0.7 * semantic_score
                +
                0.3 * keyword_bonus
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

            item["match_type"] = (
                "semantic"
            )

            combined.append(
                item
            )


        combined.sort(
            key=lambda item:
                item["score"],
            reverse=True
        )


        return combined[:top_k]


    # ========================================================
    # INFO
    # ========================================================

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

            "backend":
                self.backend,

            "chunks":
                len(self.chunks),

            "dimensions":
                dimensions

        }


# ============================================================
# FACTORY
# ============================================================

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