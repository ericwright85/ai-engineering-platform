# ADR 001: Separate suggestions from authority

Status: Accepted.

Repository text and provider responses are untrusted. Reviewers can submit only typed findings whose evidence is verified against bounded input. They cannot choose commands, approve themselves or mutate GitHub. State transitions use compare-and-set updates with an event journal. A trusted human must approve export and optional sandbox execution. Demo approval is explicitly simulated, never represented as a real approval service.

Use a provider protocol and deterministic mock to make the entire review reproducible without paid keys. Reviewer concurrency reduces independent analysis latency; persistence occurs on the coordinator thread. SQLite WAL keeps state inspectable. Idempotency is content-addressed per provider class and workflow version; changing a hosted model will require a configuration/version fingerprint.

Docker isolates the fixed test runner from the host but shares a kernel. Use dedicated ephemeral VM workers for adversarial inputs. Local approval is not a signed enterprise authorization and the sandbox source is selected by the trusted user, not cryptographically bound to the analyzed fixture. Production must close that gap before supporting remote job execution.
