"""
RAG Engine - Simplified for İpekGPT Web Application
Uses existing ChromaDB and Gemini API for LLM responses
"""
import os
import time
from typing import Dict, Optional, Any

# LangChain imports
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from .config import settings
from .gemini_api import gemini_manager


# ============================================================================
# Vector Store (Load Existing Only)
# ============================================================================

class VectorStore:
    """Loads existing ChromaDB vector store with HuggingFace embeddings"""
    
    def __init__(self, embedding_model_name: str = None, db_path: str = None, collection_name: str = None):
        self.embedding_model_name = embedding_model_name or settings.EMBEDDING_MODEL
        self.db_path = db_path or settings.VECTOR_DB_PATH
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.vectorstore = None
        self.embeddings = None
        
        self._init_embeddings()
    
    def _init_embeddings(self):
        """Initialize the embedding model"""
        print("Initializing Turkish embedding model...")
        
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"  (Using device: {device} for embeddings)")
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model_name,
            model_kwargs={'device': device}
        )
        print("Embedding model ready!")
    
    def load_existing(self):
        """Load existing vector store from disk"""
        print("Loading existing vector store from chroma_db...")
        
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(
                f"ChromaDB not found at: {self.db_path}\n"
                "Please ensure the chroma_db folder exists with your vector data."
            )
        
        chroma_client = chromadb.PersistentClient(
            path=self.db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.vectorstore = Chroma(
            client=chroma_client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )
        
        print("Vector store loaded!")
        return self.vectorstore


# ============================================================================
# RAG Chatbot (Using Gemini API)
# ============================================================================

class TurkishRAGChatbot:
    """RAG chatbot using Gemini API for Turkish responses"""
    
    PROMPT_TEMPLATE = """Sen İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi'nin resmi yapay zeka asistanısın.
Adın: İpekGPT.

KİMLİĞİN:
- Samimi, yardımsever ve profesyonel bir asistansın.
- İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi hakkında bilgi veriyorsun.
- İpek Yolu'nun AI asistanısın.

SOHBET KURALLARI:
1. Selamlaşmalara uygun şekilde karşılık ver:
   - "Sa", "Selam", "Selamün aleyküm" derse "Aleykümselam! Size nasıl yardımcı olabilirim?" de.
   - "Merhaba", "Mrb" derse "Merhaba! Size nasıl yardımcı olabilirim?" de.
   - "Günaydın", "İyi günler", "İyi akşamlar" derse uygun şekilde karşılık ver.

2. Kişisel sorulara samimi yanıtlar ver:
   - "Nasılsın?" derse "İyiyim, teşekkür ederim! Size nasıl yardımcı olabilirim?" de.
   - "Ne yapıyorsun?" derse "Sizin sorularınızı yanıtlamak için buradayım!" de.
   - "Kimsin?", "Sen nesin?" derse "Ben İpekGPT, İpek Yolu Merkezi'nin AI asistanıyım." de.
   - "Ne kadar zekisin?" derse "Sorularını cevaplayacak kadar zekiyim! Size merkez hakkında her türlü bilgiyi verebilirim." de.
   - "Nerelisin?" derse "Has Elazığlıyım!" de.
   - "Ben kimim?" derse "Siz şu an benimle sohbet eden değerli bir ziyaretçisiniz! Size nasıl yardımcı olabilirim?" de.

MERKEZ BİLGİ KURALLARI:
1. Merkez hakkındaki sorularda SADECE aşağıdaki VERİLER kısmındaki bilgileri kullan.
2. "Bağlamdaki bilgilere göre", "Verilere göre" gibi ifadeler KESİNLİKLE KULLANMA.
3. Doğrudan cevabı ver, sanki kendi bilginmiş gibi.
4. Listeleri madde işaretleri ile düzenle.
5. VERİLER kısmında bilgi yoksa: "Bu konuda şu an güncel bilgim bulunmuyor. Başka bir konuda yardımcı olabilir miyim?" de.
6. Uydurma, tahmin etme, hayal etme - SADECE verilen bilgileri kullan.

VERİLER:
{context}

SORU: {question}

CEVAP:"""
    
    def __init__(self, vectorstore=None):
        """Initialize the RAG chatbot"""
        self.vectorstore = vectorstore
        
        self.PROMPT = PromptTemplate(
            template=self.PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        print("Turkish RAG Chatbot initialized with Gemini API!")
    
    async def ask_async(self, question: str, show_sources: bool = False) -> Dict:
        """Ask a question and get a response (async version)"""
        start_time = time.time()
        
        try:
            # Retrieve relevant documents
            docs = self.vectorstore.similarity_search(question, k=settings.TOP_K_RESULTS)
            
            # Build context from retrieved documents
            context_parts = []
            for doc in docs:
                context_parts.append(doc.page_content)
            context = "\n\n".join(context_parts)
            
            # Create prompt
            prompt = self.PROMPT.format(context=context, question=question)
            
            # Generate response using Gemini API
            result = await gemini_manager.generate_response(prompt)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if result['error']:
                return {
                    'answer': result['error'],
                    'num_sources': 0,
                    'categories_used': [],
                    'response_time_ms': response_time_ms,
                    'error': result['error']
                }
            
            # Get categories used
            categories = list(set(doc.metadata.get('category', 'Unknown') for doc in docs))
            
            return {
                'answer': result['text'],
                'num_sources': len(docs),
                'categories_used': categories,
                'response_time_ms': response_time_ms,
                'sources': docs if show_sources else None
            }
            
        except Exception as e:
            print(f"Error in ask_async(): {e}")
            return {
                'answer': "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.",
                'num_sources': 0,
                'categories_used': [],
                'response_time_ms': int((time.time() - start_time) * 1000),
                'error': str(e)
            }
    
    def ask(self, question: str, show_sources: bool = False) -> Dict:
        """Synchronous wrapper for ask_async (for compatibility)"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.ask_async(question, show_sources))
                    return future.result()
            else:
                return loop.run_until_complete(self.ask_async(question, show_sources))
        except RuntimeError:
            return asyncio.run(self.ask_async(question, show_sources))


# ============================================================================
# RAG System Builder
# ============================================================================

class RAGSystem:
    """Main RAG system that manages all components"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if RAGSystem._initialized:
            return
        
        self.chatbot = None
        self.vectorstore = None
        self.vector_store_manager = None
    
    def initialize(self):
        """Initialize the RAG system - loads existing ChromaDB"""
        if RAGSystem._initialized:
            print("RAG System already initialized!")
            return self.chatbot
        
        print("=" * 70)
        print("IPEKYOLU RAG SISTEMI BASLATILIYOR")
        print("=" * 70)
        
        # Initialize vector store manager and load existing ChromaDB
        self.vector_store_manager = VectorStore()
        self.vectorstore = self.vector_store_manager.load_existing()
        
        if not self.vectorstore:
            print("Vector store yuklenemedi!")
            return None
        
        print("\nTurkish Gemini RAG chatbot baslatiliyor...")
        self.chatbot = TurkishRAGChatbot(vectorstore=self.vectorstore)
        
        RAGSystem._initialized = True
        
        print("\n" + "=" * 70)
        print("IPEKYOLU RAG SISTEMI HAZIR!")
        print("=" * 70)
        
        return self.chatbot
    
    def get_chatbot(self) -> Optional[TurkishRAGChatbot]:
        """Get the chatbot instance, initializing if needed"""
        if not RAGSystem._initialized:
            return self.initialize()
        return self.chatbot
    
    async def ask_async(self, question: str) -> Dict:
        """Async method to ask a question"""
        chatbot = self.get_chatbot()
        if not chatbot:
            return {
                'answer': "Sistem henüz hazır değil, lütfen bekleyin.",
                'num_sources': 0,
                'categories_used': [],
                'response_time_ms': 0
            }
        return await chatbot.ask_async(question)
    
    def ask(self, question: str) -> Dict:
        """Convenience method to ask a question (sync)"""
        chatbot = self.get_chatbot()
        if not chatbot:
            return {
                'answer': "Sistem henüz hazır değil, lütfen bekleyin.",
                'num_sources': 0,
                'categories_used': [],
                'response_time_ms': 0
            }
        return chatbot.ask(question)


# Global RAG system instance
rag_system = RAGSystem()
