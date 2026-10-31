"""cognitive-ecology — a persistent cognitive ecology.

The thesis (see docs/MANIFESTO.md): intelligence is not answers, language, or
memory — it is the accumulation of effective organization through time. This
package is the first executable sketch of that idea:

- Law 1  Time is the substrate      -> ecology.runtime (long-lived processes, ticks)
- Law 2  Attention is scarce        -> ecology.attention (an economy, not a hierarchy)
- Law 3  Why precedes memory        -> ecology.why (live justification as conservation law)
- Law 4  LLMs are teachers          -> ecology.llm (they edit the organism, never are it)

The WHY kernel is a faithful Python port of why-core v0.2 from the
SuperInstance/why repository (Rust): same two-file format, same four statuses,
same golden corpus. The Rust tool remains the reference implementation; this
port exists so the ecology's runtime can query justification as a pure
in-process function — WHY as the scheduler's conservation law.
"""

__version__ = "0.1.0"
