"""Server-side playable board generation for Possession."""

from collections import Counter
from itertools import combinations
import random
import time


CLUB_REGIONS = {
    "Arsenal": "england", "Liverpool": "england",
    "Manchester United": "england", "Manchester City": "england",
    "Tottenham Hotspur": "england", "Newcastle United": "england",
    "Chelsea": "england", "Sevilla": "spain",
    "Atletico Madrid": "spain", "Barcelona": "spain",
    "Real Madrid": "spain", "AC Milan": "italy",
    "Inter Milan": "italy", "AS Roma": "italy", "Napoli": "italy",
    "Juventus": "italy", "Paris Saint-Germain": "france",
    "AS Monaco": "france", "Bayern Munich": "germany",
    "Borussia Dortmund": "germany", "Benfica": "portugal",
    "Sporting CP": "portugal", "Ajax": "netherlands",
    "Galatasaray": "turkey", "Fenerbahçe": "turkey",
    "Beşiktaş": "turkey", "Trabzonspor": "turkey",
}

TURKISH_CLUBS = {
    "Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor"
}
TRABZONSPOR_RANDOM_WEIGHT = 0.5

# Connection-quality calibration. Keep these explicit so board quality can be
# tuned without changing the construction algorithm.
PLAYABLE_EDGE_MIN_RECOGNIZABLE = 2
STRONG_EDGE_MIN_RECOGNIZABLE = 5
MIN_PLAYABLE_EDGE_RATIO = 0.60
MIN_QUALITY_TRIPLE_REGIONS = 6
MAX_WEAK_CELLS = 8
ASIA_KEY = ("continent", "Asia")

CLUB_CLASSES = {
    "A": (
        "Arsenal", "Liverpool", "Manchester United", "Manchester City",
        "Chelsea", "Barcelona", "Real Madrid", "AC Milan", "Inter Milan",
        "Juventus", "Bayern Munich",
    ),
    "B": (
        "Tottenham Hotspur", "Sevilla", "Atletico Madrid", "AS Roma",
        "Napoli", "Paris Saint-Germain", "Borussia Dortmund", "Benfica",
        "Ajax", "Galatasaray", "Fenerbahçe",
    ),
    "C": (
        "Newcastle United", "AS Monaco", "Sporting CP", "Beşiktaş",
        "Trabzonspor",
    ),
}

CLUB_CLASS_SLOTS = {
    14: {"A": 8, "B": 5, "C": 1},
    15: {"A": 9, "B": 5, "C": 1},
    16: {"A": 9, "B": 5, "C": 2},
}


class CriterionEngine:
    """Build balanced 31-cell boards from an approved criterion pool."""

    def __init__(
        self, players, criteria, neighbors, matcher,
        player_key_resolver=None
    ):
        self.players = players
        self.criteria = list(criteria)
        self.neighbors = neighbors
        self.matcher = matcher
        self.player_key_resolver = player_key_resolver
        self.keys = [self._key(item) for item in self.criteria]
        self.by_key = dict(zip(self.keys, self.criteria))
        self.player_keys = []
        self.answer_sets = {key: set() for key in self.keys}
        self.recognizable_answer_sets = {}
        self._pair_stats_cache = {}
        self.tiers = {}
        self.type_partitions = self._build_type_partitions()
        self._build_indexes()

    @staticmethod
    def _key(condition):
        return (condition["type"], condition["value"])

    def _build_indexes(self):
        raw_matches = []
        for player_index, player in enumerate(self.players):
            if self.player_key_resolver:
                matched = set(self.player_key_resolver(player))
            else:
                matched = {
                    key for key, condition in self.by_key.items()
                    if self.matcher(player, condition)
                }
            raw_matches.append(matched)
            for key in matched:
                self.answer_sets[key].add(player_index)

        for player_index, matched in enumerate(raw_matches):
            legacy_matches = {
                key for key in matched
                if key[0] in {"club", "nationality", "trophy"}
            }
            club_count = sum(key[0] == "club" for key in legacy_matches)
            trophy_count = sum(key[0] == "trophy" for key in legacy_matches)
            has_nationality = any(key[0] == "nationality" for key in matched)
            breadth = len(legacy_matches)
            if breadth >= 5 or (club_count >= 2 and trophy_count >= 1):
                tier = "popular"
            elif breadth >= 2 or (club_count >= 1 and has_nationality):
                tier = "medium"
            else:
                tier = "obscure"
            self.tiers[player_index] = tier
            self.player_keys.append(matched)

        self.criterion_stats = {}
        for key, answers in self.answer_sets.items():
            counts = Counter(self.tiers[index] for index in answers)
            self.criterion_stats[key] = {
                "total": len(answers),
                "popular": counts["popular"],
                "medium": counts["medium"],
                "obscure": counts["obscure"],
            }
            self.recognizable_answer_sets[key] = {
                index for index in answers
                if self.tiers[index] in {"popular", "medium"}
            }

    def _pair_stats(self, first, second):
        cache_key = tuple(sorted((first, second)))
        cached = self._pair_stats_cache.get(cache_key)
        if cached is not None:
            return cached
        common = self.answer_sets[first] & self.answer_sets[second]
        tiers = Counter(self.tiers[index] for index in common)
        result = len(common), tiers["popular"], tiers["medium"], common
        self._pair_stats_cache[cache_key] = result
        return result

    def _is_playable_pair(self, first, second):
        return len(
            self.recognizable_answer_sets[first]
            & self.recognizable_answer_sets[second]
        ) >= PLAYABLE_EDGE_MIN_RECOGNIZABLE

    def _pair_value(self, first, second):
        total, popular, medium, _ = self._pair_stats(first, second)
        if total == 0:
            return -2.5
        recognizable = popular + medium
        if recognizable == 0:
            return -1.5
        if recognizable <= 5:
            return 3.0
        if recognizable <= 20:
            return 2.3
        if recognizable <= 60:
            return 1.2
        return 0.3

    def _type_targets(self, rng):
        valid = [
            (nationalities, trophies, 25 - nationalities - trophies)
            for nationalities in range(3, 6)
            for trophies in range(6, 9)
            if 14 <= 25 - nationalities - trophies <= 16
        ]
        nationalities, trophies, clubs = rng.choice(valid)
        return {
            "club": clubs,
            "nationality": nationalities,
            "trophy": trophies,
            "league": 2,
            "position": 2,
            "birth_decade": 1,
            "continent": 1,
        }

    def _type_template_valid(self, assigned, position, criterion_type):
        trial = dict(assigned)
        trial[position] = criterion_type

        non_adjacent_types = {"nationality", "position", "league"}
        if criterion_type in non_adjacent_types and any(
            trial.get(neighbor) == criterion_type
            for neighbor in self.neighbors[position]
        ):
            return False

        trophy_cells = {
            index for index, value in trial.items()
            if value == "trophy"
        }
        unseen = set(trophy_cells)
        while unseen:
            component = {unseen.pop()}
            frontier = list(component)
            while frontier:
                current = frontier.pop()
                connected = unseen & set(self.neighbors[current])
                unseen -= connected
                component |= connected
                frontier.extend(connected)
            if len(component) >= 3:
                return False

        for trophy_cell in trophy_cells:
            trophy_neighbors = sum(
                trial.get(neighbor) == "trophy"
                for neighbor in self.neighbors[trophy_cell]
            )
            if trophy_neighbors > len(self.neighbors[trophy_cell]) // 2:
                return False

        return True

    def _build_type_partitions(self):
        order = sorted(
            self.neighbors,
            key=lambda index: len(self.neighbors[index]),
            reverse=True
        )
        colors = {}

        def color_position(order_index):
            if order_index == len(order):
                return True
            position = order[order_index]
            unavailable = {
                colors[neighbor]
                for neighbor in self.neighbors[position]
                if neighbor in colors
            }
            for color in range(3):
                if color in unavailable:
                    continue
                colors[position] = color
                if color_position(order_index + 1):
                    return True
                del colors[position]
            return False

        if not color_position(0):
            raise ValueError("Possession grid must be three-colorable")
        return tuple(
            tuple(index for index, value in colors.items() if value == color)
            for color in range(3)
        )

    def _generate_type_template(self, rng, targets, previous_types=None):
        nationality_count = targets["nationality"]

        for _ in range(240):
            eligible_partitions = [
                partition for partition in self.type_partitions
                if len(partition) >= nationality_count
            ]
            nationality_cells = set(rng.sample(
                rng.choice(eligible_partitions),
                nationality_count
            ))
            template = ["club"] * 31
            for index in nationality_cells:
                template[index] = "nationality"
            remaining_cells = [
                index for index in range(31)
                if index not in nationality_cells
            ]
            extra_types = (
                ["trophy"] * targets["trophy"]
                + ["league"] * 2
                + ["position"] * 2
                + ["birth_decade"]
                + ["continent"]
            )
            rng.shuffle(remaining_cells)
            rng.shuffle(extra_types)
            for index, criterion_type in zip(remaining_cells, extra_types):
                template[index] = criterion_type
            template = tuple(template)
            if template == previous_types:
                continue
            assigned = {}
            template_valid = True
            for index, criterion_type in enumerate(template):
                if not self._type_template_valid(
                    assigned,
                    index,
                    criterion_type
                ):
                    template_valid = False
                    break
                assigned[index] = criterion_type
            if not template_valid:
                continue
            return template
        return None

    def _creates_five_move(self, placed, position, candidate):
        trial = dict(placed)
        trial[position] = candidate
        affected = {position, *self.neighbors[position]}
        for center in affected:
            if center not in trial:
                continue
            neighborhood = [center] + [
                item for item in self.neighbors[center] if item in trial
            ]
            if len(neighborhood) < 5:
                continue
            for group in combinations(neighborhood, 5):
                common_players = set.intersection(
                    *(self.answer_sets[trial[item]] for item in group)
                )
                if common_players:
                    return True
        return False

    def _weighted_club_sample(self, rng, club_class, amount, turkish_count):
        available = [
            ("club", value) for value in CLUB_CLASSES[club_class]
            if ("club", value) in self.by_key
        ]
        selected = []
        for _ in range(amount):
            candidates = [
                key for key in available
                if turkish_count < 2 or key[1] not in TURKISH_CLUBS
            ]
            if not candidates:
                return None, turkish_count
            weights = [
                TRABZONSPOR_RANDOM_WEIGHT if key[1] == "Trabzonspor" else 1.0
                for key in candidates
            ]
            key = rng.choices(candidates, weights=weights, k=1)[0]
            selected.append(key)
            available.remove(key)
            turkish_count += key[1] in TURKISH_CLUBS
        return selected, turkish_count

    def _random_keys(self, rng, criterion_type, amount):
        pool = [key for key in self.keys if key[0] == criterion_type]
        if len(pool) < amount:
            return None
        return rng.sample(pool, amount)

    def _build_candidate(
        self,
        rng,
        previous_keys=None,
        previous_types=None,
        fixed_keys=None,
    ):
        previous_keys = previous_keys or set()
        fixed_keys = fixed_keys or {}
        targets = self._type_targets(rng)
        type_template = self._generate_type_template(
            rng,
            targets,
            previous_types
        )
        if not type_template:
            return None
        selected_by_type = {}
        turkish_count = 0
        selected_clubs = []
        for club_class, amount in CLUB_CLASS_SLOTS[targets["club"]].items():
            class_selection, turkish_count = self._weighted_club_sample(
                rng, club_class, amount, turkish_count
            )
            if class_selection is None:
                return None
            selected_clubs.extend(class_selection)
        selected_by_type["club"] = selected_clubs

        for criterion_type in ("nationality", "trophy"):
            selected_by_type[criterion_type] = self._random_keys(
                rng, criterion_type, targets[criterion_type]
            )
        for criterion_type in (
            "position", "league", "birth_decade", "continent"
        ):
            selected_by_type[criterion_type] = list(fixed_keys[criterion_type])

        if any(values is None for values in selected_by_type.values()):
            return None
        for values in selected_by_type.values():
            rng.shuffle(values)
        placed = {}
        for position, criterion_type in enumerate(type_template):
            candidates = list(selected_by_type[criterion_type])
            rng.shuffle(candidates)
            valid = [
                key for key in candidates
                if not self._creates_five_move(placed, position, key)
            ]
            if not valid:
                return None
            placed_neighbors = [
                placed[neighbor]
                for neighbor in self.neighbors[position]
                if neighbor in placed
            ]
            connected = [
                key for key in valid
                if any(
                    self._is_playable_pair(key, neighbor_key)
                    for neighbor_key in placed_neighbors
                )
            ]
            # Asia has a narrower answer pool. When filling one of its direct
            # neighbors, prefer (but never require) a strong indexed pair.
            asia_is_placed_neighbor = ASIA_KEY in placed_neighbors
            strong_to_asia = [
                key for key in valid
                if asia_is_placed_neighbor
                and len(
                    self.recognizable_answer_sets[key]
                    & self.recognizable_answer_sets[ASIA_KEY]
                ) >= STRONG_EDGE_MIN_RECOGNIZABLE
            ]
            key = rng.choice(strong_to_asia or connected or valid)
            placed[position] = key
            selected_by_type[criterion_type].remove(key)
        return [self.by_key[placed[index]] for index in range(31)]

    def analyze_board(self, board):
        keys = [self._key(item) for item in board]
        edges = {
            tuple(sorted((index, neighbor)))
            for index, adjacent in self.neighbors.items()
            for neighbor in adjacent
        }
        dead = obscure_only = playable = strong = weak = 0
        playable_neighbors = Counter()
        for first, second in edges:
            total, popular, medium, _ = self._pair_stats(keys[first], keys[second])
            recognizable = popular + medium
            dead += total == 0
            obscure_only += total > 0 and recognizable == 0
            is_playable = recognizable >= PLAYABLE_EDGE_MIN_RECOGNIZABLE
            playable += is_playable
            strong += recognizable >= STRONG_EDGE_MIN_RECOGNIZABLE
            weak += not is_playable
            if is_playable:
                playable_neighbors[first] += 1
                playable_neighbors[second] += 1

        opportunities = Counter()
        dominant = Counter()
        isolated = 0
        quality_triples = set()
        for center in range(31):
            adjacent = self.neighbors[center]
            if playable_neighbors[center] == 0:
                isolated += 1
            for first, second in combinations(adjacent, 2):
                common = set.intersection(
                    self.recognizable_answer_sets[keys[center]],
                    self.recognizable_answer_sets[keys[first]],
                    self.recognizable_answer_sets[keys[second]],
                )
                if common:
                    quality_triples.add(frozenset((center, first, second)))
            for player_index in self.answer_sets[keys[center]]:
                size = 1 + sum(
                    player_index in self.answer_sets[keys[item]] for item in adjacent
                )
                opportunities[min(size, 5)] += 1
                if size >= 2:
                    dominant[player_index] += 1

        type_counts = Counter(key[0] for key in keys)
        recognizable_ratios = []
        for key in keys:
            stats = self.criterion_stats[key]
            recognizable_ratios.append(
                (stats["popular"] + stats["medium"]) / max(1, stats["total"])
            )
        dead_ratio = dead / max(1, len(edges))
        playable_ratio = playable / max(1, len(edges))
        strong_ratio = strong / max(1, len(edges))
        weak_ratio = weak / max(1, len(edges))
        weak_cells = sum(
            playable_neighbors[index] < (1 if len(self.neighbors[index]) <= 2 else 2)
            for index in range(31)
        )
        asia_local = None
        if ASIA_KEY in keys:
            asia_index = keys.index(ASIA_KEY)
            asia_edges = []
            for neighbor in self.neighbors[asia_index]:
                total, popular, medium, _ = self._pair_stats(
                    ASIA_KEY, keys[neighbor]
                )
                recognizable = popular + medium
                asia_edges.append({
                    "playable": recognizable >= PLAYABLE_EDGE_MIN_RECOGNIZABLE,
                    "strong": recognizable >= STRONG_EDGE_MIN_RECOGNIZABLE,
                    "dead": total == 0,
                })
            asia_local = {
                "neighbor_count": len(asia_edges),
                "playable_neighbors": sum(
                    edge["playable"] for edge in asia_edges
                ),
                "strong_neighbors": sum(edge["strong"] for edge in asia_edges),
                "dead_neighbors": sum(edge["dead"] for edge in asia_edges),
            }
        score = 94.0
        score -= max(0, dead_ratio - 0.12) * 140
        score -= isolated * 8
        score -= obscure_only * 1.5
        score -= max(0, opportunities[4] - 14) * 0.35
        score -= opportunities[5] * 25
        score -= max(0, max(dominant.values(), default=0) - 7) * 2.0
        score -= abs(type_counts["club"] - 15.5) * 1.2
        score -= abs(type_counts["nationality"] - 4) * 1.0
        score -= abs(type_counts["trophy"] - 7) * 1.0
        score -= max(0, 0.28 - sum(recognizable_ratios) / 31) * 50
        return {
            "score": round(max(0, min(100, score)), 2),
            "dead_edges": dead,
            "obscure_only_edges": obscure_only,
            "isolated_cells": isolated,
            "edge_count": len(edges),
            "playable_edges": playable,
            "strong_edges": strong,
            "weak_edges": weak,
            "playable_edge_ratio": round(playable_ratio, 4),
            "strong_edge_ratio": round(strong_ratio, 4),
            "weak_edge_ratio": round(weak_ratio, 4),
            "playable_neighbor_cells": {
                "0": sum(playable_neighbors[index] == 0 for index in range(31)),
                "1": sum(playable_neighbors[index] == 1 for index in range(31)),
                "2_plus": sum(playable_neighbors[index] >= 2 for index in range(31)),
            },
            "weak_cells": weak_cells,
            "quality_triple_regions": len(quality_triples),
            "asia_local": asia_local,
            "opportunities": {str(size): opportunities[size] for size in range(1, 6)},
            "type_counts": dict(type_counts),
            "has_five_plus": opportunities[5] > 0,
            "max_player_combos": max(dominant.values(), default=0),
            "dominant_players": dominant.most_common(5),
            "unique": len(set(keys)) == 31,
        }

    def generate_board(self, previous=None, attempts=1200, seed=None):
        rng = random.Random(seed)
        previous_keys = {self._key(item) for item in (previous or [])}
        previous_types = tuple(
            item["type"] for item in (previous or [])
        ) or None
        previous_leagues = {
            key for key in previous_keys if key[0] == "league"
        }
        leagues = self._random_keys(rng, "league", 2)
        for _ in range(3):
            if set(leagues) != previous_leagues:
                break
            leagues = self._random_keys(rng, "league", 2)
        fixed_keys = {
            "league": leagues,
            "position": self._random_keys(rng, "position", 2),
            "birth_decade": self._random_keys(rng, "birth_decade", 1),
            "continent": self._random_keys(rng, "continent", 1),
        }
        started = time.perf_counter()
        for attempt in range(1, attempts + 1):
            board = self._build_candidate(
                rng,
                previous_keys,
                previous_types,
                fixed_keys,
            )
            if not board:
                continue
            analysis = self.analyze_board(board)
            board_keys = {self._key(item) for item in board}
            acceptable = (
                analysis["unique"]
                and not analysis["has_five_plus"]
                and analysis["isolated_cells"] == 0
                and analysis["playable_edge_ratio"] >= MIN_PLAYABLE_EDGE_RATIO
                and analysis["quality_triple_regions"] >= MIN_QUALITY_TRIPLE_REGIONS
                and analysis["weak_cells"] <= MAX_WEAK_CELLS
                and (
                    analysis["asia_local"] is None
                    or analysis["asia_local"]["playable_neighbors"] >= (
                        1
                        if analysis["asia_local"]["neighbor_count"] <= 2
                        else 2
                    )
                )
                and all(
                    self.criterion_stats[key]["total"] > 0
                    for key in board_keys
                )
                and board_keys != previous_keys
            )
            if acceptable:
                analysis["previous_overlap"] = len(previous_keys & board_keys)
                analysis["generation_ms"] = round(
                    (time.perf_counter() - started) * 1000, 2
                )
                analysis["attempts"] = attempt
                return board, analysis
        raise RuntimeError("No playable Possession board could be generated")
