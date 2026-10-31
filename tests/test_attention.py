"""L5 — attention economics and the executive."""
from cognitive_ecology import AttentionBid, AttentionMarket, EventBus, Executive
from cognitive_ecology.attention import FACTORS


def test_attention_is_the_product():
    b = AttentionBid(src="critter", label="forage",
                     urgency=1.0, justification=1.0, opportunity=1.0,
                     novelty=1.0, expected_value=0.5)
    assert abs(b.attention - 0.5) < 1e-9


def test_any_zero_factor_vetoes():
    """The multiplicative law: no urgency can buy past a dead WHY."""
    b = AttentionBid(src="critter", label="griefing",
                     urgency=1.0, justification=0.0, opportunity=1.0,
                     novelty=1.0, expected_value=1.0)
    assert b.attention == 0.0


def test_factors_clamp_garbage():
    b = AttentionBid(src="x", label="y", urgency=7.0, justification=-3.0,
                     opportunity="wat", novelty=0.5, expected_value=float("nan"))
    assert b.attention == 0.0  # garbage clamps to 0 -> veto
    assert set(b.factors()) == set(FACTORS)


def test_market_clears_top_k_and_counts_starvation():
    m = AttentionMarket()
    bids = [
        AttentionBid(src="a", label="low", urgency=0.2, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=0.5),
        AttentionBid(src="a", label="high", urgency=0.9, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=0.9),
        AttentionBid(src="b", label="mid", urgency=0.5, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=0.7),
    ]
    for b in bids:
        m.submit(b)
    result = m.clear(top_k=2)
    assert [w.label for w in result.winners] == ["high", "mid"]
    assert [s.label for s in result.starved] == ["low"]
    # deterministic tie-break: same attention -> by src then label
    m2 = AttentionMarket()
    twins = [
        AttentionBid(src="b", label="zzz", urgency=0.5, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=0.9),
        AttentionBid(src="a", label="aaa", urgency=0.5, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=0.9),
    ]
    for t in twins:
        m2.submit(t)
    r = m2.clear(top_k=1)
    assert r.winners[0].label == "aaa" and r.starved[0].label == "zzz"
    # the market empties after clearing
    assert m.pending() == 0


def test_vetoed_bids_never_clear_even_in_an_empty_market():
    """The veto law: attention 0 means NO budget spend, however idle the organism."""
    m = AttentionMarket()
    m.submit(AttentionBid(src="a", label="sated", urgency=0.0, justification=1.0,
                          opportunity=1.0, novelty=1.0, expected_value=1.0))
    result = m.clear(top_k=3)
    assert result.winners == []          # nothing cleared
    assert [b.label for b in result.starved] == ["sated"]  # and it starved


def test_executive_resolves_resource_conflicts():
    bus = EventBus()
    market = AttentionMarket()
    ex = Executive(market, bus=bus, max_actions=2)
    bids = [
        AttentionBid(src="a", label="speak-loud", urgency=0.9, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0, resource="mic"),
        AttentionBid(src="b", label="speak-soft", urgency=0.5, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0, resource="mic"),
        AttentionBid(src="c", label="wave", urgency=0.4, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0),
    ]
    decisions = ex.arbitrate(bids, top_k=3, ts=1)
    by_label = {d.bid.label: d for d in decisions}
    assert by_label["speak-loud"].status == "run"
    assert by_label["speak-soft"].status == "yield"  # lost the mic
    assert by_label["wave"].status == "run"
    # DECISION events were emitted and can become causes
    decision_events = [e for e in bus.log() if e.kind.name == "DECISION"]
    assert len(decision_events) == 3
    assert by_label["speak-loud"].event_seq > 0
    # the starved list is exposed for ecology bookkeeping
    assert ex.last_clear is not None and ex.last_clear.starved == []
