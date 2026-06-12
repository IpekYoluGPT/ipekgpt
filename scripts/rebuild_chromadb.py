"""
ChromaDB Rebuild Script with Google Gemini Embeddings
Run this in Google Colab to rebuild your vector database.

Usage:
1. Upload your data folders (data/processed/ and data/rag_dataset/) to Colab
2. Set your GEMINI_API_KEY
3. Run this script
4. Download the chroma_db folder
"""

# ============================================================================
# Install required packages (for Colab)
# ============================================================================
import subprocess
import sys

def install_packages():
    packages = ["chromadb", "google-genai"]
    for pkg in packages:
        print(f"📦 Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
    print("✅ All packages installed!\n")

install_packages()

# ============================================================================
# Imports
# ============================================================================
import os
import json
from pathlib import Path
from google import genai
from google.genai import types

# ============================================================================
# Configuration
# ============================================================================

import os

# Base directory setup to work both locally and in Colab
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else '.'

GEMINI_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your key
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768
COLLECTION_NAME = "org_knowledge_turkish"
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")
DATA_DIRECTORIES = [
    os.path.join(BASE_DIR, "data", "processed"),
    os.path.join(BASE_DIR, "data", "rag_dataset")
]

# ============================================================================
# Google Gemini Embeddings
# ============================================================================

class GeminiEmbeddings:
    """Google Gemini Embeddings for ChromaDB"""
    
    def __init__(self, api_key: str, model: str = "gemini-embedding-001", dimension: int = 768):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.dimension = dimension
    
    def embed_documents(self, texts: list) -> list:
        """Embed multiple documents"""
        if not texts:
            return []
        
        # Process in batches of 100
        all_embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            result = self.client.models.embed_content(
                model=self.model,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self.dimension
                )
            )
            all_embeddings.extend([list(e.values) for e in result.embeddings])
            print(f"  Processed {min(i+batch_size, len(texts))}/{len(texts)} documents")
        
        return all_embeddings

    def __call__(self, input):
        """Make callable for ChromaDB compatibility"""
        if isinstance(input, str):
            input = [input]
        return self.embed_documents(input)


# ============================================================================
# Data Loading
# ============================================================================

def load_qa_pairs():
    """Load Q&A pairs from JSON files"""
    qa_pairs = []
    
    for data_dir in DATA_DIRECTORIES:
        if not os.path.exists(data_dir):
            print(f"⚠️ Directory not found: {data_dir}")
            continue
        
        print(f"\n📁 Loading from: {data_dir}")
        
        for json_file in Path(data_dir).glob("**/*.json"):
            try:
                # Try utf-8-sig first (handles BOM), fallback to utf-8
                try:
                    with open(json_file, 'r', encoding='utf-8-sig') as f:
                        data = json.load(f)
                except:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                count = 0
                
                # New format: {"metadata": {...}, "data": [{question, answer}, ...]}
                if isinstance(data, dict) and 'data' in data:
                    for item in data['data']:
                        if 'question' in item and 'answer' in item:
                            qa_pairs.append({
                                'question': item['question'],
                                'answer': item['answer'],
                                'source': json_file.name
                            })
                            count += 1
                
                # Old format: [{"soru": ..., "cevap": ...}, ...]
                elif isinstance(data, list):
                    for item in data:
                        if 'soru' in item and 'cevap' in item:
                            qa_pairs.append({
                                'question': item['soru'],
                                'answer': item['cevap'],
                                'source': json_file.name
                            })
                            count += 1
                        elif 'question' in item and 'answer' in item:
                            qa_pairs.append({
                                'question': item['question'],
                                'answer': item['answer'],
                                'source': json_file.name
                            })
                            count += 1
                
                # Single Q&A dict
                elif isinstance(data, dict):
                    if 'soru' in data and 'cevap' in data:
                        qa_pairs.append({
                            'question': data['soru'],
                            'answer': data['cevap'],
                            'source': json_file.name
                        })
                        count = 1
                    elif 'question' in data and 'answer' in data:
                        qa_pairs.append({
                            'question': data['question'],
                            'answer': data['answer'],
                            'source': json_file.name
                        })
                        count = 1
                
                if count > 0:
                    print(f"  ✅ {json_file.name} ({count} pairs)")
                else:
                    print(f"  ⚠️ {json_file.name} (no Q&A found)")
                    
            except Exception as e:
                print(f"  ❌ {json_file.name}: {e}")
    
    return qa_pairs


# ============================================================================
# ChromaDB Build
# ============================================================================

def build_chromadb():
    """Build ChromaDB with Google Gemini embeddings"""
    import chromadb
    from chromadb.config import Settings
    
    print("=" * 60)
    print("🚀 ChromaDB Rebuild with Google Gemini Embeddings")
    print("=" * 60)
    
    # Load data
    print("\n📂 Step 1: Loading Q&A data...")
    qa_pairs = load_qa_pairs()
    print(f"\n✅ Loaded {len(qa_pairs)} Q&A pairs")
    
    if not qa_pairs:
        print("❌ No data found! Check your data directories.")
        return
    
    # Initialize embeddings
    print("\n🧠 Step 2: Initializing Google Gemini Embeddings...")
    embeddings = GeminiEmbeddings(
        api_key=GEMINI_API_KEY,
        model=EMBEDDING_MODEL,
        dimension=EMBEDDING_DIMENSION
    )
    print(f"  Model: {EMBEDDING_MODEL}")
    print(f"  Dimension: {EMBEDDING_DIMENSION}")
    
    # Prepare documents
    print("\n📝 Step 3: Preparing documents...")
    documents = []
    metadatas = []
    ids = []
    
    for i, qa in enumerate(qa_pairs):
        # Combine question and answer for embedding
        text = f"Soru: {qa['question']}\nCevap: {qa['answer']}"
        documents.append(text)
        metadatas.append({
            'source': qa['source'],
            'question': qa['question'][:100]  # Truncate for metadata
        })
        ids.append(f"doc_{i}")
    
    # Generate embeddings
    print(f"\n🔄 Step 4: Generating embeddings for {len(documents)} documents...")
    doc_embeddings = embeddings.embed_documents(documents)
    print(f"  ✅ Generated {len(doc_embeddings)} embeddings")
    
    # Create ChromaDB
    print("\n💾 Step 5: Creating ChromaDB...")
    
    # Remove old database
    import shutil
    if os.path.exists(CHROMA_DB_PATH):
        shutil.rmtree(CHROMA_DB_PATH)
    
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Add documents with embeddings
    collection.add(
        documents=documents,
        embeddings=doc_embeddings,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"  ✅ Created collection: {COLLECTION_NAME}")
    print(f"  ✅ Added {collection.count()} documents")
    
    print("\n" + "=" * 60)
    print("✅ ChromaDB rebuild complete!")
    print(f"📁 Output: {CHROMA_DB_PATH}")
    print("=" * 60)
    print("\n📥 Download the 'chroma_db' folder and replace it in your project.")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    if GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set your GEMINI_API_KEY first!")
    else:
        build_chromadb()
