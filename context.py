# Types and the ordered typing context from Dunfield & Krishnaswami (2013).
#
# The context is immutable: every operation takes Γ and returns a new Δ,
# mirroring the paper's Γ ⊢ ... ⊣ Δ judgments. The algorithm never
# backtracks, so there's no need to undo anything.
from dataclasses import dataclass, field, replace
from itertools import count
from parser import Type, IntType, FunType, TVar, Forall, Exists, TCon


# ---------------------------------------------------------------------------
# Operations on types
# ---------------------------------------------------------------------------


def is_monotype(t: Type) -> bool:
    """Monotypes (τ) are types with no `forall` anywhere inside them."""
    match t:
        case IntType() | TVar(_) | Exists(_):
            return True
        case FunType(param, result):
            return is_monotype(param) and is_monotype(result)
        case TCon(_, args):
            return all(is_monotype(arg) for arg in args)
        case Forall(_, _):
            return False


def occurs(name: str, t: Type) -> bool:
    """Whether the existential α̂ named `name` appears free in `t`."""
    match t:
        case Exists(n):
            return n == name
        case IntType() | TVar(_):
            return False
        case FunType(param, result):
            return occurs(name, param) or occurs(name, result)
        case TCon(_, args):
            return any(occurs(name, arg) for arg in args)
        case Forall(_, body):
            return occurs(name, body)


def substitute(t: Type, name: str, replacement: Type) -> Type:
    """[replacement/name]t: replace the type variable `name` in `t`.

    Stops at a `forall` that rebinds `name`. Doesn't rename to avoid capture;
    the checker only ever substitutes existentials or fresh type variables.
    """
    match t:
        case TVar(n):
            return replacement if n == name else t
        case IntType() | Exists(_):
            return t
        case FunType(param, result):
            return FunType(
                substitute(param, name, replacement),
                substitute(result, name, replacement),
            )
        case TCon(con, args):
            return TCon(con, tuple(substitute(arg, name, replacement) for arg in args))
        case Forall(var, body):
            if var == name:
                return t
            return Forall(var, substitute(body, name, replacement))


def show_type(t: Type) -> str:
    """Print a type in surface syntax, with existentials written as `^a`."""
    match t:
        case IntType():
            return "Int"
        case TVar(n):
            return n
        case Exists(n):
            return f"^{n}"
        case FunType(param, result):
            # `->` is right-associative and `forall` extends as far right as
            # possible, so only the left side ever needs parentheses.
            lhs = show_type(param)
            if isinstance(param, (FunType, Forall)):
                lhs = f"({lhs})"
            return f"{lhs} -> {show_type(result)}"
        case TCon(name, args):
            # Arguments are atoms, so anything that isn't gets parentheses:
            # Option (List Int), List (Int -> Int).
            parts = [name]
            for arg in args:
                s = show_type(arg)
                if isinstance(arg, (FunType, Forall)) or (
                    isinstance(arg, TCon) and arg.args
                ):
                    s = f"({s})"
                parts.append(s)
            return " ".join(parts)
        case Forall(_, _):
            # Nested foralls print as one binder list: forall a b. ...
            names = []
            while isinstance(t, Forall):
                names.append(t.var)
                t = t.body
            return f"forall {' '.join(names)}. {show_type(t)}"


_fresh_counter = count()


def reset_fresh():
    """Restart fresh names from 0, so each program gets small, repeatable
    names in its error messages. Only safe between independent checks."""
    global _fresh_counter
    _fresh_counter = count()


def fresh(base: str = "a") -> str:
    """A name that has never been handed out before.

    The `'` can't appear in a source identifier, so fresh names never
    collide with user-written type variables. A base that is itself a fresh
    name is trimmed back to its root, so `a'3` gives `a'7`, not `a'3'7`.
    """
    return f"{base.split("'")[0]}'{next(_fresh_counter)}"


# ---------------------------------------------------------------------------
# Context entries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CVar:
    """x : A"""

    name: str
    type: Type


@dataclass(frozen=True)
class CTVar:
    """α"""

    name: str


@dataclass(frozen=True)
class CExists:
    """α̂ (unsolved)"""

    name: str


@dataclass(frozen=True)
class CSolved:
    """α̂ = τ"""

    name: str
    type: Type


@dataclass(frozen=True)
class CMarker:
    """▶α̂, marks where a scope of existentials begins"""

    name: str


Entry = CVar | CTVar | CExists | CSolved | CMarker


def show_entry(entry: Entry) -> str:
    match entry:
        case CVar(name, t):
            return f"{name} : {show_type(t)}"
        case CTVar(name):
            return name
        case CExists(name):
            return f"^{name}"
        case CSolved(name, t):
            return f"^{name} = {show_type(t)}"
        case CMarker(name):
            return f"|>^{name}"


# ---------------------------------------------------------------------------
# Declared types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeInfo:
    params: tuple[str, ...]
    constructors: tuple[str, ...]


@dataclass(frozen=True)
class CtorInfo:
    type_name: str
    fields: tuple[Type, ...]
    # ∀params. F1 → … → Fn → T params
    scheme: Type


@dataclass(frozen=True)
class TypeTable:
    """Declared types and their constructors. Built by types_table.py and
    never mutated: declaring a group returns a new table."""

    types: dict[str, TypeInfo] = field(default_factory=dict)
    ctors: dict[str, CtorInfo] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# The ordered context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Context:
    entries: tuple[Entry, ...] = ()
    # Declarations sit at the top level and never go out of scope, so they
    # live beside the ordered entries rather than in them. Every rule
    # threads Γ to Δ, which carries the table along with no extra plumbing.
    table: TypeTable = field(default_factory=TypeTable)
    # Every match checked so far, with its scrutinee's type, for the
    # exhaustiveness pass. Like the table it survives dropping scopes: the
    # type's existentials may only be solved later, so it's resolved
    # against the final context once the whole program is typed.
    matches: tuple[tuple[object, Type], ...] = ()

    def __str__(self) -> str:
        return ", ".join(show_entry(e) for e in self.entries)

    def _with(self, entries: tuple[Entry, ...]) -> "Context":
        return replace(self, entries=entries)

    def record_match(self, match: object, t: Type) -> "Context":
        return replace(self, matches=self.matches + ((match, t),))

    def extend(self, *entries: Entry) -> "Context":
        """Γ, entries"""
        return self._with(self.entries + entries)

    def _index(self, entry: Entry) -> int:
        """Position of the rightmost `entry`, the innermost scope if it's
        shadowed (e.g. the second `x : Int` in `/x -> /x -> x`)."""
        for i in range(len(self.entries) - 1, -1, -1):
            if self.entries[i] == entry:
                return i
        raise TypeError(f"{show_entry(entry)} is not in context [{self}]")

    def drop(self, entry: Entry) -> "Context":
        """Γ, entry, Θ  becomes  Γ. Used to leave a scope."""
        return self._with(self.entries[: self._index(entry)])

    def replace(self, entry: Entry, *new_entries: Entry) -> "Context":
        """Γ[entry]  becomes  Γ[new_entries], keeping everything else in place."""
        i = self._index(entry)
        return self._with(self.entries[:i] + new_entries + self.entries[i + 1 :])

    def lookup(self, name: str) -> Type | None:
        """The type of term variable `name`; the rightmost binding wins."""
        for entry in reversed(self.entries):
            if isinstance(entry, CVar) and entry.name == name:
                return entry.type
        return None

    def has_tvar(self, name: str) -> bool:
        return CTVar(name) in self.entries

    def has_exists(self, name: str) -> bool:
        """Whether α̂ is declared, solved or not."""
        return any(
            isinstance(e, (CExists, CSolved)) and e.name == name
            for e in self.entries
        )

    def solution(self, name: str) -> Type | None:
        """τ if α̂ = τ is in the context, None if α̂ is unsolved or absent."""
        for entry in self.entries:
            if isinstance(entry, CSolved) and entry.name == name:
                return entry.type
        return None

    def apply(self, t: Type) -> Type:
        """[Γ]A: replace every solved existential in `t` with its solution."""
        match t:
            case Exists(name):
                solved = self.solution(name)
                return t if solved is None else self.apply(solved)
            case IntType() | TVar(_):
                return t
            case FunType(param, result):
                return FunType(self.apply(param), self.apply(result))
            case TCon(name, args):
                return TCon(name, tuple(self.apply(arg) for arg in args))
            case Forall(var, body):
                return Forall(var, self.apply(body))

    def well_formed(self, t: Type) -> bool:
        """Γ ⊢ A: every variable in `t` is bound by the context or a forall,
        and every declared type is applied correctly."""
        return self.why_ill_formed(t) is None

    def why_ill_formed(self, t: Type) -> str | None:
        """None if Γ ⊢ A, otherwise what's wrong with A."""
        match t:
            case IntType():
                return None
            case TVar(name):
                return None if self.has_tvar(name) else f"type variable {name} is not in scope"
            case Exists(name):
                return None if self.has_exists(name) else f"^{name} is not in scope"
            case FunType(param, result):
                return self.why_ill_formed(param) or self.why_ill_formed(result)
            case TCon(name, args):
                info = self.table.types.get(name)
                if info is None:
                    return f"unknown type {name}"
                if len(args) != len(info.params):
                    return (
                        f"{name} expects {len(info.params)} argument(s)"
                        f" but got {len(args)} in {show_type(t)}"
                    )
                for arg in args:
                    # Arguments are monotypes, as instantiation is in the
                    # paper, so declared types never need variance.
                    if not is_monotype(arg):
                        return f"type arguments must be monotypes: {show_type(t)}"
                    if reason := self.why_ill_formed(arg):
                        return reason
                return None
            case Forall(var, body):
                return self.extend(CTVar(var)).why_ill_formed(body)

    def split(self, name: str, n: int, build) -> tuple["Context", list[Exists]]:
        """Γ[α̂]  becomes  Γ[α̂ₙ, …, α̂₁, α̂ = build(α̂₁, …, α̂ₙ)].

        The new existentials go just before α̂, so anything α̂ could be
        solved to can also mention them.
        """
        parts = [Exists(fresh(name)) for _ in range(n)]
        ctx = self.replace(
            CExists(name),
            *(CExists(p.name) for p in reversed(parts)),
            CSolved(name, build(*parts)),
        )
        return ctx, parts

    def split_arrow(self, name: str) -> tuple["Context", Exists, Exists]:
        """Γ[α̂]  becomes  Γ[α̂₂, α̂₁, α̂ = α̂₁ → α̂₂].

        Returns the new context with α̂₁ and α̂₂. Used by the instantiation
        rules when α̂ has to become a function type.
        """
        ctx, (a1, a2) = self.split(name, 2, FunType)
        return ctx, a1, a2

    def split_tcon(self, name: str, con: str, n: int) -> tuple["Context", list[Exists]]:
        """Γ[α̂]  becomes  Γ[α̂ₙ, …, α̂₁, α̂ = T α̂₁ … α̂ₙ], the declared-type
        counterpart of split_arrow."""
        return self.split(name, n, lambda *parts: TCon(con, tuple(parts)))
