"""Service for managing conversations and chat history."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from app.models.conversation import Conversation, Message
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history and messages."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_conversation(
        self,
        user: User,
        title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            user_id=user.id,
            organization_id=user.organization_id,
            title=title or "New Conversation"
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        logger.info(f"Created conversation {conversation.id} for user {user.id}")
        return conversation
    
    def get_conversation(
        self,
        conversation_id: uuid.UUID,
        user: User
    ) -> Optional[Conversation]:
        """Get a conversation by ID (with user access check)."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
            Conversation.organization_id == user.organization_id
        ).first()
        
        return conversation
    
    def list_conversations(
        self,
        user: User,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """List conversations for a user."""
        conversations = self.db.query(Conversation).filter(
            Conversation.user_id == user.id,
            Conversation.organization_id == user.organization_id
        ).order_by(desc(Conversation.updated_at)).offset(skip).limit(limit).all()
        
        return conversations
    
    def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            sources=sources
        )
        self.db.add(message)
        
        # Update conversation updated_at
        from sqlalchemy import func
        conversation.updated_at = func.now()
        
        self.db.commit()
        self.db.refresh(message)
        
        logger.info(f"Added {role} message to conversation {conversation.id}")
        return message
    
    def get_messages(
        self,
        conversation_id: uuid.UUID,
        user: User,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get messages for a conversation."""
        # Verify access
        conversation = self.get_conversation(conversation_id, user)
        if not conversation:
            return []
        
        query = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_conversation_history_for_lightrag(
        self,
        conversation_id: uuid.UUID,
        user: User,
        max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for LightRAG.
        
        Returns list of dicts with 'role' and 'content' keys.
        Format: [{"role": "user", "content": "..."},  {"role": "assistant", "content": "..."}]
        """
        messages = self.get_messages(conversation_id, user, limit=max_messages)
        
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        logger.info(f"Retrieved {len(history)} messages for LightRAG context")
        return history
    
    def update_conversation_title(
        self,
        conversation_id: uuid.UUID,
        user: User,
        title: str
    ) -> Optional[Conversation]:
        """Update conversation title."""
        conversation = self.get_conversation(conversation_id, user)
        if not conversation:
            return None
        
        conversation.title = title
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        user: User
    ) -> bool:
        """Delete a conversation and all its messages."""
        conversation = self.get_conversation(conversation_id, user)
        if not conversation:
            return False
        
        self.db.delete(conversation)
        self.db.commit()
        
        logger.info(f"Deleted conversation {conversation_id}")
        return True

