# Checking matches with Maranget's usefulness algorithm, in the
# witness-producing form from "Warnings for pattern matching" (2007).
#
# A vector of patterns q is useful against a matrix P (one row per earlier
# branch) if some value matches q but no row of P. Then
#   - a match is exhaustive iff the all-wildcard row isn't useful against
#     its branches, and the witness is an example of a missing value;
#   - branch i is useless iff it isn't useful against branches 0..i-1.
from dataclasses import dataclass
from parser import Type, IntType, TCon, Pattern, PVar, PWild, PInt, PCon
from context import TypeTable, substitute

Row = list[Pattern]


@dataclass(frozen=True)
class _Ctor:
    """A head constructor: a declared constructor, or an integer literal."""

    name: str | int
    arity: int


def _head(p: Pattern) -> _Ctor | None:
    match p:
        case PCon(name, args):
            return _Ctor(name, len(args))
        case PInt(n):
            return _Ctor(n, 0)
    return None  # a variable or wildcard


def _args(p: Pattern) -> list[Pattern]:
    return list(p.args) if isinstance(p, PCon) else []


def _rebuild(c: _Ctor, args: list[Pattern]) -> Pattern:
    return PInt(c.name) if isinstance(c.name, int) else PCon(c.name, tuple(args))


class _Checker:
    def __init__(self, table: TypeTable):
        self.table = table

    def _type_name(self, t: Type | None, column: list[Pattern]) -> str | None:
        """The declared type of a column, from its type if known, otherwise
        from any constructor pattern in it."""
        if isinstance(t, TCon):
            return t.name
        for p in column:
            if isinstance(p, PCon) and p.name in self.table.ctors:
                return self.table.ctors[p.name].type_name
        return None

    def _signature(self, t: Type | None, column: list[Pattern]) -> list[_Ctor] | None:
        """Every constructor of the column's type, or None when the set is
        infinite (integers) or unknown."""
        name = self._type_name(t, column)
        if name is None or name not in self.table.types:
            return None
        return [
            _Ctor(c, len(self.table.ctors[c].fields))
            for c in self.table.types[name].constructors
        ]

    def _field_types(self, t: Type | None, c: _Ctor) -> list[Type | None]:
        """The types of c's fields, given the column's type T args."""
        if isinstance(c.name, int):
            return []
        info = self.table.ctors[c.name]
        if not isinstance(t, TCon) or t.name != info.type_name:
            return [None] * c.arity
        params = self.table.types[info.type_name].params
        fields = list(info.fields)
        for param, arg in zip(params, t.args):
            fields = [substitute(f, param, arg) for f in fields]
        return fields

    @staticmethod
    def _specialize(c: _Ctor, rows: list[Row]) -> list[Row]:
        """S(c, P): rows that could match c, with c's fields exposed."""
        out = []
        for row in rows:
            head = _head(row[0])
            if head is None:
                out.append([PWild()] * c.arity + row[1:])
            elif head == c:
                out.append(_args(row[0]) + row[1:])
        return out

    @staticmethod
    def _default(rows: list[Row]) -> list[Row]:
        """D(P): rows whose first pattern matches anything."""
        return [row[1:] for row in rows if _head(row[0]) is None]

    def useful(self, rows: list[Row], q: Row, types: list[Type | None]) -> Row | None:
        """A witness row of values matching q but no row in `rows`, or None
        if there isn't one."""
        if not q:
            return None if rows else []
        t, rest_types = types[0], types[1:]
        head = _head(q[0])
        if head is not None:
            fields = self._field_types(t, head)
            w = self.useful(
                self._specialize(head, rows),
                _args(q[0]) + q[1:],
                fields + rest_types,
            )
            return None if w is None else [_rebuild(head, w[: head.arity])] + w[head.arity :]

        column = [row[0] for row in rows]
        seen = []
        for p in column:
            c = _head(p)
            if c is not None and c not in seen:
                seen.append(c)
        signature = self._signature(t, column)
        if signature is not None and seen and all(c in seen for c in signature):
            # Every constructor appears, so a missing value has to be
            # missing under one of them.
            for c in signature:
                w = self.useful(
                    self._specialize(c, rows),
                    [PWild()] * c.arity + q[1:],
                    self._field_types(t, c) + rest_types,
                )
                if w is not None:
                    return [_rebuild(c, w[: c.arity])] + w[c.arity :]
            return None
        # Some constructor is missing (integers always have one), so the
        # rows with a wildcard first decide it.
        w = self.useful(self._default(rows), q[1:], rest_types)
        if w is None:
            return None
        return [self._missing_example(t, seen, signature)] + w

    @staticmethod
    def _missing_example(t, seen: list[_Ctor], signature: list[_Ctor] | None) -> Pattern:
        if not seen:
            return PWild()
        if signature is None:
            if all(isinstance(c.name, int) for c in seen):
                # The smallest non-negative integer no branch mentions.
                n = 0
                while _Ctor(n, 0) in seen:
                    n += 1
                return PInt(n)
            return PWild()
        missing = next(c for c in signature if c not in seen)
        return _rebuild(missing, [PWild()] * missing.arity)


def useless_branches(
    table: TypeTable, t: Type | None, patterns: list[Pattern]
) -> list[int]:
    """Indices of branches that can never match: every value they'd match
    is already taken by an earlier branch."""
    checker = _Checker(table)
    rows = [[p] for p in patterns]
    return [i for i in range(len(rows)) if checker.useful(rows[:i], rows[i], [t]) is None]


def missing_case(table: TypeTable, t: Type | None, patterns: list[Pattern]) -> Pattern | None:
    """An example of a value of type t that no pattern matches, or None if
    the patterns are exhaustive."""
    w = _Checker(table).useful([[p] for p in patterns], [PWild()], [t])
    return None if w is None else w[0]
