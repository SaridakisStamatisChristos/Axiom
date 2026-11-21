"""Explicit graph orders and graph6 for corpus ingestion."""
from dataclasses import dataclass

MAX_ORDER = 256


@dataclass(frozen=True)
class ExplicitGraph:
    n: int
    edges: tuple[tuple[int, int], ...]

    def __post_init__(self):
        if type(self.n) is not int or not 0 <= self.n <= MAX_ORDER:
            raise ValueError(f"expected an explicit order between 0 and {MAX_ORDER}")
        if type(self.edges) is not tuple:
            raise ValueError("expected tuple of edges")
        previous = (-1, -1)
        for edge in self.edges:
            if (type(edge) is not tuple or len(edge) != 2
                    or any(type(vertex) is not int for vertex in edge)
                    or not 0 <= edge[0] < edge[1] < self.n or edge <= previous):
                raise ValueError("invalid, repeated or unordered edge")
            previous = edge

    @classmethod
    def from_dict(cls, data):
        if (type(data) is not dict or set(data) != {"n", "edges"} or type(data["edges"]) is not list
                or any(type(edge) is not list or len(edge) != 2
                       or any(type(v) is not int for v in edge) for edge in data["edges"])):
            raise ValueError("expected an explicit-order edge list")
        return cls(data["n"], tuple(sorted(tuple(sorted(edge)) for edge in data["edges"])))

    def to_dict(self):
        return {"n": self.n, "edges": [list(edge) for edge in self.edges]}

    def adjacency(self):
        rows = [0] * self.n
        for a, b in self.edges:
            rows[a] |= 1 << b
            rows[b] |= 1 << a
        return tuple(rows)

    @property
    def degrees(self):
        return tuple(row.bit_count() for row in self.adjacency())

    @classmethod
    def from_graph6(cls, line):
        order, packed = parse_graph6(line)
        edges = []
        bit = 0
        for b in range(order):
            for a in range(b):
                if packed[bit // 6] & (1 << (5 - bit % 6)):
                    edges.append((a, b))
                bit += 1
        return cls(order, tuple(sorted(edges)))

    def graph6(self):
        output = [self.n] if self.n < 63 else [63, self.n >> 12, self.n >> 6 & 63, self.n & 63]
        offset = len(output)
        output.extend([0] * ((self.n * (self.n - 1) // 2 + 5) // 6))
        for a, b in self.edges:
            bit = b * (b - 1) // 2 + a
            output[offset + bit // 6] |= 1 << (5 - bit % 6)
        return "".join(chr(value + 63) for value in output)


def parse_graph6(line):
    """Validate graph6, including unused padding bits."""
    if type(line) is not str:
        raise ValueError("graph6 must be text")
    line = line.rstrip("\r\n").removeprefix(">>graph6<<")
    if not line or any(not 63 <= ord(char) <= 126 for char in line):
        raise ValueError("invalid graph6 character")
    data = [ord(char) - 63 for char in line]
    order, offset = data[0], 1
    if order == 63:
        if len(data) < 4 or data[1] == 63:
            raise ValueError("unsupported extended graph6 order")
        order = (data[1] << 12) + (data[2] << 6) + data[3]
        offset = 4
        if order < 63:
            raise ValueError("noncanonical extended graph6 header")
    if order > MAX_ORDER:
        raise ValueError("graph6 order exceeds the ingestion limit")
    bits = order * (order - 1) // 2
    if len(data) != offset + (bits + 5) // 6 or (bits % 6 and data[-1] & ((1 << (6 - bits % 6)) - 1)):
        raise ValueError("invalid graph6 length or padding")
    return order, data[offset:]
