from app.algorithms.matching import Candidate, rank_matches


def test_unanimous_partial_and_missing():
    rows = [Candidate("partial", 1, 0), Candidate("all", 2, 0), Candidate("mixed", 1, 1)]
    ranked = rank_matches(rows, 2)
    assert [row.restaurant_id for row in ranked] == ["all", "partial", "mixed"]
    assert ranked[0].unanimous
    assert not ranked[1].unanimous
    assert ranked[1].approval_percent == 100
    assert ranked[1].participant_like_percent == 50


def test_ties_budget_distance_stable_id_and_diet():
    ranked = rank_matches([
        Candidate("b", 1, 1, 1, 0),
        Candidate("a", 1, 1, 1, 0),
        Candidate("closer", 1, 1, 0.5, 0),
        Candidate("costly", 1, 1, 0.1, 20),
        Candidate("none", 0, 2),
        Candidate("unsafe", 2, 0, eligible=False),
    ], 2)
    assert [row.restaurant_id for row in ranked] == ["closer", "a", "b", "costly"]


def test_no_positive_votes_or_any_participants():
    assert rank_matches([Candidate("none", 0, 1)], 2) == []
    assert rank_matches([], 0) == []


def test_group_support_beats_a_single_unopposed_ballot():
    ranked = rank_matches([Candidate("single", 1, 0), Candidate("majority", 3, 1)], 4)
    assert [row.restaurant_id for row in ranked] == ["majority", "single"]
