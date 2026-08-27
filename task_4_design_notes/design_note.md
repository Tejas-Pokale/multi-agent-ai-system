# Task 4 — Production Design Note

## Table of Contents

- [Failure Modes](#failure-modes)
- [Latency vs Quality](#latency-vs-quality)
- [Data Sensitivity](#data-sensitivity)
- [Scaling](#scaling)

---

## Failure Modes

### 1. Incorrect or Hallucinated AI Output

In Task 1, the triage agent could classify a ticket into the wrong product area, category, or urgency, retrieve an irrelevant knowledge-base document, or recommend an inappropriate responder team. In Task 2, the model could overstate account-health concerns, misunderstand the relationship between account-level signals and individual tickets, or identify a churn/escalation risk without sufficient evidence.

- **Detection:** The evaluation harness from Task 3, which tests both systems against known acceptance criteria and adversarial cases. Structured Pydantic outputs also provide a predictable contract for downstream components.
- **Mitigation:** Improving prompts using observed failures, strengthening retrieval/reranking in Task 1, keeping deterministic calculations outside the LLM in Task 2, and using a quality gate so low-scoring model versions are not silently promoted.

### 2. Incorrect or Inconsistent Source Data

This is particularly relevant because the mock data already contains inconsistencies between account-level and ticket-level fields.

- **Approach:** Use `account_id` as the authoritative join key. Use the account record as the source of truth for account attributes, and use the individual ticket record as the source of truth for ticket-specific properties such as urgency, status, and ticket text. For Task 2, the selected analysis date and time window must also be applied deterministically before data is sent to the LLM.
- **Detection:** Schema validation, deterministic data checks, and regression cases designed around inconsistent or incomplete records.
- **Mitigation:** Important conflicts should be surfaced rather than silently "fixed" by the model.

### 3. LLM/API Failure, Timeout, Rate Limiting, or Degraded Latency

Task 1 depends on external inference as part of its retrieval/reranking and reasoning workflow, while Task 2 performs several sequential LLM calls.

- **Requirements:** Request timeouts, bounded retries, structured exception handling, and monitoring of API error rates and latency. The UI should fail gracefully rather than appearing frozen or returning a misleading partial answer.
- **Mitigation:** Model fallbacks, caching deterministic intermediate data, asynchronous execution, and circuit-breaking during prolonged provider failures.
- **Ongoing monitoring:** Evaluation scores and latency should be tracked after every model or prompt change so operational degradation is visible alongside quality degradation.

---

## Latency vs Quality

For Task 2, I made a deliberate trade-off in favor of **output quality and reasoning separation**. Rather than asking one prompt to understand account health, detect risks, and write the final QBR brief simultaneously, the system uses a three-stage LangChain pipeline:

1. Account analysis
2. Risk detection
3. Final synthesis

This requires multiple LLM calls and therefore increases end-to-end latency, but it gives each stage a focused objective and makes the resulting structured output easier to reason about and evaluate. Deterministic metrics such as seat utilization and ticket counts are calculated in Python instead of asking the model to perform arithmetic.

**If latency became the hard constraint**, I would:

- Collapse the three stages into a **single LLM call**
- Keep all deterministic calculations in Python
- Use a smaller/faster model
- Reduce the amount of ticket history sent to the model, prioritizing the most recent or highest-severity tickets rather than the full available history

The trade-off would be lower reasoning separation and potentially weaker risk detection, but substantially lower token usage, API calls, and response time.

---

## Data Sensitivity

Account and support-ticket data can contain PII and commercially sensitive information, so production systems should follow a **data-minimization approach**. The current internship solution sends application context to an external OpenAI model, so a production implementation should first identify information that is unnecessary for the particular reasoning task. Names, email addresses, phone numbers, free-form personal details, and other sensitive fields should be removed, masked, or tokenized when they are not required for the output.

Additional safeguards:

- Avoid writing raw ticket bodies or complete prompts to application logs
- Authenticate and authorize access to the service
- Use encryption in transit for network communication
- Protect stored evaluation/reporting artifacts appropriately
- Configure external model-provider retention and privacy settings according to the organization's requirements

For environments where customer data cannot leave the organization's controlled boundary, the same interfaces could be retained while replacing the external LLM with a privately hosted model.

**Key principle:** The application should send the minimum data required to perform the task, rather than automatically exposing the full account record and ticket history.

---

## Scaling

At **10× the current ticket volume**, the first limitation in Task 2 would likely be **LLM input size, token cost, and latency — rather than pandas filtering**. The current data layer loads the JSON datasets once into memory, which is efficient at the mock-data scale, and ticket filtering itself is straightforward. However, sending increasingly large ticket histories through multiple LLM stages causes the context to grow, increasing token consumption, API cost, latency, and the possibility of exceeding model context limits.

**First architectural change:** Reduce the amount of raw ticket data reaching the model by introducing deterministic pre-filtering, aggregation, chunking, or retrieval so that only the most relevant tickets are included in the reasoning context.

Task 1 would face a similar scaling issue in its retrieval layer. Larger ticket and knowledge-base collections increase semantic retrieval, lexical retrieval, reranking, and multi-hop costs. At that point:

- Local application storage would be replaced or backed by a scalable vector/search service
- Caching could be introduced for repeated retrieval patterns
- Both tasks would benefit from asynchronous processing, concurrency limits, and monitoring of token usage
- Separate metrics should track retrieval latency, model latency, and total request latency

**Key scaling principle:** Keep deterministic processing outside the LLM and minimize the amount of information sent to the model. Ten times more raw data should not result in ten times more prompt tokens or ten times more LLM reasoning.