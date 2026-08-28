# -*- coding: utf-8 -*-
"""
tools/knowledge_tool.py -- base de conhecimento local e a ferramenta
``search_project_knowledge``.

Os arquivos Markdown de ``knowledge/`` são lidos com classes Java de
entrada/saída, quebrados em trechos pequenos e ranqueados por similaridade
textual (Apache Commons Text). Só os trechos mais próximos da pergunta são
enviados ao modelo -- um RAG lexical, sem embeddings.

APIs Java utilizadas neste módulo:

    java.io.File            -> lista os arquivos da base de conhecimento
    java.io.FileInputStream -> abre cada arquivo
    java.io.InputStreamReader + java.io.BufferedReader -> leem em UTF-8
    java.lang.StringBuilder -> monta o conteúdo lido
"""
from __future__ import unicode_literals

from java.io import File
from java.io import FileInputStream
from java.io import InputStreamReader
from java.io import BufferedReader
from java.io import IOException
from java.lang import StringBuilder

import config
from search.chunker import chunk_markdown
from search.fuzzy_matcher import rank
from tools.registry import Tool, ToolError


class KnowledgeBase(object):
    """Documentos Markdown do projeto, divididos em trechos pesquisáveis."""

    def __init__(self, directory=None, max_chars=None):
        self.directory = directory or config.KNOWLEDGE_DIR
        self.max_chars = max_chars or config.KNOWLEDGE_MAX_CHARS
        self._chunks = []
        self._documents = []
        self._loaded = False

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------
    def load(self, force=False):
        """Lê os arquivos .md com java.io e monta os trechos."""
        if self._loaded and not force:
            return self

        self._chunks = []
        self._documents = []

        folder = File(self.directory)
        if not folder.isDirectory():
            self._loaded = True
            return self

        files = folder.listFiles()
        names = sorted([f.getName() for f in files
                        if f.isFile() and f.getName().lower().endswith(".md")])

        for name in names:
            content = self._read_file(File(folder, name))
            if not content:
                continue
            chunks = chunk_markdown(name, content, max_chars=self.max_chars)
            self._chunks.extend(chunks)
            title = chunks[0].title if chunks else name
            self._documents.append({
                "doc_id": name,
                "title": title,
                "chunks": len(chunks),
                "chars": len(content),
            })

        self._loaded = True
        return self

    def _read_file(self, java_file):
        """Lê um arquivo em UTF-8 usando streams Java."""
        reader = None
        try:
            reader = BufferedReader(
                InputStreamReader(FileInputStream(java_file), "UTF-8"))
            buffer = StringBuilder()
            line = reader.readLine()
            while line is not None:
                buffer.append(line)
                buffer.append("\n")
                line = reader.readLine()
            return buffer.toString()
        except IOException:
            return ""
        finally:
            if reader is not None:
                try:
                    reader.close()
                except IOException:
                    pass

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def chunks(self):
        self.load()
        return list(self._chunks)

    def documents(self):
        self.load()
        return list(self._documents)

    def document_count(self):
        return len(self.documents())

    def chunk_count(self):
        return len(self.chunks())

    def search(self, query, top_k=None, min_score=None, max_chars=None):
        """Ranqueia os trechos por proximidade textual com a pergunta."""
        self.load()
        if not query or not query.strip():
            return []

        top_k = top_k or config.KNOWLEDGE_TOP_K
        min_score = config.KNOWLEDGE_MIN_SCORE if min_score is None else min_score
        max_chars = max_chars or config.KNOWLEDGE_MAX_CHARS

        ranked = rank(
            query,
            self._chunks,
            text_of=lambda chunk: chunk.search_text(),
            reference_of=lambda chunk: chunk.label,
            top_k=top_k,
            min_score=min_score,
        )

        results = []
        for chunk, score in ranked:
            results.append({
                "documento": chunk.doc_id,
                "titulo": chunk.title,
                "secao": chunk.heading,
                "score": round(score, 4),
                "trecho": chunk.text[:max_chars],
            })
        return results


# ---------------------------------------------------------------------------
# Ferramenta exposta ao modelo
# ---------------------------------------------------------------------------
def create_tools(context):
    knowledge = context.knowledge

    def search_project_knowledge(query, limit=None):
        if knowledge is None:
            raise ToolError("Base de conhecimento indisponível.")

        top_k = limit or config.KNOWLEDGE_TOP_K
        if top_k < 1:
            top_k = 1
        if top_k > 8:
            top_k = 8

        results = knowledge.search(query, top_k=top_k)
        return {
            "consulta": query,
            "documentos_na_base": knowledge.document_count(),
            "trechos_na_base": knowledge.chunk_count(),
            "encontrados": len(results),
            "resultados": results,
            "observacao": ("Nenhum trecho passou do score mínimo; responda com "
                           "cautela e diga que a documentação local não cobre "
                           "o assunto." if not results else None),
        }

    return [Tool(
        name="search_project_knowledge",
        description=(
            "Pesquisa na documentação local do projeto Jython AI Agent. "
            "Use SEMPRE que a pergunta for sobre este projeto: arquitetura, "
            "arquivos, Jython, Java, Groq, Docker, banco de dados, "
            "ferramentas, testes, configuração ou funcionamento interno. "
            "Devolve os trechos mais relevantes com score de similaridade."),
        parameters={
            "query": {
                "type": "string",
                "description": "Termos de busca, em linguagem natural.",
            },
            "limit": {
                "type": "integer",
                "description": "Quantidade de trechos a devolver (1 a 8). "
                               "Padrão: 3.",
            },
        },
        required=["query"],
        handler=search_project_knowledge,
    )]
