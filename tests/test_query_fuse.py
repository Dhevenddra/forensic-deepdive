"""RRF fusion + output shaping (DEC-038, PRD §4.5 test 2)."""

from __future__ import annotations

from forensic_deepdive.query.fuse import (
    RRF_K,
    fused_order,
    reciprocal_rank_fusion,
    shape,
    shape_factor,
)


def test_rrf_default_k_is_60() -> None:
    assert RRF_K == 60


def test_rrf_math_single_list() -> None:
    # 1-based ranks: a@1, b@2, c@3 -> 1/(60+r).
    scores = reciprocal_rank_fusion([["a", "b", "c"]])
    assert scores["a"] == 1.0 / 61
    assert scores["b"] == 1.0 / 62
    assert scores["c"] == 1.0 / 63


def test_rrf_fuses_across_lists() -> None:
    # b appears high in both lists -> should win.
    lists = [["a", "b", "c"], ["b", "c", "d"]]
    scores = reciprocal_rank_fusion(lists, k=60)
    assert scores["b"] == 1.0 / 61 + 1.0 / 62  # rank 2 then rank 1
    assert scores["a"] == 1.0 / 61  # only list 1, rank 1
    assert scores["d"] == 1.0 / 63  # only list 2, rank 3
    order = fused_order(scores)
    assert order[0] == "b"  # strongest combined evidence


def test_rrf_empty_lists_are_noop() -> None:
    assert reciprocal_rank_fusion([]) == {}
    assert reciprocal_rank_fusion([[], []]) == {}


def test_fused_order_is_deterministic_on_ties() -> None:
    # a and z each appear once at rank 1 in separate lists -> equal score,
    # broken by id ascending.
    scores = reciprocal_rank_fusion([["z"], ["a"]])
    assert scores["a"] == scores["z"]
    assert fused_order(scores) == ["a", "z"]


def test_shape_factor_boosts_impl_over_test() -> None:
    assert shape_factor("source", "function") > shape_factor("test", "function")
    assert shape_factor("source", "function") > shape_factor("vendored", "function")
    assert shape_factor("source", "function") > shape_factor("generated", "class")


def test_shaping_demotes_test_below_equal_rank_impl() -> None:
    # Two hits with identical base RRF score: one impl (source/function), one
    # test (test/function). After shaping the impl must rank first.
    base = 1.0 / 61
    hits = [
        {"symbol": "src/x.py::helper", "role": "test", "kind": "function", "score": base},
        {"symbol": "src/y.py::handle", "role": "source", "kind": "function", "score": base},
    ]
    shaped = shape(hits)
    assert shaped[0]["symbol"] == "src/y.py::handle"  # impl boosted above test
    assert shaped[1]["symbol"] == "src/x.py::helper"
    assert shaped[0]["shaped_score"] > shaped[1]["shaped_score"]


def test_shaping_is_deterministic_on_equal_shaped_score() -> None:
    base = 1.0 / 61
    hits = [
        {"symbol": "b::f", "role": "source", "kind": "function", "score": base},
        {"symbol": "a::f", "role": "source", "kind": "function", "score": base},
    ]
    shaped = shape(hits)
    assert [h["symbol"] for h in shaped] == ["a::f", "b::f"]  # tie broken by symbol
