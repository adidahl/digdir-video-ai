import { useState } from "react";
import Header from "../components/layout/Header";
import ChatInterface from "../components/chat/ChatInterface";

export default function Search() {
  const [conversationId, setConversationId] = useState<string | null>(null);

  return (
    <div>
      <Header />
      
      <div style={{ maxWidth: "1400px", margin: "0 auto", padding: "2rem" }}>
        <div style={{
          backgroundColor: "#fff",
          borderRadius: "8px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          overflow: "hidden",
        }}>
          <ChatInterface
            conversationId={conversationId}
            onConversationChange={(id) => setConversationId(id || null)}
          />
        </div>
      </div>
    </div>
  );
}
