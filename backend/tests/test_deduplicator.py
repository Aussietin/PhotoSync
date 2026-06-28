"""BK-tree clustering correctness. Requires the app deps (sqlalchemy) installed."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("sqlalchemy")

from services.deduplicator import BKTree


def _int_metric(a, b):
    return abs(a[1] - b[1])


def test_bktree_finds_within_threshold():
    tree = BKTree(distance=_int_metric)
    for item in [(1, 0), (2, 5), (3, 10)]:
        tree.add(item)
    # Within radius 2 of value 1 → only (1,0)
    matches = tree.find((99, 1), 2)
    assert {m[0] for m in matches} == {1}


def test_bktree_clustering_simulation():
    """Mimics rescan: add as original only when nothing is near (radius 2)."""
    tree = BKTree(distance=_int_metric)
    originals, dups = [], []
    for item in [(1, 0), (2, 3), (3, 10), (4, 11), (5, 100)]:
        if tree.find(item, 2):
            dups.append(item[0])
        else:
            tree.add(item)
            originals.append(item[0])
    # 0 and 3 are >2 apart → both originals; 11 is within 2 of 10 → dup; 100 alone
    assert originals == [1, 2, 3, 5]
    assert dups == [4]


def test_bktree_empty():
    tree = BKTree(distance=_int_metric)
    assert tree.find((1, 5), 3) == []
