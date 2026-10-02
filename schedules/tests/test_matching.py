import itertools
import random

from django.test import SimpleTestCase

from schedules.utils.matching import maximum_bipartite_matching


def brute_force_size(adjacency, right_count):
    """The size of the largest matching, by trying all assignments"""
    best = 0
    options = [list(rights) + [None] for rights in adjacency]
    for choice in itertools.product(*options):
        used = [right for right in choice if right is not None]
        if len(used) == len(set(used)):
            best = max(best, len(used))
    return best


class TestMaximumBipartiteMatching(SimpleTestCase):
    def assert_valid(self, adjacency, result):
        matched_left = [left for left in result if left != -1]
        self.assertEqual(len(matched_left), len(set(matched_left)))
        for right, left in enumerate(result):
            if left != -1:
                self.assertIn(right, adjacency[left])

    def test__no_left_vertices__matches_nothing(self):
        self.assertEqual(maximum_bipartite_matching([], 3), [-1, -1, -1])

    def test__no_edges__matches_nothing(self):
        self.assertEqual(maximum_bipartite_matching([[], []], 2), [-1, -1])

    def test__perfect_matching__needs_augmenting_path(self):
        # Left 0 takes right 0 first. Left 1 can only use right 0, so left 0
        # must move to right 1.
        adjacency = [[0, 1], [0]]
        self.assertEqual(maximum_bipartite_matching(adjacency, 2), [1, 0])

    def test__more_left_than_right__fills_every_right(self):
        adjacency = [[0], [0], [0, 1]]
        result = maximum_bipartite_matching(adjacency, 2)
        self.assert_valid(adjacency, result)
        self.assertNotIn(-1, result)

    def test__random_graphs__match_brute_force_size(self):
        rng = random.Random(42)
        for _ in range(300):
            left_count = rng.randint(1, 6)
            right_count = rng.randint(1, 6)
            adjacency = [
                [right for right in range(right_count) if rng.random() < 0.4]
                for _ in range(left_count)
            ]
            result = maximum_bipartite_matching(adjacency, right_count)
            self.assert_valid(adjacency, result)
            self.assertEqual(
                sum(left != -1 for left in result),
                brute_force_size(adjacency, right_count),
            )
