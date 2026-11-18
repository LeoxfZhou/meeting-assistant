from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.actions import get_llm
from app.core.security import CurrentUser
from app.db.session import get_session
from app.llm.client import LLMClient
from app.rag.embedding import Embedder, get_embedder
from app.rag.service import ingest_company, index_meeting, retrieve
from app.rag.answer import answer_question
from app.models.knowledge import KnowledgeChunk, CompanyDocument
from app.services.access import require_meeting

router=APIRouter(tags=['knowledge'])
DB=Annotated[Session,Depends(get_session)]
Embedding=Annotated[Embedder,Depends(get_embedder)]


class Question(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question: str = Field(min_length=1,max_length=380)
    k: int = Field(default=5,ge=1,le=10)

    @field_validator('question')
    @classmethod
    def valid_question(cls,value):
        if not value.strip() or '\x00' in value:
            raise ValueError('Invalid question')
        return value.strip()


@router.post('/knowledge/company/ingest')
def ingest(session:DB,user:CurrentUser,embedder:Embedding):
    if not user.is_owner:
        raise HTTPException(403,'Owner role required')
    return {'chunks':ingest_company(session,embedder)}


@router.post('/meetings/{meeting_id}/index')
def index(meeting_id:UUID,session:DB,user:CurrentUser,embedder:Embedding):
    return {'chunks':index_meeting(session,meeting_id,user,embedder)}


@router.post('/knowledge/search')
def search(payload:Question,session:DB,user:CurrentUser,embedder:Embedding):
    return {'sources':retrieve(session,payload.question,user,embedder,payload.k)}


@router.post('/knowledge/ask')
def ask(payload:Question,session:DB,user:CurrentUser,embedder:Embedding,llm:Annotated[LLMClient,Depends(get_llm)]):
    sources=retrieve(session,payload.question,user,embedder,payload.k)
    return answer_question(payload.question,sources,llm)


@router.get('/knowledge/chunks/{chunk_id}')
def get_chunk(chunk_id:UUID,session:DB,user:CurrentUser):
    chunk=session.get(KnowledgeChunk,chunk_id)
    if chunk is None:
        raise HTTPException(404,'Chunk not found')
    if chunk.meeting_id:
        require_meeting(session,chunk.meeting_id,user)
    return {'chunk_id':str(chunk.id),'source_type':chunk.source_type,'source_id':str(chunk.source_id),
            'source_title':chunk.source_title,'content':chunk.content,'char_start':chunk.char_start,'char_end':chunk.char_end}


@router.get('/knowledge/documents/{document_id}')
def get_document(document_id:UUID,session:DB,user:CurrentUser):
    doc=session.get(CompanyDocument,document_id)
    if doc is None:
        raise HTTPException(404,'Document not found')
    return {'id':str(doc.id),'title':doc.title,'slug':doc.slug,'content':doc.content}
