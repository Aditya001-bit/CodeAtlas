from backend.rag.chunker import build_chunks, chunk_by_node
from backend.rag.retriever import build_retriever
from backend.rag.graph_context import build_graph_context
from backend.rag.llm import get_llm


class CodeAtlasRAG:

    def __init__(self, parsed_files, graph):
        self.parsed_files = parsed_files
        self.graph = graph

        self.chunks = []
        self.by_node = {}
        self.retriever = None
        self.llm = None

    def build(self, prefer_gemini=True):

        self.chunks = build_chunks(
            self.parsed_files
        )

        self.by_node = chunk_by_node(
            self.chunks
        )

        self.retriever = build_retriever(
            self.chunks,
            prefer_gemini=prefer_gemini
        )

        try:
            self.llm = get_llm()
        except ValueError:
            self.llm = None

        return {
            "chunks": len(self.chunks),
            "retrieval": self.retriever.info(),
            "llm_available": self.llm is not None
        }

    def retrieve(self, question, top_k=5):

        if self.retriever is None:
            raise RuntimeError(
                "RAG has not been built yet."
            )

        return self.retriever.search(
            question,
            top_k=top_k
        )

    def build_prompt(
        self,
        question,
        hits,
        graph_context
    ):

        code_context = []

        for index, hit in enumerate(hits, start=1):

            code_context.append(
                f"""
SOURCE {index}
File: {hit.get('file')}
Function/Class: {hit.get('name')}
Lines: {hit.get('start_line')} - {hit.get('end_line')}
Type: {hit.get('type')}
Similarity: {hit.get('score', 0):.3f}

Code:
{hit.get('source', '')}
"""
            )

        code_text = "\n".join(code_context)

        graph_text = graph_context.get(
            "text",
            ""
        )

        if not graph_text:
            graph_text = "No graph relationships found."

        prompt = f"""
You are CodeAtlas, an AI assistant that understands
Python repositories.

Answer the user's question using ONLY the repository
context provided below.

Do not invent files, functions, relationships, or
behavior that are not supported by the context.

If the context is insufficient, clearly say that the
repository context does not contain enough information.

Always mention the relevant files and functions when
possible.

USER QUESTION:
{question}

RETRIEVED CODE:
{code_text}

GRAPH RELATIONSHIPS:
{graph_text}

Provide a clear developer-friendly answer.
"""

        return prompt

    def build_sources(
        self,
        hits,
        graph_context
    ):

        sources = []

        seen = set()

        for hit in hits:

            node_id = hit.get("node_id")

            if node_id in seen:
                continue

            seen.add(node_id)

            sources.append({
                "node_id": node_id,
                "file": hit.get("file"),
                "name": hit.get("name"),
                "type": hit.get("type"),
                "start_line": hit.get("start_line"),
                "end_line": hit.get("end_line"),
                "score": hit.get("score", 0)
            })

        return sources

    def ask(
        self,
        question,
        top_k=5,
        hops=1
    ):

        hits = self.retrieve(
            question,
            top_k=top_k
        )

        graph_context = build_graph_context(
            self.graph,
            hits,
            hops=hops
        )

        prompt = self.build_prompt(
            question,
            hits,
            graph_context
        )

        answer = None
        llm_ok = False
        llm_error = None

        if self.llm is not None:

            try:
                answer = self.llm.generate(
                    prompt
                )

                llm_ok = True

            except Exception as error:

                llm_error = str(error)

        sources = self.build_sources(
            hits,
            graph_context
        )

        return {
            "question": question,
            "answer": answer,
            "hits": hits,
            "graph_context": graph_context,
            "sources": sources,
            "prompt": prompt,
            "retrieval_backend": self.retriever.backend,
            "llm_ok": llm_ok,
            "llm_error": llm_error
        }