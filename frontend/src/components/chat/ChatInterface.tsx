import { useState, useEffect, useRef } from "react";
import { Button, Textfield, Card, Spinner } from "@digdir/designsystemet-react";
import { chatAPI } from "../../api/chat";
import type { Message, MessageSource } from "../../types/chat";
import MessageBubble from "./MessageBubble";
import VideoPlayerModal from "../video/VideoPlayerModal";
import DebugModal from "./DebugModal";

interface ChatInterfaceProps {
  conversationId?: string | null;
  onConversationChange?: (conversationId: string) => void;
}

export default function ChatInterface({ 
  conversationId: initialConversationId,
  onConversationChange 
}: ChatInterfaceProps) {
  const brandColor = "#1e2b3c";
  const actionButtonStyle = { backgroundColor: brandColor, color: "#fff", borderColor: "#fff", borderWidth: "1px", borderStyle: "solid" };
  const chatHeaderBg = "rgb(243, 215, 151)";
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(initialConversationId || null);
  const [selectedSource, setSelectedSource] = useState<MessageSource | null>(null);
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);
  const [isDebugModalOpen, setIsDebugModalOpen] = useState(false);
  const [debugQuery, setDebugQuery] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversation history if conversationId is provided
  useEffect(() => {
    if (initialConversationId) {
      loadConversation(initialConversationId);
    }
  }, [initialConversationId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadConversation = async (convId: string) => {
    try {
      const conversation = await chatAPI.getConversation(convId);
      setMessages(conversation.messages);
      setCurrentConversationId(convId);
      if (onConversationChange) {
        onConversationChange(convId);
      }
    } catch (error) {
      console.error("Error loading conversation:", error);
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);

    // Add user message to UI immediately
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: currentConversationId || "",
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      const response = await chatAPI.sendMessage({
        message: userMessage,
        conversation_id: currentConversationId,
      });

      // Update conversation ID if this was a new conversation
      if (!currentConversationId && response.conversation_id) {
        setCurrentConversationId(response.conversation_id);
        if (onConversationChange) {
          onConversationChange(response.conversation_id);
        }
      }

      // Replace temp message and add assistant response
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== tempUserMessage.id);
        // Generate unique IDs for user and assistant messages
        const userMessageId = `user-${Date.now()}-${Math.random()}`;
        const assistantMessageId = response.message_id;
        return [
          ...filtered,
          {
            id: userMessageId,
            conversation_id: response.conversation_id,
            role: "user",
            content: userMessage,
            created_at: new Date().toISOString(),
          },
          {
            id: assistantMessageId,
            conversation_id: response.conversation_id,
            role: "assistant",
            content: response.answer,
            sources: response.sources,
            created_at: response.created_at,
          },
        ];
      });
    } catch (error) {
      console.error("Error sending message:", error);
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMessage.id));
      alert("Failed to send message. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSourceClick = (source: MessageSource) => {
    setSelectedSource(source);
    setIsVideoModalOpen(true);
  };

  const handleNewConversation = () => {
    setCurrentConversationId(null);
    setMessages([]);
    setInput("");
    if (onConversationChange) {
      onConversationChange("");
    }
  };

  const handleDebugClick = () => {
    // Find the last user message
    const lastUserMessage = [...messages].reverse().find(m => m.role === "user");
    if (lastUserMessage && lastUserMessage.content) {
      setDebugQuery(lastUserMessage.content);
      setIsDebugModalOpen(true);
    } else if (input.trim()) {
      // If no previous message, use current input
      setDebugQuery(input.trim());
      setIsDebugModalOpen(true);
    } else {
      alert("Please enter a query or send a message first to debug");
    }
  };

  return (
    <div style={{ 
      display: "flex", 
      flexDirection: "column", 
      height: "100%",
      maxHeight: "calc(100vh - 200px)",
      minHeight: "600px"
    }}>
      {/* Header */}
      <div style={{ 
        display: "flex", 
        alignItems: "center",
        gap: "0.75rem",
        padding: "1rem",
        borderBottom: "1px solid #e0e0e0",
        backgroundColor: chatHeaderBg
      }}>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <Button 
            size="sm" 
            variant="tertiary"
            onClick={handleDebugClick}
            title="Debug source extraction for last query"
            disabled={messages.length === 0 && !input.trim()}
            style={actionButtonStyle}
          >
            🐛 Debug
          </Button>
          <Button 
            size="sm" 
            variant="secondary"
            onClick={handleNewConversation}
            style={actionButtonStyle}
          >
            New Conversation
          </Button>
        </div>
        <h2 style={{ margin: 0, color: brandColor }}>Video Search Assistant</h2>
      </div>

      {/* Messages Area */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        backgroundColor: "#f9f9f9"
      }}>
        {messages.length === 0 && (
          <div style={{ 
            textAlign: "center", 
            color: "#666", 
            marginTop: "2rem" 
          }}>
            <p>Start a conversation by asking about your videos!</p>
            <p style={{ fontSize: "0.9rem" }}>
              Try: "What is discussed about [topic]?" or "Tell me about [subject]"
            </p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onSourceClick={handleSourceClick}
          />
        ))}

        {isLoading && (
          <div style={{ display: "flex", justifyContent: "flex-start" }}>
            <Card style={{ padding: "1rem" }}>
              <Spinner size="small" />
              <span style={{ marginLeft: "0.5rem" }}>Thinking...</span>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{ 
        padding: "1rem", 
        borderTop: "1px solid #e0e0e0",
        backgroundColor: brandColor
      }}>
        <form onSubmit={handleSend} style={{ display: "flex", gap: "0.5rem" }}>
          <div style={{ flex: 1, backgroundColor: brandColor, padding: "0.25rem", borderRadius: "6px" }}>
            <Textfield
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your videos..."
              disabled={isLoading}
              style={{ width: "100%", backgroundColor: "#fff", borderRadius: "4px" }}
            />
          </div>
          <Button 
            type="submit" 
            disabled={!input.trim() || isLoading}
            style={actionButtonStyle}
          >
            Send
          </Button>
        </form>
      </div>

      {/* Video Modal */}
      <VideoPlayerModal
        isOpen={isVideoModalOpen}
        onClose={() => setIsVideoModalOpen(false)}
        source={selectedSource}
      />

      {/* Debug Modal */}
      <DebugModal
        isOpen={isDebugModalOpen}
        onClose={() => setIsDebugModalOpen(false)}
        query={debugQuery}
      />
    </div>
  );
}

