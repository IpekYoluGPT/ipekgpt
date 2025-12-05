# 🆕 Enhanced JSON Format Support - Quick Guide

## Overview

The `İpelYoluGPT.ipynb` notebook has been updated to support **both old and new JSON formats** for Q&A data. The system automatically detects which format you're using and handles it appropriately.

## 🎯 Quick Start

**IMPORTANT:** Your project has TWO data directories:
- **`./IPEKYOLU_RAG_VERISETI/`** → Contains **NEW format** files (with metadata sections)
- **`./data/`** → Contains **OLD format** files (without metadata sections)

**The system loads BOTH directories automatically!** This ensures you have the complete dataset with maximum coverage.

---

## What's New?

### 1. **Enhanced JSON Format Detection**
- Automatically detects if a JSON file uses the new format (with `metadata` section)
- Falls back gracefully to old format for backward compatibility
- No breaking changes - old files still work!

### 2. **New Metadata Fields**
The new format supports additional metadata:
- `source_ids`: Array of source document IDs
- `file_version`: Version number of the JSON file
- `last_updated`: Last update date
- Better category and sub-category organization

### 3. **New Helper Functions**
- `inspect_json_format()`: Examine a JSON file's structure before loading
- Enhanced source display showing `source_ids` when available

---

## JSON Format Comparison

### NEW Format (Recommended)
```json
{
    "metadata": {
        "file_name": "1.1_ana_sayfa_genel_bakis.json",
        "category": "TEMEL_BILGILER",
        "sub_category": "Genel İstatistikler, İmkanlar ve Eğitim Kataloğu",
        "last_updated": "2025-11-04",
        "version": "1.0"
    },
    "data": [
        {
            "question": "Merkezinizin genel istatistikleri nelerdir?",
            "answer": "Merkezimiz, bugüne kadar 700 saatin üzerinde...",
            "source_ids": ["60"],
            "category": "İstatistikler",
            "keywords": ["istatistik", "sayısal", "700+ saat"],
            "priority": "high",
            "related_questions": ["Kaç kişiye eğitim verdiniz?"]
        }
    ],
    "notes": {
        "chunking_strategy": "Her Q&A çifti bağımsız...",
        "augmentation_notes": "Aynı bilgi için farklı soru..."
    }
}
```

### OLD Format (Still Supported)
```json
{
    "data": [
        {
            "question": "Merkezinizin genel istatistikleri nelerdir?",
            "answer": "Merkezimiz, bugüne kadar 700 saatin üzerinde...",
            "category": "İstatistikler",
            "keywords": ["istatistik", "sayısal"],
            "priority": "high",
            "related_questions": ["Kaç kişiye eğitim verdiniz?"]
        }
    ]
}
```

---

## Usage Examples

### 1. Inspect JSON Format Before Loading
```python
from pathlib import Path

loader = QADataLoader()

# Check NEW format file
loader.inspect_json_format('./IPEKYOLU_RAG_VERISETI/01_TEMEL_BILGILER/1.1_ana_sayfa_genel_bakis.json')

# Check OLD format file
loader.inspect_json_format('./data/AnaSayfa.json')
```

**Output:**
```
🔍 DOSYA FORMATI İNCELEMESİ: AnaSayfa.json
======================================================================
✅ YENİ FORMAT ALGILANDI (metadata bölümü mevcut)

Metadata Bilgileri:
  • file_name: 1.1_ana_sayfa_genel_bakis.json
  • category: TEMEL_BILGILER
  • sub_category: Genel İstatistikler, İmkanlar ve Eğitim Kataloğu
  • last_updated: 2025-11-04
  • version: 1.0

📊 Toplam Q&A Çifti: 23

🔎 Örnek Q&A Yapısı:
  • Alanlar: question, answer, source_ids, category, keywords, priority, related_questions
  ✅ source_ids alanı mevcut (yeni format)
```

### 2. Load from BOTH Directories (RECOMMENDED - Default Behavior)
```python
# This is what the system does automatically!
loader = QADataLoader()
all_documents = []

# Load NEW format files
new_format_docs = loader.load_from_directory('./IPEKYOLU_RAG_VERISETI')
all_documents.extend(new_format_docs)

# Load OLD format files
old_format_docs = loader.load_from_directory('./data')
all_documents.extend(old_format_docs)

print(f"✅ Total: {len(all_documents)} Q&A pairs")
print(f"   └─ NEW format: {len(new_format_docs)} pairs")
print(f"   └─ OLD format: {len(old_format_docs)} pairs")

# Build system with ALL data
# (The main notebook does this automatically)
```

### 3. Load from NEW Format Directory Only
```python
# Load only from IPEKYOLU_RAG_VERISETI
qa_data_path = './IPEKYOLU_RAG_VERISETI'
chatbot = build_turkish_rag_system(qa_data_path)
```

### 4. Load from OLD Format Directory Only
```python
# Load only from data folder
qa_data_path = './data'
chatbot = build_turkish_rag_system(qa_data_path)
```

### 5. Load from Single JSON File
```python
# Load just one file (NEW format)
qa_data_path = './IPEKYOLU_RAG_VERISETI/01_TEMEL_BILGILER/1.1_hakkimizda.json'
chatbot = build_turkish_rag_system(qa_data_path)

# Or OLD format
qa_data_path = './data/hakkimizda.json'
chatbot = build_turkish_rag_system(qa_data_path)
```

### 4. Ask Questions with Enhanced Source Display
```python
# Ask a question
result = chatbot.ask("Yapay zeka eğitimi veriyor musunuz?")
```

**Output now includes source IDs:**
```
📚 Bilgi tabanından 3 kaynak kullanıldı:

  Kaynak 1: [TEMEL_BILGILER > Genel Bilgiler] (Öncelik: high)
    Kaynak ID'leri: 85
    Soru: Yapay zeka eğitimi veriyor musunuz?
    Anahtar Kelimeler: yapay zeka, ai, yapay zeka 101
```

### 5. Batch Test Multiple Questions
```python
test_questions = [
    "Merkezinizin genel istatistikleri nelerdir?",
    "Lise seviyesi eğitimleriniz nelerdir?",
    "Telefon numaranız nedir?"
]

batch_test_questions(chatbot, test_questions)
```

---

## 📁 Directory Structure

**IMPORTANT:** Your project has TWO data directories:

### 1. **`./IPEKYOLU_RAG_VERISETI/`** → NEW Format Files
Contains hierarchically organized JSON files with metadata sections:
- ✅ `01_TEMEL_BILGILER/` - Basic information with metadata
- ✅ `02_EGITIM_VE_KATILIM/` - Education programs with metadata
- ✅ `03_BASARILAR_VE_TAKIM/` - Achievements with metadata
- ✅ And more organized subdirectories...

### 2. **`./data/`** → OLD Format Files (Backward Compatible)
Contains flat JSON files without metadata sections:
- ✅ `AnaSayfa.json`
- ✅ `ArgeCalismalarimiz.json`
- ✅ `atolyelerimiz.json`
- ✅ `basarilarimiz.json`
- ✅ `BasindaBiz.json`
- ✅ `hakkimizda.json`
- ✅ `iletisim.json`
- ✅ `KariyerVeEtkinliklerimiz.json`
- ✅ `Linkedin.json`
- ✅ `sss.json`

**The system loads BOTH directories by default!** This gives you the complete dataset.

---

## Key Features

### Automatic Format Detection
✅ No need to specify which format you're using  
✅ System detects and adapts automatically  
✅ Old files still work without modification

### Enhanced Metadata Tracking
✅ `source_ids`: Track which source documents were used  
✅ `file_version`: Version control for your data  
✅ `last_updated`: Know when data was last modified  
✅ Better categorization with `metadata.category` and `metadata.sub_category`

### Better Debugging
✅ `inspect_json_format()`: See exactly what's in your files  
✅ Enhanced statistics showing categories and file distribution  
✅ Source IDs displayed in chatbot responses

---

## Migration Notes

### If You Have Old Format Files
**No action needed!** The system still supports old format files. They will work exactly as before.

### If You Want to Upgrade Old Files to New Format
Add a `metadata` section at the top:
```json
{
    "metadata": {
        "file_name": "your_file.json",
        "category": "YOUR_CATEGORY",
        "sub_category": "Your Sub Category",
        "last_updated": "2025-11-04",
        "version": "1.0"
    },
    "data": [ ... your existing Q&A pairs ... ]
}
```

And optionally add `source_ids` to each Q&A pair:
```json
{
    "question": "...",
    "answer": "...",
    "source_ids": ["60", "61"],  // Add this
    ...
}
```

---

## Testing Your Setup

Run the demonstration cells in the notebook:

```python
# Test inspection
loader = QADataLoader()
loader.inspect_json_format('./data/AnaSayfa.json')

# Test loading
test_docs = loader.load_from_directory('./data')
loader.print_statistics()

# Test chatbot
qa_data_path = './data'
chatbot = build_turkish_rag_system(qa_data_path)
chatbot.ask("Merkeziniz nedir?")
```

---

## Questions?

If you encounter any issues:
1. Use `inspect_json_format()` to check your file structure
2. Verify JSON syntax is valid
3. Check that `data` array exists in your JSON
4. Make sure file encoding is UTF-8

---

**Happy coding! 🚀**

