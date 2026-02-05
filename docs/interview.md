# Interview Story – RAG Knowledge Base System

This document maps engineering decisions in this project
to common backend / ML system design interview questions.

## Interview Mapping

Key engineering decisions mapped to common system design questions:

| Interview Question | System Implementation |
| :--- | :--- |
| **"How do you prevent hallucinations?"** | **Quality Gate + Prompt Hardening**: We enforce strict strict system prompts ("only use context") and a post-generation Quality Gate that verifies citations against source text. |
| **"What happens when the model delivers a bad answer?"** | **Deterministic Fallback**: Bad answers are caught by the gate, discarded, and replaced with a safe, grounded summary of the retrieved documents. |
| **"How do you test stochastic LLM behavior?"** | **Mocked Regression Tests**: We use a file-based mocking mechanism to simulate LLM outputs, allowing us to deterministically test the Quality Gate logic without API costs or variance. |
| **"How do you debug production failures?"** | **Error Taxonomy + Structured Metrics**: Failures are typed (e.g., `evidence_miss`, `prompt_violation`) and logged in structured JSON for aggregation and alerting. |
