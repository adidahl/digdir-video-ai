import { Card, Button, Paragraph } from "@digdir/designsystemet-react";
import type { Message, MessageSource } from "../../types/chat";

interface MessageBubbleProps {
  message: Message;
  onSourceClick: (source: MessageSource) => void;
}

export default function MessageBubble({ message, onSourceClick }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const formatTime = (timestamp: number): string => {
    const mins = Math.floor(timestamp / 60);
    const secs = Math.floor(timestamp % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        width: "100%",
      }}
    >
      <div
        style={{
          maxWidth: "70%",
          display: "flex",
          flexDirection: "column",
          alignItems: isUser ? "flex-end" : "flex-start",
        }}
      >
        <Card
          style={{
            padding: "1rem",
            backgroundColor: isUser ? "#0062BA" : "#fff",
            color: isUser ? "#fff" : "#000",
            borderRadius: "12px",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          }}
        >
          <Paragraph
            style={{
              margin: 0,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {message.content}
          </Paragraph>
        </Card>

        {/* Sources for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div
            style={{
              marginTop: "0.5rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              width: "100%",
            }}
          >
            <Paragraph
              style={{
                fontSize: "0.875rem",
                color: "#666",
                margin: "0.5rem 0 0 0",
              }}
            >
              Sources:
            </Paragraph>
            {message.sources.map((source, index) => (
              <Card
                key={index}
                style={{
                  padding: "0.75rem",
                  backgroundColor: "#f5f5f5",
                  border: "1px solid #e0e0e0",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "background-color 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "#e8f4f8";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "#f5f5f5";
                }}
                onClick={() => onSourceClick(source)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ flex: 1 }}>
                    <Paragraph
                      style={{
                        margin: 0,
                        fontWeight: "bold",
                        fontSize: "0.875rem",
                      }}
                    >
                      {source.video_title}
                    </Paragraph>
                    <Paragraph
                      style={{
                        margin: "0.25rem 0 0 0",
                        fontSize: "0.75rem",
                        color: "#666",
                      }}
                    >
                      {formatTime(source.timestamp)}
                    </Paragraph>
                    {source.text && (
                      <Paragraph
                        style={{
                          margin: "0.5rem 0 0 0",
                          fontSize: "0.75rem",
                          color: "#333",
                        }}
                      >
                        {source.text}
                      </Paragraph>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    style={{ marginLeft: "0.5rem" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSourceClick(source);
                    }}
                  >
                    Watch
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <Paragraph
          style={{
            fontSize: "0.75rem",
            color: "#999",
            margin: "0.25rem 0.5rem 0 0.5rem",
          }}
        >
          {new Date(message.created_at).toLocaleTimeString()}
        </Paragraph>
      </div>
    </div>
  );
}

