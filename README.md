A Technical Whitepaper on a Video AI RAG Pipeline

1.0 Introduction

Modern enterprises like DIgDir are confronting a compounding knowledge debt, where vast archives of unstructured video content—from strategic meetings to technical training—grow daily, yet the intelligence within remains inaccessible. This creates a strategic intelligence gap, locking valuable insights away from those who need them most, hindering organizational agility, and stifling innovation. Without the ability to effectively search and retrieve this institutional knowledge, enterprises face duplicated effort, delayed decisions, and a persistent inability to leverage their own expertise.

This whitepaper details a successful Proof-of-Concept (POC) for a Video AI Retrieval-Augmented Generation (RAG) pipeline, architected to resolve this challenge. The pipeline is designed to systematically transcribe, index, and transform passive video assets into a fully searchable, interactive enterprise knowledge base. By converting spoken content into structured, queryable data, the solution unlocks the value trapped within these media files.

The following sections provide a comprehensive overview of the solution architecture, an analysis of the core technology stack, a step-by-step review of the implementation, and an exploration of its strategic business value.

2.0 Solution Architecture Overview

The strategic success of a modern AI system depends on a modular, end-to-end architecture that is both robust and scalable. The design of this Video AI RAG pipeline prioritizes a logical and transparent data flow, from initial ingestion to intelligent retrieval. This section provides a high-level blueprint of the POC's operational stages and the technology stack that powers them.

The pipeline processes video content through a sequence of five distinct stages:

1. Video Ingestion: Local video files (video1.mp4, video2.mp4) are identified and prepared for processing.
2. AI-Powered Transcription: OpenAI's Whisper model transcribes the video content, generating precise text segments with associated timestamps.
3. Data Structuring & Indexing: Transcribed segments are formatted into structured contexts and ingested into the LightRAG framework for semantic indexing.
4. Dual-Strategy Persistence: The structured data is exported and loaded into two distinct database systems: a PostgreSQL database for vector-enabled querying and a Neo4j graph database for contextual relationship mapping.
5. Intelligent Retrieval: A user query triggers a semantic search across the indexed data, retrieving the most relevant video segments with actionable timestamps.

The core technologies were architected to create a powerful, integrated, and flexible system.

Component	Selected Technology	Role in the Pipeline
Video Transcription	OpenAI Whisper (large model)	Transcribes video audio into precise text segments with timestamps, forming the foundational data layer.
RAG Orchestration	LightRAG	Acts as the central framework for managing the RAG pipeline, handling data indexing and integration with the embedding and language models.
Embedding & LLM	OpenAI (openai_embed, gpt_4o_mini_complete)	Converts text into numerical vectors for semantic search. gpt_4o_mini_complete is the configured LLM, making the pipeline inherently generative-ready for summarization or Q&A tasks.
Structured/Vector Store	PostgreSQL	Serves as the primary structured database for video segments, designed to be extended with vector capabilities (pgvector) for fast, operational semantic search.
Graph Context Store	Neo4j	Models the transcribed data as a graph, enabling the analytical exploration of complex relationships between videos, segments, and topics.

This high-level architecture provides the foundation for a deeper analysis of each component's specific role and contribution to the overall solution.

3.0 Core Technology Stack Analysis

The technology stack was architected to leverage best-in-class, loosely coupled components, ensuring each stage of the pipeline is optimized for its specific task. This approach maximizes accuracy, efficiency, and future extensibility. This section analyzes the rationale behind each key component.

3.1 Video Transcription: OpenAI Whisper

OpenAI Whisper serves as the foundational component of the entire pipeline, responsible for the critical first step of data extraction. The POC utilizes the "large" model variant to ensure the highest possible transcription accuracy. Whisper's key function is not just converting speech to text, but doing so while generating precise, segment-level timestamps. These timestamps are essential, as they enable the final application to link a user's query directly to the exact moment in a video where the relevant topic is discussed, making the retrieved information immediately actionable.

3.2 RAG Orchestration: LightRAG

LightRAG functions as the central nervous system of the pipeline, orchestrating the core RAG process. It ingests the prepared text segments, managing the internal text splitting and chunking strategy, and generating the corresponding vector embeddings for indexing via its configured openai_embed function. Crucially, the architecture is inherently generative-ready. By configuring gpt_4o_mini_complete as the llm_model_func at initialization, the pipeline is immediately capable of performing advanced generative tasks—such as abstractive question-answering or summarization—that build upon the retrieved video contexts, even though this POC focuses on the retrieval component.

3.3 Dual-Persistence Strategy: PostgreSQL and Neo4j

The architecture deliberately employs a dual-database strategy to decouple operational retrieval from analytical exploration. This design is not redundant; it provides two complementary data models that serve distinct query patterns, creating a more robust and versatile knowledge base capable of satisfying both application-level and analytical requirements.

3.3.1 PostgreSQL for Vector-Enabled Structured Storage

PostgreSQL acts as the primary datastore for operational, low-latency semantic retrieval. The POC establishes a video_segments table with a well-defined schema (id, video_id, segment_id, start, "end", text, url) to house the structured data. This relational model is optimized for the "find-the-needle" task where an application needs a fast, precise answer. Utilizing a standard relational database that can be enhanced with vector extensions like pgvector presents a cost-effective and integration-friendly pattern for deploying efficient, large-scale semantic search capabilities.

3.3.2 Neo4j for Graph-Based Contextual Relationships

Neo4j is used to model the same data as an interconnected graph, designed for analytical, exploratory analysis. In this model, each video and its transcript segments are represented as nodes, linked by a (:Video)-[:HAS_SEGMENT]->(:VideoSegment) relationship. This graph structure is optimized for the "understand-the-haystack" task, uncovering latent connections and patterns across the entire dataset. This graph structure enables complex queries such as, "Find all projects discussed by Speaker X in Q3 that are also related to the 'data sharing' initiative," a task that is prohibitively complex for a relational or vector-only store.

This technical foundation provides the "what" of the solution; the next section details the "how" of its implementation.

4.0 Step-by-Step Implementation of the Proof-of-Concept

This section provides a clear, narrative walkthrough of the four primary phases of the POC's execution. It translates the technical operations from the source code into a logical sequence, demonstrating how raw video files are transformed into an intelligent, queryable asset.

4.1 Phase 1: Video Processing and Transcription

The process begins by configuring the paths to local video files, video1.mp4 and video2.mp4. The transcribe_video function executes the Whisper model against each file, automatically detecting the language and generating a detailed transcription. The output is a collection of structured data segments, each containing the transcribed text along with its precise start and end time. This raw output is systematically saved to a transcripts_segments.jsonl file, creating a durable, reusable data source for all subsequent steps.

4.2 Phase 2: Data Preparation and Indexing

With the raw transcripts available, the next phase prepares this data for the RAG framework. Each segment record from the JSONL file is transformed into a standardized "context" string by prepending a metadata header (e.g., [video_id=video1;start=10.5;end=25.2;segment_id=1]) to the transcribed text. This practice of embedding structured metadata directly within the text context is a crucial RAG pattern. It ensures that each retrieved chunk is a self-contained unit of information, eliminating the need for secondary lookups and simplifying the process of grounding an LLM's response with verifiable source data. These prepared contexts are then inserted into the LightRAG instance using rag.ainsert for semantic indexing.

4.3 Phase 3: Data Persistence in External Databases

To ensure long-term storage and enable diverse query capabilities, the structured segments are exported to an intermediate file, chunks_for_db.jsonl. After the initial transcripts are generated into transcripts_segments.jsonl, they are loaded, formatted with metadata, and then exported as a clean, persistence-ready dataset to chunks_for_db.jsonl. This intermediate file acts as a canonical source for idempotently populating both the relational and graph databases.

* PostgreSQL Ingestion: The system connects to PostgreSQL and executes a CREATE TABLE statement to ensure the video_segments table exists. It then iterates through the records in chunks_for_db.jsonl, using an INSERT ... ON CONFLICT statement to efficiently load each segment into the relational table.
* Neo4j Ingestion: Concurrently, for each record in the same source file, a Cypher query is executed against the Neo4j database. The query uses MERGE to intelligently create :Video and :VideoSegment nodes and establish the :HAS_SEGMENT relationship between them, effectively building the knowledge graph segment by segment.

4.4 Phase 4: Semantic Retrieval and Interaction

The final phase demonstrates the pipeline's core retrieval value through the search_segments_async function. For the purposes of this POC, the function pre-computes and caches the embeddings for all video segments into an in-memory NumPy array. When a user provides a natural language query, such as "Når snakker de om datadeling og plattform?", the function computes the query's embedding. The search operation is then executed as a highly efficient cosine similarity calculation between the query vector and this cached array, allowing for rapid, real-time retrieval without immediate reliance on a dedicated vector database.

The function returns the top matching results, each containing the video_id, start time, relevant text, a relevance score, and a URL designed to link a user directly to that precise moment in the video.

This implementation successfully bridges the gap between raw technical capability and tangible business utility for an organization like DIgDir.

5.0 Business Applications and Strategic Value for DIgDir

The technical capabilities demonstrated in this POC translate directly into tangible business outcomes. By transforming a passive video archive into an active and intelligent corporate asset, the Video AI RAG pipeline offers DIgDir a significant competitive advantage. This section evaluates the primary business applications and their strategic value.

* On-Demand Knowledge Retrieval Employees can find precise information in minutes instead of hours. By asking natural language questions, they receive direct answers backed by a link to the source video at the exact moment a topic was discussed. This capability is powered by the sub-second latency of the semantic cache and the precision of Whisper's timestamping, drastically reducing research time.
* Accelerated Content Discovery Teams can instantly locate all mentions of specific projects, initiatives, or keywords across the entire video library without manual review. This capability is a direct result of transforming unstructured speech into a unified, indexed data layer across both relational and graph models, supporting better-informed strategic planning.
* Enhanced Training and Onboarding Corporate training becomes far more effective. Managers can create curated learning paths with direct links to specific, bite-sized segments from longer instructional videos. This allows for customized, efficient, and just-in-time learning, improving knowledge retention and reducing ramp-up time for new hires.
* Improved Accessibility and Compliance The automatically generated transcripts make all video content fully accessible and searchable, aiding employees with hearing impairments or those who prefer reading. Furthermore, having a complete, time-stamped text record of official proceedings aids in compliance, record-keeping, and governance activities.

This solution empowers DIgDir to leverage its own history and expertise in powerful new ways, fostering a more knowledgeable and efficient workforce.

6.0 Conclusion

This Proof-of-Concept has successfully demonstrated a viable, end-to-end pipeline for unlocking the immense value contained within DIgDir's video archives. The project confirmed that it is possible to systematically ingest, transcribe, index, and query video content, thereby converting a previously opaque data source into a powerful organizational asset.

The primary conclusion is that by leveraging a modern AI stack—including OpenAI Whisper for transcription, LightRAG for orchestration, and a dual-database persistence strategy with PostgreSQL and Neo4j—an organization can transform a static video library into a dynamic, queryable enterprise knowledge base.

This POC establishes a foundational architectural pattern for converting unstructured data streams into queryable assets, positioning DIgDir to build a comprehensive and scalable enterprise intelligence fabric.
