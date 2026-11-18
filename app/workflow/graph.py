"""Controlled LangGraph execution with a durable SQL human-review boundary.

Extraction graph ends at pending candidates. A separate authenticated confirmation
request starts the resume graph from SQL state. No process-local interrupt/checkpoint
is required; restarting the API cannot lose pending review or bypass confirmation.
"""
import re
from typing import TypedDict, Any
from uuid import UUID
from fastapi import HTTPException
from langgraph.graph import StateGraph, START, END
from sqlalchemy import select
from app.llm.extraction import extract
from app.models.action_item import ActionItem
from app.services.access import require_meeting
from app.workflow.tools import ToolContext, execute_tool


class ExtractionState(TypedDict,total=False):
    meeting_id: str
    meeting: dict
    extracted: Any
    knowledge_sources: list[dict]
    candidates: list[Any]
    status: str


def run_extraction(meeting_id: UUID, context: ToolContext, llm):
    session,user=context.session,context.user

    def load(state):
        meeting=execute_tool('get_meeting',{'meeting_id':str(meeting_id)},context)
        if session.scalar(select(ActionItem.id).where(ActionItem.meeting_id==meeting_id).limit(1)):
            raise HTTPException(409,'Candidates already exist; review existing candidates')
        session.commit()
        return {'meeting':meeting}

    def extract_node(state):
        return {'extracted':extract(state['meeting']['content'],llm)}

    def needs_knowledge(state):
        return 'retrieve_knowledge' if re.search(r'制度|SOP|P1|P2|按.{0,8}流程',state['meeting']['content'],re.I) else 'save_candidates'

    def retrieve_node(state):
        content=state['meeting']['content']
        match=re.search(r'.{0,40}(?:制度|SOP|P1|P2|流程).{0,80}',content,re.I)
        sources=execute_tool('search_knowledge',{'query':match.group(0) if match else content[:200],'k':3},context)
        return {'knowledge_sources':[{k:v for k,v in s.items() if k!='content'} for s in sources]}

    def save(state):
        meeting=require_meeting(session,meeting_id,user,lock=True)
        if meeting.content!=state['meeting']['content']:
            raise HTTPException(409,'Meeting changed during extraction')
        if session.scalar(select(ActionItem.id).where(ActionItem.meeting_id==meeting_id).limit(1)):
            raise HTTPException(409,'Concurrent extraction already saved candidates')
        items=[ActionItem(meeting_id=meeting_id,task=x.task,assignee_name=x.assignee_name,
                          due_date_text=x.deadline,evidence=x.evidence) for x in state['extracted'].action_items]
        session.add_all(items);session.commit()
        return {'candidates':items}

    def review(state):
        return {'status':'awaiting_human_review' if state['candidates'] else 'completed_no_actions'}

    builder=StateGraph(ExtractionState)
    builder.add_node('load_meeting',load)
    builder.add_node('extract_and_validate',extract_node)
    builder.add_node('retrieve_knowledge',retrieve_node)
    builder.add_node('save_candidates',save)
    builder.add_node('human_review_boundary',review)
    builder.add_edge(START,'load_meeting')
    builder.add_edge('load_meeting','extract_and_validate')
    builder.add_conditional_edges('extract_and_validate',needs_knowledge,{'retrieve_knowledge':'retrieve_knowledge','save_candidates':'save_candidates'})
    builder.add_edge('retrieve_knowledge','save_candidates')
    builder.add_edge('save_candidates','human_review_boundary')
    builder.add_edge('human_review_boundary',END)
    return builder.compile().invoke({'meeting_id':str(meeting_id),'knowledge_sources':[]},{'recursion_limit':10})


class ConfirmationState(TypedDict,total=False):
    candidate_id: str
    revision: int
    task: Any


def run_confirmation(candidate_id: UUID, revision: int, context: ToolContext):
    def create(state):
        return {'task':execute_tool('create_task',{'candidate_id':state['candidate_id'],'revision':state['revision']},context)}
    builder=StateGraph(ConfirmationState)
    builder.add_node('confirmed_create_task',create)
    builder.add_edge(START,'confirmed_create_task')
    builder.add_edge('confirmed_create_task',END)
    return builder.compile().invoke({'candidate_id':str(candidate_id),'revision':revision},{'recursion_limit':3})['task']
