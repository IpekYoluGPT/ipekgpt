"""
RAG Engine - Simplified for İpekGPT Web Application
Uses existing ChromaDB and Gemini API for LLM responses
"""
import os
import time
from typing import Dict, Optional, Any, List

# LangChain imports
from langchain_core.prompts import PromptTemplate
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma

# Google Generative AI for embeddings
from google import genai
from google.genai import types

from .config import settings
from .gemini_api import gemini_manager


# ============================================================================
# Google Gemini Embeddings Wrapper for LangChain
# ============================================================================

class GeminiEmbeddings(Embeddings):
    """Custom LangChain Embeddings wrapper for Google Gemini API"""
    
    def __init__(self, model: str = "gemini-embedding-001", dimension: int = 768):
        self.model = model
        self.dimension = dimension
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Gemini client with API key"""
        api_keys = settings.GEMINI_API_KEYS
        if api_keys:
            self.client = genai.Client(api_key=api_keys[0])
            print(f"[OK] Gemini Embeddings initialized (model={self.model}, dim={self.dimension})")
        else:
            raise ValueError("No GEMINI_API_KEYS configured!")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        if not texts:
            return []
        
        result = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self.dimension
            )
        )
        return [list(e.values) for e in result.embeddings]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        result = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self.dimension
            )
        )
        return list(result.embeddings[0].values)


# ============================================================================
# Vector Store (Load Existing Only)
# ============================================================================

class VectorStore:
    """Loads existing ChromaDB vector store with Google Gemini embeddings"""
    
    def __init__(self, db_path: str = None, collection_name: str = None):
        self.db_path = db_path or settings.VECTOR_DB_PATH
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.vectorstore = None
        self.embeddings = None
        
        self._init_embeddings()
    
    def _init_embeddings(self):
        """Initialize the Google Gemini embedding model"""
        print("Initializing Google Gemini Embeddings API...")
        self.embeddings = GeminiEmbeddings(model="gemini-embedding-001", dimension=768)
        print("Embeddings ready!")
    
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
    
    PROMPT_TEMPLATE = """
Sen İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi'nin resmi yapay zeka asistanısın.
Adın: İpekGPT.

GÜNCEL TARİH VE SAAT: {current_datetime}

DİL KURALI:
- Kullanıcının yazdığı dili tespit et ve AYNI DİLDE yanıt ver.
- Türkçe soru → Türkçe cevap
- İngilizce soru → İngilizce cevap  
- Almanca soru → Almanca cevap
- Diğer diller için de aynı mantık geçerli.

KİMLİĞİN:
- Samimi, yardımsever ve profesyonel bir asistansın.
- İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi hakkında bilgi veriyorsun.
- Elazığ'da bulunan bu merkezin AI asistanısın.

ÖNEMLİ TALİMATLAR:
1. MERKEZ HAKKINDA SORULAR: Aşağıdaki SORU-CEVAP çiftlerini kullanarak yanıtla.
2. Birden fazla bilgi varsa, bunları birleştirip kapsamlı bir cevap oluştur.
3. "Bağlamdaki bilgilere göre", "Verilere göre" gibi ifadeler KULLANMA - doğrudan cevabı ver.
4. Listeleri madde işaretleri ile düzenle.
5. ÖNCEKİ KONUŞMAYA dikkat et ve bağlamı koru.

GENEL BİLGİ SORULARI:
- Basit matematik soruları ve genel kültür sorularına kısa ve net cevaplar ver.

SINIRLAR:
- Hiç “bilgim olmayabilir” demediysen → “Bu konuda sanırım bilgim olmayabilir, daha açıklayıcı sorarsan hatırlayabilirim.”
- Daha önce zaten söylediyse → “Üzgünüm, şu anda bu konuda bilgim yok. İstersen başka bir konuda yardımcı olabilirim.”
- Zararlı, uygunsuz veya etik dışı içeriklere cevap verme.
- Kullanıcı bir daha sormadıkça asla kendini yeniden tanıtma. 
- Güncel bilgiler hakkında net bir bilgin yoksa "Güncel bilgilere erişemiyorum" diye cevapla.

MERKEZ HAKKINDAKİ BİLGİLER:
{context}

ÖNCEKİ KONUŞMA:
{history}

KULLANICININ ŞİMDİKİ SORUSU: {question}

YANITIM:
"""
    
    def __init__(self, vectorstore=None):
        """Initialize the RAG chatbot"""
        self.vectorstore = vectorstore
        
        self.PROMPT = PromptTemplate(
            template=self.PROMPT_TEMPLATE,
            input_variables=["context", "history", "question", "current_datetime"]
        )
        
        print("Turkish RAG Chatbot initialized with Gemini API!")
    
    async def ask_async(self, question: str, history: list = None, show_sources: bool = False) -> Dict:
        """Ask a question and get a response (async version)
        
        Args:
            question: The user's question
            history: List of previous messages [{"role": "user"/"assistant", "content": "..."}]
            show_sources: Whether to include source documents in response
        """
        start_time = time.time()
        
        try:
            # Retrieve relevant documents
            perf_start = time.time()
            print(f"[RAG] Searching for: '{question[:50]}...'")
            docs = self.vectorstore.similarity_search(question, k=settings.TOP_K_RESULTS)
            search_time = int((time.time() - perf_start) * 1000)
            print(f"[PERF] Vector Search: {search_time}ms (k={settings.TOP_K_RESULTS})")
            
            # Build context from retrieved documents
            context_parts = []
            for i, doc in enumerate(docs):
                content = doc.page_content
                context_parts.append(content)
            context = "\n\n".join(context_parts)
            
            # Format conversation history
            history_text = ""
            if history:
                history_parts = []
                for msg in history:
                    role = "Kullanıcı" if msg.get("role") == "user" else "İpekGPT"
                    history_parts.append(f"{role}: {msg.get('content', '')}")
                history_text = "\n".join(history_parts)
                print(f"[RAG] Including {len(history)} messages in history")
            else:
                history_text = "(İlk mesaj - önceki konuşma yok)"
            
            # Create prompt with current datetime
            from datetime import datetime
            current_dt = datetime.now().strftime("%d %B %Y, %A, Saat: %H:%M")
            # Turkish day/month names
            tr_days = {"Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba", 
                       "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"}
            tr_months = {"January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan",
                         "May": "Mayıs", "June": "Haziran", "July": "Temmuz", "August": "Ağustos",
                         "September": "Eylül", "October": "Ekim", "November": "Kasım", "December": "Aralık"}
            for eng, tr in {**tr_days, **tr_months}.items():
                current_dt = current_dt.replace(eng, tr)
            
            prompt = self.PROMPT.format(context=context, history=history_text, question=question, current_datetime=current_dt)
            
            # Generate response using Gemini API
            perf_start = time.time()
            result = await gemini_manager.generate_response(prompt)
            llm_time = int((time.time() - perf_start) * 1000)
            print(f"[PERF] Gemini LLM: {llm_time}ms")
            
            # Calculate total response time
            response_time_ms = int((time.time() - start_time) * 1000)
            print(f"[PERF] Total RAG Cycle: {response_time_ms}ms")
            
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
    
    async def ask_async(self, question: str, history: list = None) -> Dict:
        """Async method to ask a question with conversation history"""
        chatbot = self.get_chatbot()
        if not chatbot:
            return {
                'answer': "Sistem henüz hazır değil, lütfen bekleyin.",
                'num_sources': 0,
                'categories_used': [],
                'response_time_ms': 0
            }
        return await chatbot.ask_async(question, history=history)
    
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
