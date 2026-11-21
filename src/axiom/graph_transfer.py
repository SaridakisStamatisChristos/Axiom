"""Typed, exact CPU evaluation of the graph literature-transfer fragment."""
from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property, lru_cache
from itertools import accumulate

from .graph_claims import digest, stable
from .graph_explicit import ExplicitGraph
from .graph_invariants import bipartite, components, matching_number

SCHEMA = "axiom.graph.transfer.v1"
RESULT = "axiom.graph.transfer_check.v1"
MAX_EXACT_ORDER = 12
INVARIANTS = {
    "minimum_degree": "minimum degree, zero on the empty graph",
    "maximum_degree": "maximum degree, zero on the empty graph",
    "independence": "maximum size of an independent vertex set",
    "annihilation": "largest prefix of nondecreasing degrees whose sum is <= the edge count",
    "residue": "zeros remaining after Havel–Hakimi removes all positive degrees",
    "edge_cover": "minimum edge cover; undefined on graphs with isolated vertices",
    "independent_domination": "minimum cardinality of a maximal independent vertex set",
    "minimum_maximal_matching": "minimum cardinality of an inclusion-maximal matching",
    "zero_forcing": "minimum initial blue set under the unique white neighbor rule",
    "harmonic_index": "sum over edges of 2/(degree(u)+degree(v)), exactly rational",
}
PREDICATES = {
    "connected", "nontrivial", "bipartite", "positive_regular", "no_isolates",
    "subcubic", "not_k4",
}


@dataclass(frozen=True)
class Expression:
    operator: str
    operands: tuple

    @classmethod
    def parse(cls, data, predicates, depth=0):
        if depth > 4 or type(data) is not dict:
            raise ValueError("invalid bounded graph expression")
        if set(data) == {"invariant"}:
            name = data["invariant"]
            if type(name) is not str or name not in INVARIANTS:
                raise ValueError("unknown invariant")
            if name == "edge_cover" and not {"no_isolates", "positive_regular"}.intersection(predicates):
                raise ValueError("edge cover requires a no-isolates premise")
            return cls("invariant", (name,))
        if set(data) == {"integer"}:
            value = data["integer"]
            if type(value) is not int or abs(value) > 256:
                raise ValueError("invalid integral literal")
            return cls("integer", (value,))
        if (set(data) != {"operator", "operands"} or type(data["operator"]) is not str
                or data["operator"] not in {"add", "multiply", "divide"}
                or type(data["operands"]) is not list or len(data["operands"]) != 2):
            raise ValueError("invalid expression operator or arity")
        left, right = (cls.parse(node, predicates, depth + 1) for node in data["operands"])
        if data["operator"] == "divide":
            constant = right.operator == "integer" and right.operands[0] > 0
            max_degree = right == cls("invariant", ("maximum_degree",)) and (
                "positive_regular" in predicates or {"connected", "nontrivial"} <= predicates)
            if not constant and not max_degree:
                raise ValueError("division requires a statically positive denominator")
        if data["operator"] in ("add", "multiply"):
            left, right = sorted((left, right), key=lambda expression: stable(expression.to_dict()))
        return cls(data["operator"], (left, right))

    def to_dict(self):
        if self.operator in ("invariant", "integer"):
            return {self.operator: self.operands[0]}
        return {"operator": self.operator, "operands": [item.to_dict() for item in self.operands]}

    def evaluate(self, invariants):
        if self.operator == "invariant":
            return Fraction(getattr(invariants, self.operands[0]))
        if self.operator == "integer":
            return Fraction(self.operands[0])
        x, y = (item.evaluate(invariants) for item in self.operands)
        if self.operator == "add":
            return x + y
        if self.operator == "multiply":
            return x * y
        return x / y

    def used(self):
        if self.operator == "invariant":
            return {self.operands[0]}
        if self.operator == "integer":
            return set()
        return set().union(*(item.used() for item in self.operands))


@dataclass(frozen=True)
class TransferStatement:
    predicates: tuple[str, ...]
    left: Expression
    right: Expression

    @classmethod
    def from_dict(cls, data):
        if (type(data) is not dict or set(data) != {"schema", "predicates", "left", "right"}
                or data["schema"] != SCHEMA or type(data["predicates"]) is not list
                or any(type(x) is not str or x not in PREDICATES for x in data["predicates"])):
            raise ValueError("invalid typed literature statement")
        predicates = set(data["predicates"])
        if len(predicates) != len(data["predicates"]):
            raise ValueError("duplicate graph predicate")
        return cls(tuple(sorted(predicates)), Expression.parse(data["left"], predicates),
                   Expression.parse(data["right"], predicates))

    def to_dict(self):
        return {"schema": SCHEMA, "predicates": list(self.predicates),
                "left": self.left.to_dict(), "right": self.right.to_dict()}


class InvariantValues:
    def __init__(self, graph):
        self.graph = graph
        self.adj = graph.adjacency()
        self.full = (1 << graph.n) - 1
        self.degrees = graph.degrees

    def _masks(self, size):
        from itertools import combinations
        return (sum(1 << v for v in group) for group in combinations(range(self.graph.n), size))

    def _vertices(self, mask):
        return (i for i in range(self.graph.n) if mask & (1 << i))

    def _independent(self, mask):
        return all(not (self.adj[v] & mask) for v in self._vertices(mask))

    @cached_property
    def minimum_degree(self):
        return min(self.degrees, default=0)

    @cached_property
    def maximum_degree(self):
        return max(self.degrees, default=0)

    @cached_property
    def independence(self):
        return next(size for size in range(self.graph.n, -1, -1)
                    if any(self._independent(mask) for mask in self._masks(size)))

    @cached_property
    def annihilation(self):
        return sum(total <= len(self.graph.edges) for total in accumulate(sorted(self.degrees)))

    @cached_property
    def residue(self):
        rows = sorted(self.degrees, reverse=True)
        while rows and rows[0]:
            degree = rows[0]
            rows = sorted((value - (i < degree) for i, value in enumerate(rows[1:])), reverse=True)
        return len(rows)

    @cached_property
    def edge_cover(self):
        if 0 in self.degrees:
            raise ValueError("edge cover is undefined on a graph with isolated vertices")
        # Gallai's edge-cover identity applies exactly on this domain.
        return self.graph.n - matching_number(self.graph)

    @cached_property
    def independent_domination(self):
        for size in range(self.graph.n + 1):
            for mask in self._masks(size):
                if not self._independent(mask):
                    continue
                cover = mask
                for v in self._vertices(mask):
                    cover |= self.adj[v]
                if cover == self.full:
                    return size
        raise ArithmeticError("maximal independent set missing")

    @cached_property
    def minimum_maximal_matching(self):
        @lru_cache(maxsize=None)
        def solve(available, unmatched):
            if not available:
                return 0
            bit = available & -available
            v = bit.bit_length() - 1
            rest = available ^ bit
            best = self.graph.n + 1
            # A matching is maximal iff its unmatched vertices are independent.
            if not self.adj[v] & unmatched:
                best = solve(rest, unmatched | bit)
            for other in self._vertices(self.adj[v] & rest):
                best = min(best, 1 + solve(rest ^ (1 << other), unmatched))
            return best

        return solve(self.full, 0)

    @cached_property
    def zero_forcing(self):
        def reaches_all(blue):
            while blue != self.full:
                updated = blue
                for v in self._vertices(blue):
                    white = self.adj[v] & ~blue
                    if white.bit_count() == 1:
                        updated |= white
                if updated == blue:
                    return False
                blue = updated
            return True

        return next(size for size in range(self.graph.n + 1)
                    if any(reaches_all(mask) for mask in self._masks(size)))

    @cached_property
    def harmonic_index(self):
        return sum((Fraction(2, self.degrees[a] + self.degrees[b]) for a, b in self.graph.edges), Fraction())

    def predicate(self, name):
        if name == "connected":
            return len(components(self.graph)) == 1
        if name == "bipartite":
            return bipartite(self.graph)
        if name == "subcubic":
            return self.maximum_degree <= 3
        if name == "positive_regular":
            return 0 < self.minimum_degree == self.maximum_degree
        if name == "no_isolates":
            return 0 not in self.degrees
        if name == "nontrivial":
            return self.graph.n >= 2
        if name == "not_k4":
            return (self.graph.n, len(self.graph.edges)) != (4, 6)
        raise ValueError("unsupported graph predicate")


def check(statement, graph):
    data = statement.to_dict()
    result = {"schema": RESULT, "statement_sha256": digest(data), "graph": graph.to_dict()}
    if graph.n > MAX_EXACT_ORDER:
        return {**result, "status": "UNSUPPORTED_ORDER", "exact_order_limit": MAX_EXACT_ORDER}
    values = InvariantValues(graph)
    predicates = {name: values.predicate(name) for name in statement.predicates}
    result["predicates"] = predicates
    if not all(predicates.values()):
        return {**result, "status": "OUTSIDE_PREMISE"}
    left, right = statement.left.evaluate(values), statement.right.evaluate(values)
    return {**result, "status": "HOLDS_ON_GRAPH" if left <= right else "COUNTEREXAMPLE",
            "left": str(left), "right": str(right), "kernel_status": "NOT_RUN",
            "invariants": {name: str(getattr(values, name))
                           for name in sorted(statement.left.used() | statement.right.used())}}


def replay(statement, evidence):
    graph = ExplicitGraph.from_dict(evidence.get("graph"))
    if stable(check(statement, graph)) != stable(evidence):
        raise ValueError("exact literature evidence does not replay")
    return True
