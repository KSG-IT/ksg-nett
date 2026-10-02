from collections import deque
from typing import List, Sequence


def maximum_bipartite_matching(
    adjacency: Sequence[Sequence[int]], right_count: int
) -> List[int]:
    """
    Finds a maximum matching in a bipartite graph.

    adjacency[left] lists the right vertices that the left vertex can be
    matched with. Returns a list with one item per right vertex: the matched
    left vertex, or -1. This is the same output as
    scipy.sparse.csgraph.maximum_bipartite_matching(graph, perm_type="row").

    Uses augmenting paths (Kuhn's algorithm) with a breadth-first search, so
    there is no recursion limit. The run time is O(V * E), which is small for
    the number of users and shift slots in a schedule.
    """
    match_right = [-1] * right_count
    match_left = [-1] * len(adjacency)

    for start in range(len(adjacency)):
        # parent[right] is the left vertex the search came from
        parent = {}
        visited_left = {start}
        queue = deque([start])
        free_right = -1
        while queue and free_right == -1:
            left = queue.popleft()
            for right in adjacency[left]:
                if right in parent:
                    continue
                parent[right] = left
                if match_right[right] == -1:
                    free_right = right
                    break
                next_left = match_right[right]
                if next_left not in visited_left:
                    visited_left.add(next_left)
                    queue.append(next_left)

        # Flip the matched and unmatched edges along the path back to start
        right = free_right
        while right != -1:
            left = parent[right]
            previous_right = match_left[left]
            match_left[left] = right
            match_right[right] = left
            right = previous_right

    return match_right
