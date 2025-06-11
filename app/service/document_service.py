from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from typing import List, Optional
import io
from sentence_transformers import SentenceTransformer

from app.models import Document, DocumentChunk

try:
    import fitz
    PDF_LIBRARY = "pymupdf"
except ImportError:
    try:
        from pypdf import PdfReader
        PDF_LIBRARY = "pypdf"
        fitz = None
    except ImportError:
        PDF_LIBRARY = None
        fitz = None

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def process_document(self, file: UploadFile, user_id: int) -> Optional[Document]:
        """Process uploaded document and save to database"""
        try:
            content = await self._extract_content(file)
            
            if len(content.strip()) < 100:
                raise HTTPException(
                    status_code=400, 
                    detail="Document must contain at least 100 characters for meaningful analysis"
                )
            
            file.file.seek(0, 2)  
            file_size = file.file.tell()
            file.file.seek(0)  
            
            document = Document(
                filename=file.filename,
                content=content,
                file_type=file.filename.split('.')[-1].lower(),
                file_size=file_size,
                user_id=user_id
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            await self._create_chunks(document)
            
            return document
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    
    async def _extract_content(self, file: UploadFile) -> str:
        """Extract text content from uploaded files"""
        content = ""
        
        if file.filename.endswith(".pdf"):
            pdf_bytes = await file.read()
            
            if PDF_LIBRARY == "pymupdf" and fitz is not None:
                try:
                    doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
                    content = ""
                    for page in doc:
                        content += page.get_text() + "\n"
                    doc.close()
                except Exception as e:
                    print(f"PyMuPDF failed: {e}")
                    raise
                    
            elif PDF_LIBRARY == "pypdf":
                try:
                    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
                    content = ""
                    for page in pdf_reader.pages:
                        content += page.extract_text() + "\n"
                except Exception as e:
                    print(f"PyPDF failed: {e}")
                    raise
            else:
                raise HTTPException(
                    status_code=500, 
                    detail="No PDF library available. Please install PyMuPDF or pypdf"
                )
                
        elif file.filename.endswith(".txt"):
            content_bytes = await file.read()
            content = content_bytes.decode("utf-8")
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Only PDF and TXT files are allowed."
            )
        
        if not content.strip():
            raise HTTPException(
                status_code=400, 
                detail="File appears to be empty or content could not be extracted"
            )
            
        return content
    
    def _chunk_text(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """Split text into manageable chunks for processing"""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _create_chunks(self, document: Document):
        """Create text chunks and generate embeddings"""
        try:
            chunks = self._chunk_text(document.content)
            
            for i, chunk_text in enumerate(chunks):
                embedding = self.embedding_model.encode(chunk_text).tolist()
                
                chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_text=chunk_text,
                    chunk_index=i,
                    embedding=embedding
                )
                
                self.db.add(chunk)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Chunk creation failed: {str(e)}")
    
    def get_relevant_chunks(self, document_id: int, query: str, top_k: int = 3) -> List[str]:
        """Get most relevant chunks for a query using similarity search"""
        try:
            query_embedding = self.embedding_model.encode(query).tolist()
            
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            if not chunks:
                return []
            
            similarities = []
            for chunk in chunks:
                if chunk.embedding:
                    similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                    similarities.append((chunk.chunk_text, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [chunk_text for chunk_text, _ in similarities[:top_k]]
            
        except Exception as e:
            print(f"Error getting relevant chunks: {str(e)}")
            return []
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))