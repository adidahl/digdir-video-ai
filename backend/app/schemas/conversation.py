"""Pydantic schemas for conversation/chat functionality."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class MessageSource(BaseModel):
    """Source reference for a message (video segment)."""
    video_id: str
    video_title: str
    timestamp: float
    text: str
    url: str  # URL to video player with timestamp
    
    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    """Base schema for messages."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    

class MessageCreate(MessageBase):
    """Schema for creating a message."""
    pass


class MessageResponse(MessageBase):
    """Schema for message responses."""
    id: uuid.UUID
    conversation_id: uuid.UUID
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base schema for conversations."""
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""
    pass


class ConversationResponse(ConversationBase):
    """Schema for conversation responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Schema for conversation with all messages."""
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for chat message request."""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Conversation ID for follow-up questions")


class ChatResponse(BaseModel):
    """Schema for chat message response."""
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    sources: List[MessageSource] = []
    created_at: datetime


class DebugSourcesRequest(BaseModel):
    """Schema for debug sources request."""
    query: str = Field(..., min_length=1, description="Query to debug")

