"""LangChain-powered hybrid vector + graph search."""
from langchain.vectorstores import Pinecone as LCPinecone
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from neo4j import GraphDatabase
import pinecone
import os


class HybridSearchEngine:
    def __init__(self):
        pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment="gcp-starter")
        self.index = pinecone.Index("legal-ref-docs")
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        self.vectorstore = LCPinecone(self.index, self.embeddings, "text")
        self.neo4j = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

    def semantic_search(self, query: str, k: int = 10, jurisdiction: str = None):
        """Vector similarity search with optional jurisdiction filter."""
        filter_dict = {"jurisdiction": jurisdiction} if jurisdiction else None
        return self.vectorstore.similarity_search_with_score(
            query, k=k, filter=filter_dict
        )

    def graph_expand(self, doc_ids: list, depth: int = 2) -> list:
        """Expand search results via graph traversal."""
        with self.neo4j.session() as sess:
            result = sess.run(
                """
                MATCH (d:Document)-[:REFERENCES*1..$depth]->(ref:Document)
                WHERE d.id IN $ids
                RETURN DISTINCT ref.id AS id, ref.title AS title
                """,
                ids=doc_ids, depth=depth,
            )
            return [r.data() for r in result]

    def compliance_qa(self, question: str) -> str:
        """RAG chain over legal documents."""
        chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 6}),
        )
        return chain.run(question)
