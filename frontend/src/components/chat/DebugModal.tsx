import { useState, useEffect } from "react";
import { Dialog, DialogBlock, Button, Spinner, Card, Paragraph } from "@digdir/designsystemet-react";
import { chatAPI } from "../../api/chat";

interface DebugModalProps {
  isOpen: boolean;
  onClose: () => void;
  query: string;
}

interface DebugSourceData {
  query: string;
  answer: string;
  vector_context_preview: string;
  mix_context_preview: string;
  vector_headers_count: number;
  mix_headers_count: number;
  vector_headers: Array<[string, string, string, string]>;
  mix_headers: Array<[string, string, string, string]>;
  segment_validations: Array<{
    mode: string;
    video_id: string;
    header_start: number;
    header_segment_id: string;
    found: boolean;
    actual_start: number | null;
    actual_segment_id: number | null;
    segment_text: string | null;
    matches_header: boolean;
  }>;
  parsed_sources: Array<{
    video_id: string;
    video_title: string;
    timestamp: number;
    text: string;
    url: string;
  }>;
  sources_count: number;
}

export default function DebugModal({ isOpen, onClose, query }: DebugModalProps) {
  const [debugData, setDebugData] = useState<DebugSourceData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "vector" | "mix" | "validations" | "sources">("overview");

  useEffect(() => {
    if (isOpen && query) {
      loadDebugData();
    } else {
      setDebugData(null);
      setError(null);
      setActiveTab("overview");
    }
  }, [isOpen, query]);

  const loadDebugData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await chatAPI.getDebugSources(query);
      setDebugData(data);
    } catch (err: any) {
      console.error("Error loading debug data:", err);
      setError(err.response?.data?.detail || err.message || "Failed to load debug data");
    } finally {
      setIsLoading(false);
    }
  };

  const formatHeader = (header: [string, string, string, string]) => {
    const [videoId, start, end, segmentId] = header;
    return `video_id: ${videoId}, start: ${start}s, end: ${end}s, segment_id: ${segmentId}`;
  };

  if (!isOpen) return null;

  return (
    <div style={{ 
      position: "fixed",
      inset: 0,
      zIndex: 9999,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "rgba(0, 0, 0, 0.5)"
    }} onClick={(e) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    }}>
      <div 
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "80vw",
          minWidth: "80vw",
          maxWidth: "80vw",
          maxHeight: "95vh",
          backgroundColor: "white",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
          overflow: "hidden",
          position: "relative"
        }}
      >
        {/* Header */}
        <div style={{
          padding: "1.5rem",
          borderBottom: "1px solid #e0e0e0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexShrink: 0
        }}>
          <h2 style={{ margin: 0, fontSize: "1.5rem", fontWeight: "bold" }}>
            Debug Source Extraction
          </h2>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: "1.5rem",
              cursor: "pointer",
              padding: "0.25rem 0.5rem",
              lineHeight: 1,
              color: "#666"
            }}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          overflowY: "auto",
          overflowX: "hidden",
          padding: "1.5rem",
          minHeight: 0
        }}>
        {isLoading && (
          <div style={{ textAlign: "center", padding: "2rem" }}>
            <Spinner size="large" />
            <p style={{ marginTop: "1rem" }}>Loading debug data...</p>
          </div>
        )}

        {error && (
          <Card style={{ padding: "1rem", backgroundColor: "#fee", marginBottom: "1rem" }}>
            <strong>Error:</strong> {error}
          </Card>
        )}

        {debugData && !isLoading && (
          <div>
            {/* Tabs */}
            <div style={{ 
              display: "flex", 
              gap: "0.5rem", 
              marginBottom: "1.5rem",
              borderBottom: "1px solid #e0e0e0",
              paddingBottom: "0.5rem",
              flexWrap: "wrap"
            }}>
              <Button
                size="sm"
                variant={activeTab === "overview" ? "primary" : "secondary"}
                onClick={() => setActiveTab("overview")}
              >
                Overview
              </Button>
              <Button
                size="sm"
                variant={activeTab === "vector" ? "primary" : "secondary"}
                onClick={() => setActiveTab("vector")}
              >
                Vector Context
              </Button>
              <Button
                size="sm"
                variant={activeTab === "mix" ? "primary" : "secondary"}
                onClick={() => setActiveTab("mix")}
              >
                Mix Context
              </Button>
              <Button
                size="sm"
                variant={activeTab === "validations" ? "primary" : "secondary"}
                onClick={() => setActiveTab("validations")}
              >
                Validations
              </Button>
              <Button
                size="sm"
                variant={activeTab === "sources" ? "primary" : "secondary"}
                onClick={() => setActiveTab("sources")}
              >
                Parsed Sources
              </Button>
            </div>

            {/* Overview Tab */}
            {activeTab === "overview" && (
              <div>
                <Card style={{ padding: "1rem", marginBottom: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Query</h3>
                  <p style={{ fontSize: "1.1rem", fontWeight: "bold" }}>{debugData.query}</p>
                </Card>

                <Card style={{ padding: "1rem", marginBottom: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Answer</h3>
                  <p>{debugData.answer}</p>
                </Card>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
                  <Card style={{ padding: "1rem" }}>
                    <h4 style={{ marginTop: 0 }}>Vector Headers</h4>
                    <p style={{ fontSize: "2rem", fontWeight: "bold", color: "#0066cc" }}>
                      {debugData.vector_headers_count}
                    </p>
                  </Card>
                  <Card style={{ padding: "1rem" }}>
                    <h4 style={{ marginTop: 0 }}>Mix Headers</h4>
                    <p style={{ fontSize: "2rem", fontWeight: "bold", color: "#0066cc" }}>
                      {debugData.mix_headers_count}
                    </p>
                  </Card>
                  <Card style={{ padding: "1rem" }}>
                    <h4 style={{ marginTop: 0 }}>Parsed Sources</h4>
                    <p style={{ fontSize: "2rem", fontWeight: "bold", color: "#0066cc" }}>
                      {debugData.sources_count}
                    </p>
                  </Card>
                </div>

                <Card style={{ padding: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Segment Validations</h3>
                  <p>
                    Total: {debugData.segment_validations.length} | 
                    Found: {debugData.segment_validations.filter(v => v.found).length} | 
                    Matches: {debugData.segment_validations.filter(v => v.matches_header).length}
                  </p>
                </Card>
              </div>
            )}

            {/* Vector Context Tab */}
            {activeTab === "vector" && (
              <div>
                <Card style={{ padding: "1rem", marginBottom: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Vector Mode Context ({debugData.vector_headers_count} headers)</h3>
                  <pre style={{ 
                    backgroundColor: "#f5f5f5", 
                    padding: "1.5rem", 
                    borderRadius: "4px",
                    overflowX: "auto",
                    fontSize: "0.9rem",
                    maxHeight: "600px",
                    overflowY: "auto",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word"
                  }}>
                    {debugData.vector_context_preview}
                  </pre>
                </Card>

                <Card style={{ padding: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Vector Headers</h3>
                  {debugData.vector_headers.length > 0 ? (
                    <ul style={{ listStyle: "none", padding: 0 }}>
                      {debugData.vector_headers.map((header, idx) => (
                        <li key={idx} style={{ 
                          padding: "0.5rem", 
                          marginBottom: "0.5rem",
                          backgroundColor: "#f9f9f9",
                          borderRadius: "4px"
                        }}>
                          {formatHeader(header)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No headers found</p>
                  )}
                </Card>
              </div>
            )}

            {/* Mix Context Tab */}
            {activeTab === "mix" && (
              <div>
                <Card style={{ padding: "1rem", marginBottom: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Mix Mode Context ({debugData.mix_headers_count} headers)</h3>
                  <pre style={{ 
                    backgroundColor: "#f5f5f5", 
                    padding: "1.5rem", 
                    borderRadius: "4px",
                    overflowX: "auto",
                    fontSize: "0.9rem",
                    maxHeight: "600px",
                    overflowY: "auto",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word"
                  }}>
                    {debugData.mix_context_preview}
                  </pre>
                </Card>

                <Card style={{ padding: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Mix Headers</h3>
                  {debugData.mix_headers.length > 0 ? (
                    <ul style={{ listStyle: "none", padding: 0 }}>
                      {debugData.mix_headers.map((header, idx) => (
                        <li key={idx} style={{ 
                          padding: "0.5rem", 
                          marginBottom: "0.5rem",
                          backgroundColor: "#f9f9f9",
                          borderRadius: "4px"
                        }}>
                          {formatHeader(header)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No headers found</p>
                  )}
                </Card>
              </div>
            )}

            {/* Validations Tab */}
            {activeTab === "validations" && (
              <div>
                <Card style={{ padding: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Segment Validations</h3>
                  {debugData.segment_validations.length > 0 ? (
                    <div style={{ overflowX: "auto", overflowY: "visible" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "800px" }}>
                        <thead>
                          <tr style={{ backgroundColor: "#f0f0f0" }}>
                            <th style={{ padding: "0.5rem", textAlign: "left", border: "1px solid #ddd" }}>Mode</th>
                            <th style={{ padding: "0.5rem", textAlign: "left", border: "1px solid #ddd" }}>Video ID</th>
                            <th style={{ padding: "0.5rem", textAlign: "left", border: "1px solid #ddd" }}>Header Start</th>
                            <th style={{ padding: "0.5rem", textAlign: "left", border: "1px solid #ddd" }}>Actual Start</th>
                            <th style={{ padding: "0.5rem", textAlign: "left", border: "1px solid #ddd" }}>Found</th>
                            <th style={{ padding: "0.5rem", textAlign: "left", border: "1px solid #ddd" }}>Matches</th>
                            <th style={{ padding: "0.5rem", textAlign: "left", border: "1px solid #ddd" }}>Segment Text</th>
                          </tr>
                        </thead>
                        <tbody>
                          {debugData.segment_validations.map((val, idx) => (
                            <tr key={idx} style={{ 
                              backgroundColor: val.matches_header ? "#e8f5e9" : val.found ? "#fff3e0" : "#ffebee" 
                            }}>
                              <td style={{ padding: "0.5rem", border: "1px solid #ddd" }}>{val.mode}</td>
                              <td style={{ padding: "0.5rem", border: "1px solid #ddd", fontFamily: "monospace", fontSize: "0.85rem" }}>
                                {val.video_id.substring(0, 8)}...
                              </td>
                              <td style={{ padding: "0.5rem", border: "1px solid #ddd" }}>{val.header_start.toFixed(2)}s</td>
                              <td style={{ padding: "0.5rem", border: "1px solid #ddd" }}>
                                {val.actual_start !== null ? `${val.actual_start.toFixed(2)}s` : "N/A"}
                              </td>
                              <td style={{ padding: "0.5rem", border: "1px solid #ddd", textAlign: "center" }}>
                                {val.found ? "✓" : "✗"}
                              </td>
                              <td style={{ padding: "0.5rem", border: "1px solid #ddd", textAlign: "center" }}>
                                {val.matches_header ? "✓" : "✗"}
                              </td>
                              <td style={{ padding: "0.5rem", border: "1px solid #ddd", maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis" }}>
                                {val.segment_text || "N/A"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p>No validations available</p>
                  )}
                </Card>
              </div>
            )}

            {/* Parsed Sources Tab */}
            {activeTab === "sources" && (
              <div>
                <Card style={{ padding: "1rem" }}>
                  <h3 style={{ marginTop: 0 }}>Parsed Sources ({debugData.sources_count})</h3>
                  {debugData.parsed_sources.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                      {debugData.parsed_sources.map((source, idx) => (
                        <Card key={idx} style={{ padding: "1rem", backgroundColor: "#f9f9f9" }}>
                          <h4 style={{ marginTop: 0 }}>
                            {idx + 1}. {source.video_title}
                          </h4>
                          <p><strong>Timestamp:</strong> {source.timestamp.toFixed(2)}s</p>
                          <p><strong>Text:</strong> {source.text}</p>
                          <p style={{ fontSize: "0.9rem", color: "#666" }}>
                            <strong>Video ID:</strong> {source.video_id} | 
                            <strong> URL:</strong> {source.url}
                          </p>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <p>No sources parsed</p>
                  )}
                </Card>
              </div>
            )}
          </div>
        )}
        </div>

        {/* Footer */}
        <div style={{ 
          display: "flex", 
          justifyContent: "flex-end", 
          padding: "1.5rem",
          borderTop: "1px solid #e0e0e0",
          flexShrink: 0
        }}>
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
}
