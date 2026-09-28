---
name: 03-network-resilience
status: draft
validated: no
executor: auditor
problems-only: true
---

# 03 — Network Resilience

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — severities are composed by this phase, never inherited.**
> Every severity in the report is composed from this phase's own run against
> `## 9`: **record the evidence first, then assign the severity.** Nothing a
> preceding document wrote beside a subject is citable, and a subject found
> already carrying one has been misread.

## 1. Goal

Whether an arbitrary user reference becomes the right validated stream, and whether the resulting transfer survives a hostile, rate-limiting, token-expiring origin.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| Acceptance | Whether a user-supplied reference is acceptable, and the identifier derived from it | A substring match on an unrelated origin; a derived identifier other consumers do not expect |
| Enumeration and selection | Filtering the format list, classifying survivors, ranking them | A capability test that matches one literal; a label that is ranked and offered but not selectable |
| Capture surface | Watching a page's responses to decide which address is the stream | An unconstrained "first address wins"; a size guard that measures after reading |
| Request budgets | Composing a deadline from several terms, per surface | A term dead at the configured floor; one value reused as an unrelated stage's budget |
| Response policy, per layer | The outcome for a status, the retry budget, the delay, the pause | Layers disagreeing on the same status; a retry with no delay; a ceiling applied before the server's value |
| Per-origin etiquette | Effective request rate; declared rate and identity policies across transports | A policy reaching a strict subset; a rate that is the product of two budgets |
| Staleness | Refreshing an expired signed address and rewriting the request | A refreshed manifest on a new base with parts still resolved against the old one; a replacement that changes what is delivered |
| Degradation ladder | Handing off from one transfer method to the next | One rung appending to another's bytes; a stage deleting what the next stage needs |

**In scope:**
- **Extraction:** URL and identifier parsing, CDN-URL normalization, format enumeration, audio-only exclusion, unknown-height resolution, and the full "no usable stream" taxonomy.
- **Surface parity** between the two distinct surfaces of the same third-party downloader (in-process library in a worker thread vs. child process) and the option divergence between them.
- Timeout budget composition (total vs. connect vs. socket-read, and their derivation from one configured value).
- **Retryable-status policy per layer** — the outcome for a given status on each layer that can receive it, the disagreement between layers where they overlap, transport-level failures, the server-supplied delay in every form it may legally arrive in, the precedence of a server-supplied delay over a computed one and where the ceiling applies, the backoff distribution, and per-origin pause coordination at every site that waits.
- Throttled-rate abort-and-retry etiquette; effective request rate as a function of the concurrency and retry budgets.
- Signed-URL staleness; the forced browser re-extraction path that refreshes an expired token and rewrites the request credential.
- The method/fallback degradation ladder, and the invariant that a degraded path must not corrupt the artifact — including that no stage destroys the bytes a later stage needs before that later stage succeeds.
- Certificate-verification policy and its propagation to every transport in the process, with the count of sites that set it and the count of sites that warn recorded as two separate numbers; request-fidelity requirements (user-agent, referer) that the origin enforces.
- Response-size bounds and the chunked-response case with no declared length.

**Out of scope:** the process that performs the transfer → `05`. Permit ownership → `04`. The credential's own lifecycle, permissions and redaction → `06` (this phase owns only the cookie *as a request credential*: injection, refresh, and non-disclosure in request-URL logging). The connection ceiling at the transport layer → `04`. What lands on disk → `07` (this phase owns destruction *ordering*, not retention). What the operator is shown → `08`. The meaning and bounds of a declared setting → `02`. A documented claim → `09`. Licence and terms posture → not an audit subject.

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` (from `.ai/context/commands.md`). `mypy` (strict) is the configured checker; a second checker present in the dev dependency group is **not** the configured one — do not substitute it.
- **No Docker. No database. No third-party origin. No service is started.** This phase's real prerequisite is a **scripted in-process origin** — an object exposing `get(url, headers=..., timeout=...)` returning an async context manager that yields a scripted `(status, headers, body)`, passed in place of the HTTP session — and, for anything that would launch a real binary, a **local stub on `PATH`** that prints its argument vector and its response file byte-for-byte and exits with a chosen status.
- Record for every scripted exchange: request count, wall-clock spacing between requests, the address and headers of each, and the value returned.
- A writable temporary directory, and the ability to invoke the process's own command-line entry point.
- The declared development platform is Windows; see R10(c).
- **Not obtainable from this process, and therefore recorded as a documented skip rather than a silent omission:** whether a child process *enforces* a certificate-verification or transport policy it was handed. The flag's **delivery** is observed in the argument vector; its enforcement belongs to the child. The internal behaviour under failure of the third-party downloader and the browser driver is out of scope by design — state it, do not guess it.

## 4. Discovery

Map the architecture before checking anything. **Use roles, not names.** Never reference a concrete file, module, or class name in this file.

1. **Transport inventory** — Enumerate every distinct way the process reaches the origin, including any in-process library invoked on a worker thread, every child process, and the browser. This list is the denominator for block (e).
2. **Chain map** — Trace the chain from the user-supplied reference through acceptance, enumeration, selection, method choice, transfer, to the written artifact. Record where each stage's inputs come from and where its failures exit.
3. **Layer map** — Identify the manifest fetch and each media-part transfer strategy separately. These are the matrices of block (a); do not merge them.
4. **Policy reach map** — For each declared network-related setting, list the sites that read it. Compare against the transport inventory and record both counts.
5. **Ladder map** — List the transfer methods in dispatch order, and for each, what it leaves on disk and what it hands to the next.
6. **Evidence map** — Search the test tree for the transport library, its timeout, connector and certificate symbols. A subject with no match has no test; declare it uncovered before checking it.

*Role vocabulary:* the acceptance predicate that gates a user-supplied list · the identifier-derivation helper · the extraction surface that runs the third-party downloader as an in-process library · the extraction surface that runs it as a child process · the browser-capture surface and its response interceptor · the format ranker and the declared quality enumeration · the manifest fetch path · the media-part transfer path, parallel and sequential strategies · the per-origin pause coordinator · the delay-derivation and server-delay parsing helpers · the muxer child wrapper · the batch merge stage and the final merge stage · the ladder dispatcher · the forced re-extraction helper · the per-transport connection and verification configuration · the output-path validator · the residue-reporting helper.

## 5. Runtime Verification (mandatory)

**Run before evaluating any dimension.**

> **Mandatory `Method` mandate — carried from this phase's predecessor:** *a **per-endpoint matrix, not a blanket rule**.* Applied here **per layer**: enumerate the outcome per status for each layer separately, and never substitute a blanket rule asserted to cover the whole origin boundary. One matrix per layer, printed separately, is the only acceptable evidence. The same rule governs transport-level policy: assert it on **every** transport, not on one.

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | Per-layer response-status matrix and pause reach | Substitute the scripted origin for the HTTP session. Drive the manifest fetch once per status in {200, 400, 401, 403, 404, 408, 410, 425, 429, 500, 501, 502, 503, 504, 507}, then each media-part transfer strategy once per status in the same set, then once more with the origin raising a connection-level exception instead of responding. **Three matrices, printed separately.** Then search the tree for every call site of the pause-wait helper, print the list, and print the set of sites that can wait without consulting it. The search is **index-scoped, excluding every worktree directory** — whose stale copy of an earlier phase set would otherwise be searched by accident. | Three matrices, each status → request count → delay before the next request → returned value; the pause call-site list; the wait sites not consulting it; the timestamped spacing for a rate-limited response. |
| R2 | Server-supplied delay: permitted forms, precedence, ceiling | Call the delay-parsing helper directly over a header table: integer seconds; non-integer seconds; a number in exponent notation; every date form the specification permits, including the obsolete ones; a date in the past; a date far in the future; two garbage strings. Then run the same table through the full compute-then-clamp path at attempt indices 0..10 with the server value above, below and absent from the computed value; print the value actually waited at each index. | The parsed value for every header form; the waited value for every attempt index under each of the three precedence cases; the index at which the ceiling first binds, and whether the server's value is inside it. |
| R3 | Method ladder: handoff state, artifact integrity, stage ordering | With the scripted origin serving a manifest of known length, force each transfer method to fail in turn by substituting the local stub binary so it writes a partial file and exits non-zero; after each failure record the file list and byte lengths in the output and working directories, and the address and credential the next method received. Then walk the merge stages: run one stage to success, and separately force the *next* stage to fail; after each, record which inputs and which outputs still exist, and the exact record the residue-reporting path emits — **including the case in which it emits nothing**. Repeat with a failure in a *middle* stage rather than the last, and record the shape of the surviving set. | Per forced failure: file inventory, byte lengths, the address and credential handed to the next method. Per stage: the input inventory at stage entry and at stage exit. The residue path's output for each case, including the empty case and the shape of a gapped surviving set. |
| R4 | Intercepted address: selection, normalisation, payload bound | (a) Call the normalisation helper over every address form a page can deliver — absolute with either scheme, scheme-relative, root-relative, bare host, bare relative path, each with and without a query string — printing the result, the branch that produced it, and any branch no input reaches. (b) Feed a response double two qualifying addresses in a fixed order, one from an unrelated origin and one from the expected origin, and print the address the surface settles on and its quality label. (c) Drive the interceptor with a counting-generator body three times — no declared length, a declared length above the cap, exactly the cap — recording the bytes read before any size decision is taken and the decision taken. Repeat (c) for the capture branch as well as the parsing branch. | Normalisation results and the producing branch per form; the list of unreachable branches; the settled address and its label after the two-address feed; bytes-read-before-decision and the decision for each of the three length cases, per branch. |
| R5 | Forced re-extraction: address rewrite, base rewrite, selection change | With the scripted origin refusing the first request and returning a fresh address on a **different host** on the second, and the extraction surface replaced by a stub returning a chosen stream, record: the address used for the manifest before and after; the base each media-part address is resolved against; the credential header on both requests; the height or quality label of the replacement stream against the one selected. Repeat with the caller's selection set to every value the enumeration can produce, and record whether the fresh result is used. | Address before and after refresh; the base used for part resolution; the credential before and after; the replacement label against the selected label; a per-selection table of used or discarded. |
| R6 | Policy reach across transports, and effective request rate | (a) Enumerate every transport the process constructs. (b) For each declared policy, find the sites that read it; print policy → read-site count against transport count. (c) For the verification policy, count **separately** the sites that set the flag and the sites that emit a warning, and print the distance from each flag site to the nearest warning. (d) For request fidelity, print per transport whether the identity headers are present and in what form. (e) Read the whole-item concurrency bound, the per-child bound passed to the child, and any per-transport connection ceiling; print each and their product at the declared ceiling. | The transport inventory; the policy→reach table; the flag-site and warning-site counts with the distance; the per-transport header table; the three bounds and their product. |
| R7 | Per-surface option parity and deadline composition | (a) Capture the option object handed to the in-process library and the argument vector handed to the child (the stub prints its `argv`), and diff them item by item. (b) Evaluate the composed timeout at the smallest, default and largest value the configuration permits; print every term, marking any term that exceeds the term containing it or that is unreachable at that setting. (c) Trace the same value into every other stage that consumes it, recording each consumer and the budget it applies there. | The item-by-item option diff; the three term sets with any exceedance marked; the list of stages that consume the same value and the budget each applies. |
| R8 | Enumeration, classification and selection | Feed a fixed table of format records: video-only, audio-only, a record with no codec key, a non-streaming address whose query string contains the streaming marker, a record with no height, and a record with a height of zero. Print per record whether it survives, how it is classified, and the label it is given. Run the ranker over fixed sets of survivors and print the order. Then take the label produced by the no-height case and run it through the declared enumeration and through a re-request; print what each does. | Survival, classification and label per record; the ranked orders; the enumeration membership of that label; the result of re-requesting it. |
| R9 | Acceptance predicate and derived identifier | Call the acceptance predicate and the identifier derivation over a fixed input list: the canonical form; the canonical pattern inside a foreign origin's query value; the bare pattern with no scheme or origin; a negative identifier component; the canonical form with a trailing path; two near-miss spellings that must be rejected; the canonical form appearing twice in one input. Print accept/reject and the derived identifier for each, then print every consumer of the derived identifier. | The accept/reject and derived-identifier table; the consumer list; which accepted inputs produce a derived identifier those consumers do not expect. |
| R10 | Baselines, coverage declaration, documented skip | (a) `uv run pytest -q -rs`; `uv run ruff check src tests`; `uv run ruff format --check src tests`; `uv run mypy src` — record exit codes, pass/fail/skip counts and every skip reason. Use exactly these. (b) Search the test tree for the transport library and its timeout, connector and certificate symbols; print the match count per subject. **Every subject with a match count of zero has no test: declare it uncovered here, before it is checked.** (c) Platform note: the declared platform is Windows, and R1–R9 are platform-independent because none opens a socket. The one effect not obtainable from this process — whether a child process *enforces* a transport or verification policy it was handed — is emitted as a **documented skip with justification**, never silence. | The four exit codes and their outputs; every skip reason; the transport-symbol match count per subject; the skip line naming the effect, the platform and the reason. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how to obtain its evidence is rewritten here, not skipped at execution time. Every method above is local: the scripted in-process origin and the local stub binary. **No method contacts the third-party origin, and none requires a service to be started.**

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.**

*Baselines, not findings:* R10 is the state the rest is observed against. Under `problems-only` its own results are never filed as findings; they are cited only as the state in which an R1–R9 finding was observed. A zero match count in R10(b) is a statement about the evidence base, not a finding about production code; the absence of coverage is `10`'s subject.

*Documented skips:* a named method that cannot be run is emitted as a **documented skip with justification — never silence**. A silent skip reads under `problems-only` as "no finding". A skip never closes the check it belongs to.

## 6. Audit Dimensions (checks + evidence)

### (a) Per-Layer Response Policy and the Retry Budget

> The same origin response can reach more than one layer, and each layer may map it to a different outcome. Enumerate the layers — the manifest fetch, and each of the transfer strategies that fetch a media part — and build a separate outcome matrix for each: rows are response statuses, columns are request count, delay before the next request, and the value returned. Assume nothing is shared between layers; where a shared constant appears, verify per layer whether it is read. A status handled one way at one layer and another way at the next is the subject.

| Check | Description | Evidence required |
|---|---|---|
| One matrix per layer | The manifest fetch and each transfer strategy have their own status matrix; no layer's row is inferred from another's | R1 |
| Agreement between layers | Where two layers can receive the same status, their outcomes agree, or the disagreement is the finding | R1 |
| Delay before the retry | Every retry path applies a delay derived from the attempt index, not only an attempt count | R1, R2 |
| Transport failure treated as a response | A connection-level failure on a retrying path is delayed and bounded like a response, not retried immediately | R1 |
| Server-supplied delay honoured in every permitted form | The delay a server may legally send is parsed in each form the specification permits, and in each syntactically valid form it happens to be tested | R2 |
| Delay ceiling applied after the server's value | Any ceiling on the wait is applied to the value actually waited, not only to the value computed locally | R2 |
| Pause consulted at every site that waits | Every site that waits consults the shared per-origin pause; a site that waits without consulting it is a finding | R1 |
| Pause keyed at least as widely as the resource it protects | A pause keyed on something narrower than the resource under pressure does not bound the pressure | R1 |

- Evidence: R1, R2.

### (b) The Method Ladder and the Artifact It Must Not Corrupt

> Several transfer methods may be offered, and one may fall back to the next. Force each method to fail in turn, against a scripted origin serving a known-length manifest, and after each forced failure record what the next method receives, what exists on disk, and the byte length of the output. Then walk the stages of the last method in order and record, for each stage, whether the bytes it needs still exist when it starts. A stage that consumes its inputs before the next stage has succeeded destroys data the next stage cannot recover.

| Check | Description | Evidence required |
|---|---|---|
| Each method is a distinct strategy | Two methods that reach the same transfer path are not two strategies; the enumeration of available methods is not overstated | R3 |
| Predecessor's partial removed before handoff | A method that fails leaves nothing a later method will append to; where one handoff removes it and another does not, the asymmetry is the finding | R3 |
| Next stage's inputs exist when it starts | No stage deletes the input a later stage needs before that later stage has succeeded; record the input inventory at each stage's entry and exit | R3 |
| Recovery is actually available | Whatever a failure path announces as retained is retained and is sufficient to finish. Record the announcement for every stage failure **including the case in which it is suppressed**: a path guarded on at least one surviving input emits nothing when nothing survives, and a path announcing a count of a *gapped* set describes a resumable set that is not the one on disk | R3 |
| Artifact not written in place twice | Two stages writing to the same destination cannot compose onto one another's bytes | R3 |
| Degraded path is a real fallback | The fallback receives an address and a credential that are still valid, not the ones the failed stage had | R3, R5 |

- Evidence: R3, R5.

### (c) The Intercepted Stream Address and the Payload It Admits

> One surface watches a page's responses and decides which address is the stream. Ask three things: which captured address wins when several qualify, what normalisation does to each form a page can actually deliver, and what the response-size guard bounds. For the guard, distinguish a decision taken from a declared length against a decision taken from bytes already in memory — they are different controls, and whether the former bounds memory is a separate question from the latter.

| Check | Description | Evidence required |
|---|---|---|
| Selection is constrained | The winning address is constrained by host, by quality, or by both; an unconstrained "first one captured" is a finding | R4 |
| Normalisation form-by-form | Every address form a page can deliver normalises to the address the origin intends: absolute with either scheme, scheme-relative, root-relative, bare host, and a bare relative path | R4 |
| Scheme is not silently downgraded | A plaintext address is not carried forward in plaintext | R4 |
| No unreachable branch | Every branch of the normalisation is reachable; a branch guarded by a condition an earlier branch already consumed is a finding | R4 |
| Guard is a memory bound | Where no declared length is present, the guard stops reading at the cap rather than reading the body and then measuring it | R4 |
| Guard covers every branch | Every branch that admits a response body is subject to the cap, not only the branch that parses it | R4 |
| Guard boundary is exact | The guard triggers *at* the cap and above it, not one byte below | R4 |

- Evidence: R4.

### (d) Address Staleness and the Forced Re-Extraction Path

> A delivered media address carries a signature that expires, and a refusal can be answered by forcing a fresh extraction and rewriting what the request carries. Drive that path if it exists: serve a refusal first and a fresh address on a different host second, then record the address used for the manifest, the base each media-part address is resolved against, and the credential on both requests. Ask what the replacement is *taken from*, and what happens to the parts the caller had already selected.

| Check | Description | Evidence required |
|---|---|---|
| Refresh reaches every derived address | An address obtained by the refresh is used as the base for the parts derived from the original address, not only for the manifest that triggered it | R5 |
| Replacement carries the selected property | The replacement stream carries the property the caller selected; a replacement that cannot express it changes what is delivered | R5 |
| Fresh result is not discarded | A forced re-extraction whose result is discarded, or used only for some selections, is a finding | R5 |
| Credential is rewritten coherently | The request credential is rewritten where the address is, and only where the address is | R5 |
| Non-disclosure holds in the rewritten request | The credential is not disclosed in any log of the rewritten request address | R5 |
| Refusal on a lower layer has a path | A layer that can receive a refusal has a refresh path, or its refusal is terminal and that is stated rather than assumed | R5 |

- Evidence: R5.

### (e) Policy Reach Across Transports and the Effective Request Rate

> The process builds several transports, and a handful of declared policies are supposed to apply to all of them. For each policy, count the transports that read it against the number of transports the process constructs; a policy that reaches a strict subset is a finding, and so is one that reaches a transport with no record that it did. For verification disablement, count the sites that set the flag and the sites that warn as **two separate numbers**, and record the distance between them — a warning raised by a caller is not a warning on the flag. Then compute the peak number of simultaneous requests a single item can make against the origin, as the product of every independent budget on the path.

| Check | Description | Evidence required |
|---|---|---|
| One inventory of transports | Every distinct way the process reaches the origin is enumerated once, including any in-process library invoked on a worker thread and any child process | R6 |
| Policy reach counted per policy | For each declared policy, the count of transports applying it is recorded; it is either all of them or a finding | R6 |
| Flag sites and warning sites counted separately | The number of sites that disable verification and the number that warn are two counts, never assumed equal | R6 |
| Warning travels with the flag | A flag set on a helper that is separately callable is not warned about by only one of its callers | R6 |
| Request-fidelity headers reach every transport | The configured identity headers are present on every transport, and in a form the transport can actually deliver | R6 |
| Enforcement observable from this process | Where a policy is enforced inside a child process, its *delivery* is observed in the argument vector and its *enforcement* is recorded as a documented skip with justification | R6 |
| Throttled-rate reaches the paths it is meant to govern | A declared transfer-rate policy is read by every path that can be throttled, or its absence is a finding | R6 |
| Effective rate computed as a product | The peak simultaneous request count against one origin is computed as the product of the whole-item bound and the per-child bound, at the declared ceiling; the result is recorded even when each factor is individually acceptable | R6 |

- Evidence: R6, R7.

*De-duplication rule:* a gap confined to one of two surfaces of the same third-party tool is recorded here only as a data point in the reach count. The surface-level finding belongs to per-surface option parity and is filed once.

### (f) Per-Surface Option Parity and Deadline Composition

> The same third-party downloader is invoked in two different ways — as an in-process library on a worker thread, and as a child process. Intercept both surfaces and diff their option sets item by item. Separately, a timeout is composed from several terms: record, at the configured floor, the default, and the ceiling, what each term is, which terms derive from the setting and which are literals, whether any term exceeds the term that contains it, and whether the same value is reused unchanged as another stage's budget.

| Check | Description | Evidence required |
|---|---|---|
| Option sets compared item by item | The two surfaces are diffed on the full option set; a setting present on one and absent on the other is a finding on the surface that omits it | R7 |
| The shared value means the same thing on both | Where one value is used as a socket timeout on one surface and as a whole-operation budget on the other, that divergence is stated and is a finding if it is unintended | R7 |
| Dead terms at the configured floor | At the smallest value the configuration permits, no term of the composed timeout exceeds the term that contains it, and no term is unreachable | R7 |
| Derived vs literal terms | Every term is either derived from a declared setting or a literal; a literal that duplicates a bounded setting's purpose is a finding | R7 |
| No value reused as an unrelated stage's budget | A value configured for one stage is not applied unchanged as another stage's budget, especially when the second stage repeats the first | R7 |
| Exported helpers honour the settings model | Publicly exported entry points take their budgets from the settings model, not from literals in their signatures | R7 |

- Evidence: R7.

### (g) Enumeration, Classification and Selection of a Stream

> A format list is filtered, each survivor is classified, and a ranker chooses one. Feed a fixed table of format records — video-only, audio-only, a record with no codec key at all, a non-streaming address whose query string happens to contain the streaming marker, a record with no height — and print what survives, how each survivor is classified, and the order the ranker produces. Then look at what the *unranked* case produces: a value that is ranked, offered to the caller, and carried in an error's list of alternatives, and ask whether it is a member of the declared enumeration.

| Check | Description | Evidence required |
|---|---|---|
| Audio exclusion is by capability | Audio-only formats are excluded by an observed property of the record, not by matching one literal string; a record missing the property entirely is not treated as video | R8 |
| Classification inspects the address's structure | A format is classified by the structure of its address, not by the marker appearing anywhere in it | R8 |
| Unknown-value label is a member | Any label produced by enumeration is a member of the declared enumeration, and re-requesting it succeeds | R8 |
| Unknown-value label is presented consistently | A label offered in the list of alternatives is one the caller can act on; a label that appears in an error's alternatives but is not selectable is a finding | R8 |
| Ranker is total and deterministic | Given the same set, the ranker returns the same order, and never prefers an unknown value over a known one where a known one exists | R8 |
| Every "no usable stream" outcome is distinguishable | The ways a request can fail before bytes arrive are enumerated, and each produces a distinct, actionable outcome | R8 |

- Evidence: R8.

### (h) Acceptance of a User-Supplied Reference

> A predicate decides whether a user-supplied reference is acceptable, and it may gate an entire user-supplied list rather than one item. Feed a fixed table of inputs — the canonical form, the pattern embedded in a foreign origin's query value, the bare pattern with no origin, a negative identifier component, the canonical form with a trailing path, and near-miss spellings that must be rejected — and print accept/reject and the derived identifier for each. Then follow the derived identifier into the log field it populates.

| Check | Description | Evidence required |
|---|---|---|
| Anchored match | Acceptance requires the reference's whole relevant structure to match, not merely to contain the pattern somewhere | R9 |
| Origin constrained | A match inside a query value of an unrelated origin is not acceptance | R9 |
| Component signs validated | A negative or otherwise out-of-range identifier component is rejected at acceptance, not carried forward | R9 |
| Near misses rejected | Spellings that differ by one character or one separator are rejected | R9 |
| Derived identifier is well-formed | The derived identifier is well-formed for everything the predicate accepts, including a bare pattern with no origin | R9 |
| Derived identifier is not load-bearing elsewhere | The derived identifier's other consumers — log fields, name derivation, cache keys — assume the canonical form; an accepted non-canonical input reaches them | R9 |

- Evidence: R9.

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **The child process that performs a transfer** — its argument vector's design, pipe wiring, output draining, exit-status interpretation, and kill escalation → `05`. This phase owns only *which* command-line option is passed and *when*.
- **Concurrency permits and their acquisition count → `04`. The connection ceiling at the transport layer — including any hardcoded literal overriding a bounded setting — is also `04`'s.** This phase files only the **product** of the bounds as an effective request rate against the origin, and must not restate the ceiling itself as a finding. Seam: *the ceiling is a setting-composition defect → `04`; the rate it permits against one origin is a transport-etiquette defect → this phase.*
- **Derivation of shutdown state from a signal, and the event's cross-loop visibility → `04`.** This phase owns only that a wait consults the shutdown event; its delivery and ownership are `04`'s.
- **The credential's lifetime, its file's permission mode, its cleanup, and whether a secret reaches any sink → `06`.** This phase owns the credential **only as a request credential**: its injection, its refresh, and its non-disclosure in any log of a request address. This phase files neither the file's permission mode nor the query-string embedding of the file path as a disclosure — that channel is `06`'s, and it is not re-filed here.
- **Whether a signed value or a secret appears in anything the operator sees → `06`** (whether it appears) **and `08`** (the rendering mechanics). This phase owns only the request-address redaction applied inside the transport layer.
- **What lands on disk** — permission mode, creation mode, atomicity, residue and orphan cleanup, merge-stage disk amplification, the working directory's staleness signature, and the absence of any size or free-space ceiling → `07`. **The single carve-out, owned here:** whether a stage destroys the bytes a later stage needs *before* that later stage succeeds. That is a ladder invariant, not a retention policy, and `07` does not own it.
- **What the operator is shown** — terminal streams, live display, progress, the available-quality line, renderer selection, and the mapping from an outcome to an exit status → `08`. This phase owns only which stream was selected, never how it is rendered. In particular, the appearance of a non-selectable quality label in an error's list of alternatives is `08`'s rendering question and this phase's selection question: file it here as a selection defect and name `08` rather than filing it in both phases.
- **The meaning, bound, sourcing and validation of a declared setting → `02`.** This phase owns only whether the value reaches its consumer and what the consumer does with it. The example environment file's bounds → `02`.
- **A documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09` by R-E; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`. This phase files **no** `DOC-UPDATE` findings. In particular, where a helper's own documentation describes a precedence the implementation contradicts while a test pins the implementation, the contradiction is `09`'s; what this phase files is the runtime behaviour the contradiction is about, once, and not the wording.
- **Whether a file survives being moved** — import graph, layer direction, cycles, facades, bootstrap order → `01`. **File-local craft** — typing, naming, module size, duplication within one file → `09`.
- **A dependency declaration in the build manifest → `11`.**
- **Whether the test suite proves any of this → `10`.** Whether a *finding* from this phase survives validation → `99`.
- **Licence posture, terms acknowledgement, notice mechanism → not an audit subject**; inadmissible under `problems-only` and expressly rejected. Do not file.

## 8. Edge Cases

- The user supplies a list, and one entry is a foreign origin that merely contains the expected pattern.
- A format record omits the codec key entirely rather than declaring it absent.
- The declared quality enumeration has no member for the label enumeration produces.
- An address arrives scheme-relative, and separately as a bare relative path that the normaliser is asked to promote to a host.
- A response body arrives with no declared length, on a branch other than the one that parses it.
- A manifest is refused once with an expiry status and the replacement address lives on a different host.
- A refusal arrives on a media part rather than on the manifest.
- A middle merge stage fails rather than the last one.
- A rate-limited response carries a server-supplied delay far larger than any local ceiling.
- A server-supplied delay is a date in the past, or one of the date forms the specification permits but the code does not parse.
- A connection-level failure occurs on the layer that otherwise waits between attempts.
- Two concurrent items hit the same origin, and the pause is keyed on something narrower than the origin.
- (Gap: whether a child process *enforces* the certificate and transport policies it is handed cannot be observed from this process — verify or document, and never report it as verified.)
- (Gap: the transport layer may have no test of any kind, in which case every subject in this phase is established by the scripted origin rather than by the suite — verify or document.)

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are not redefined here.

| Severity | Conditions |
|---|---|
| CRITICAL | Bytes are destroyed before the operation that needed them succeeds, with no recovery path inside the process; a transfer is abandoned on the exact condition the layer beneath it exists to survive, with no operator-visible diagnosis; a transport runs with verification disabled and nothing records it. |
| HIGH | A delivered address or a delivered quality differs from the one selected with no record of the change; a degraded path writes onto its predecessor's output; a declared policy reaches a strict subset of the transports; a composed timeout has a term that is dead at the configured floor; one configured value is reused as an unrelated stage's budget. |
| MEDIUM | A shared pause is consulted at a strict subset of the sites that could consult it; a wait is bounded by a local ceiling that a server-supplied value is applied outside of; an acceptance, classification or exclusion rule admits a value the origin or the enumeration will not accept; a pause is keyed narrower than the resource it protects. |
| LOW | A shape, naming or structure deviation with no runtime consequence, including a branch that can never be reached. |

**Type guidance.** `SPEC-DEVIATION` for behaviour that contradicts the project's own declared setting, bound or rule. `RUNTIME-ERROR` for anything observed failing at runtime. `BEST-PRACTICE` for a defensible design with a demonstrated risk. **This phase files no `DOC-UPDATE`** — a documented claim belongs to `09` by R-E, including a helper's own description of a precedence the implementation contradicts.

A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.

## 10. Recommended Sequence

1. Discovery (§4).
2. R10 first — the static baseline and the coverage declaration. Every later step is observed against it, and a zero-match subject is declared uncovered before it is checked, not after.
3. The scripted origin and the local stub binaries (§3), then R1 and R2. The harness is built once; every later step reuses it.
4. Blocks (a) through (h), in the order they are written in §6. **Do not reorder by convenience.** This is risk order, descending: a pass that is cut short must return the high-risk blocks, never the easy ones.
5. R3, R4, R5, R6, R7, R8, R9 as their blocks are reached, each producing the evidence named in that block's `- Evidence:` line.
6. Cross-cutting (§7) and edge cases (§8).
7. Consolidate findings, re-reading §7 before writing each one.

**Second-pass order (W-6).** If this phase is re-run after a thin result, do **not** start again from step 1. Re-enter at the first block below for which no evidence was recorded, and continue downward: `(a)` per-layer response policy and retry budget → `(b)` method ladder and artifact integrity → `(c)` intercepted address and payload bound → `(d)` address staleness and forced re-extraction → `(e)` policy reach and effective request rate → `(f)` per-surface parity and deadline composition → `(g)` enumeration, classification and selection → `(h)` acceptance of a user-supplied reference → R10's coverage declaration, refreshed last so it reflects what was actually run.

R1 and R2 are re-run **only** if (a) has no evidence at all, since the harness they build is reused by (b), (d) and (e). A block with partial evidence is resumed, not restarted; a block with complete evidence is skipped. A re-run that finds no new evidence writes `No problems found in this phase.` and stops.

## 11. Finding Prefix

Use `NET-` for all findings in this phase. `NET-` is unique in the catalogue, shares no first two characters with any other phase prefix, and is obtainable from no other prefix by a single plausible edit. It does not encode the phase number.

## 12. Reporting

- Write findings to: `.ai/audit/03-network-resilience/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row, or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) the **exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
