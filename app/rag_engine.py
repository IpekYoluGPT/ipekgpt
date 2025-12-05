"""
RAG Engine - Simplified for İpekGPT Web Application
Uses existing ChromaDB and pre-downloads Turkish Gemma model
"""
import os
import re
import time
from typing import Dict, Optional, Any

# LangChain imports
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.llms import LLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Llama CPP
from llama_cpp import Llama

from .config import settings


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
        print("⏳ Initializing Turkish embedding model...")
        
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"  (Using device: {device} for embeddings)")
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model_name,
            model_kwargs={'device': device}
        )
        print("✅ Embedding model ready!")
    
    def load_existing(self):
        """Load existing vector store from disk"""
        print("⏳ Loading existing vector store from chroma_db...")
        
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(
                f"❌ ChromaDB not found at: {self.db_path}\n"
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
        
        print("✅ Vector store loaded!")
        return self.vectorstore


# ============================================================================
# Turkish Gemma LLM Wrapper
# ============================================================================

class TurkishGemmaLLM(LLM):
    """Custom LLM wrapper for Turkish Gemma model"""
    
    model: Any = None
    
    def __init__(self, repo_id: str = None, filename: str = None, **kwargs):
        super().__init__()
        
        repo_id = repo_id or settings.GEMMA_REPO_ID
        filename = filename or settings.GEMMA_FILENAME
        
        print("⏳ Downloading and loading Turkish Gemma model...")
        print("   (This may take several minutes on first run)")
        
        self.model = Llama.from_pretrained(
            repo_id=repo_id,
            filename=filename,
            verbose=False,
            **settings.GEMMA_PARAMS
        )
        
        print("✅ Turkish Gemma model loaded!")
        
        if settings.GEMMA_PARAMS.get('n_gpu_layers', 0) > 0 or settings.GEMMA_PARAMS.get('n_gpu_layers') == -1:
            print("   🚀 Model is using GPU acceleration!")
    
    @property
    def _llm_type(self) -> str:
        return "turkish_gemma"
    
    def _call(self, prompt: str, stop=None) -> str:
        """Generate response from the model"""
        response = self.model(
            prompt,
            stop=["<end_of_turn>", "</s>"],
            max_tokens=settings.GEMMA_PARAMS['n_predict'],
            temperature=settings.GEMMA_PARAMS['temp'],
            top_p=settings.GEMMA_PARAMS['top_p'],
            top_k=settings.GEMMA_PARAMS['top_k'],
            repeat_penalty=settings.GEMMA_PARAMS['repeat_penalty']
        )
        
        raw_text = response['choices'][0]['text']
        
        # Clean up response
        cleaned_text = re.sub(r'<think>.*?(?:</think>|$)', '', raw_text, flags=re.DOTALL)
        cleaned_text = re.sub(r'\[cite.*?\]', '', cleaned_text, flags=re.DOTALL)
        cleaned_text = re.sub(r'\\', '', cleaned_text)
        
        disclaimer_patterns = [
            r'\*\(Not:.*?\)',
            r'\(Not:.*?\)',
            r'\* Bilgi tabanımızda.*',
            r'Verilen bilgiler arasında.*',
            r'Bağlamda.*',
        ]
        
        for pattern in disclaimer_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
        
        return cleaned_text.strip()


# ============================================================================
# RAG Chatbot
# ============================================================================

class TurkishRAGChatbot:
    """RAG chatbot using Turkish Gemma model"""
    
    PROMPT_TEMPLATE = """<bos><start_of_turn>user
Sen İpekyolu Girişimci Kuluçka Merkezi'nin resmi yapay zeka asistanısın.
Adın: İpekGPT.

GÖREVİN:
Sana verilen bilgileri (Aşağıdaki VERİLER kısmını) *kendi bilginmiş gibi* kabul et ve kullanıcıya doğrudan cevap ver.

KURALLAR:
1. "Bağlamdaki bilgilere göre", "Verilere göre", "Bilgi tabanına göre", "Metinde yazdığı gibi" gibi ifadeler KESİNLİKLE KULLANMA.
2. Doğrudan cevabı ver.
3. Listeleri madde işaretleri ile düzenle.
4. Bilgi VERİLER kısmında yoksa, "Bu konuda şu an güncel bilgim bulunmuyor" de.

VERİLER:
{context}

SORU: {question}<end_of_turn>
<start_of_turn>model
"""
    
    def __init__(self, vectorstore=None, llm=None):
        """Initialize the RAG chatbot"""
        self.vectorstore = vectorstore
        self.llm = llm or TurkishGemmaLLM()
        
        self.PROMPT = PromptTemplate(
            template=self.PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        print("✅ Turkish RAG Chatbot initialized and ready!")
    
    def ask(self, question: str, show_sources: bool = False) -> Dict:
        """Ask a question and get a response"""
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
            
            # Generate response
            answer = self.llm._call(prompt)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Get categories used
            categories = list(set(doc.metadata.get('category', 'Unknown') for doc in docs))
            
            return {
                'answer': answer,
                'num_sources': len(docs),
                'categories_used': categories,
                'response_time_ms': response_time_ms,
                'sources': docs if show_sources else None
            }
            
        except Exception as e:
            print(f"Error in ask(): {e}")
            return {
                'answer': "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.",
                'num_sources': 0,
                'categories_used': [],
                'response_time_ms': int((time.time() - start_time) * 1000),
                'error': str(e)
            }


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
        """Initialize the RAG system - loads existing ChromaDB and pre-downloads model"""
        if RAGSystem._initialized:
            print("RAG System already initialized!")
            return self.chatbot
        
        print("=" * 70)
        print("🚀 İPEKYOLU RAG SİSTEMİ BAŞLATILIYOR")
        print("=" * 70)
        
        # Initialize vector store manager and load existing ChromaDB
        self.vector_store_manager = VectorStore()
        self.vectorstore = self.vector_store_manager.load_existing()
        
        if not self.vectorstore:
            print("❌ Vector store yüklenemedi!")
            return None
        
        print("\n🤖 Turkish Gemma RAG chatbot başlatılıyor...")
        self.chatbot = TurkishRAGChatbot(vectorstore=self.vectorstore)
        
        RAGSystem._initialized = True
        
        print("\n" + "=" * 70)
        print("✅ İPEKYOLU RAG SİSTEMİ HAZIR!")
        print("=" * 70)
        
        return self.chatbot
    
    def get_chatbot(self) -> Optional[TurkishRAGChatbot]:
        """Get the chatbot instance, initializing if needed"""
        if not RAGSystem._initialized:
            return self.initialize()
        return self.chatbot
    
    def ask(self, question: str) -> Dict:
        """Convenience method to ask a question"""
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
