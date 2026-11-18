import hashlib
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL
from fastapi import HTTPException
from sqlalchemy import select, delete, or_, and_
from sqlalchemy.orm import Session
from app.models.knowledge import CompanyDocument, KnowledgeChunk
from app.models.meeting import Meeting
from app.models.user import User
from app.rag.chunking import chunks
from app.rag.embedding import Embedder, MODEL_ID
from app.services.access import require_meeting


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def company_id(slug: str) -> UUID:
    return uuid5(NAMESPACE_URL,'meeting-assistant:synthetic-company:'+slug)


def ingest_company(session: Session, embedder: Embedder) -> int:
    count = 0
    for path in sorted(Path('data/company_docs').glob('*.md')):
        text = path.read_text()
        if not text.strip() or 'Synthetic / Fictional Dataset' not in text:
            raise ValueError('Company ingestion only accepts the bundled synthetic documents')
        title = text.splitlines()[0].lstrip('# ').strip()
        parts = chunks(text,'company_document')
        vectors = embedder.encode([p['content'] for p in parts])
        # 串行化同一固定文档的重复入库，无需额外队列。
        from sqlalchemy import text as sql_text
        session.execute(sql_text('SELECT pg_advisory_xact_lock(:key)'),{'key':company_id(path.stem).int % (2**63-1)})
        doc = session.get(CompanyDocument, company_id(path.stem))
        if doc is None:
            doc = CompanyDocument(id=company_id(path.stem),slug=path.stem,title=title,content=text,content_hash=digest(text))
            session.add(doc)
        else:
            doc.title, doc.content, doc.content_hash = title,text,digest(text)
        session.flush()
        session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.company_document_id==doc.id))
        session.add_all([KnowledgeChunk(source_type='company_document',company_document_id=doc.id,
            source_title=title, source_hash=doc.content_hash,embedding=vector,embedding_model=MODEL_ID,**part)
            for part,vector in zip(parts,vectors,strict=True)])
        count += len(parts)
    session.commit()
    return count


def index_meeting(session: Session, meeting_id: UUID, user: User, embedder: Embedder) -> int:
    meeting = require_meeting(session, meeting_id, user)
    content,title = meeting.content,meeting.title
    session.commit()
    parts = chunks(content,'meeting')
    vectors = embedder.encode([p['content'] for p in parts])
    meeting = require_meeting(session, meeting_id, user,lock=True)
    if (meeting.content,meeting.title) != (content,title):
        raise HTTPException(409,'Meeting changed during indexing')
    session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.meeting_id==meeting_id))
    session.add_all([KnowledgeChunk(source_type='meeting',meeting_id=meeting_id,source_title=title,
        source_hash=digest(content),embedding=vector,embedding_model=MODEL_ID,**part)
        for part,vector in zip(parts,vectors,strict=True)])
    session.commit()
    return len(parts)


def retrieve(session: Session, question: str, user: User, embedder: Embedder, k: int = 5) -> list[dict]:
    vector = embedder.encode([question],query=True)[0]
    distance = KnowledgeChunk.embedding.cosine_distance(vector)
    # 权限过滤在 SQL 的 LIMIT 之前，绝不先取全公司片段再在 Python 隐藏。
    allowed_meetings = select(Meeting.id)
    if not user.is_owner:
        allowed_meetings = allowed_meetings.where(Meeting.creator_user_id==user.id)
    query = select(KnowledgeChunk,distance.label('distance')).where(
        KnowledgeChunk.embedding_model==MODEL_ID,
        or_(KnowledgeChunk.source_type=='company_document',
            and_(KnowledgeChunk.source_type=='meeting',KnowledgeChunk.meeting_id.in_(allowed_meetings)))
    ).order_by(distance,KnowledgeChunk.id).limit(k)
    return [dict(chunk_id=str(chunk.id),source_type=chunk.source_type,source_id=str(chunk.source_id),
                 source_title=chunk.source_title,content=chunk.content,chunk_index=chunk.chunk_index,
                 char_start=chunk.char_start,char_end=chunk.char_end,score=round(1-float(dist),6))
            for chunk,dist in session.execute(query)]
