# Typing patterns:  Γ ⊢ p ⇐ A ⊣ Δ
#
# Δ extends Γ with the pattern's variables. The match rule puts a marker
# before each branch and drops back to it afterwards, which removes them.
from parser import Type, IntType, Forall, Exists, TCon, Pattern, PVar, PWild, PInt, PCon
from context import Context, CVar, CExists, substitute, show_type, fresh
from errors import TypeCheckError, rule_frame
from subtyping import subtype


def show_pattern(p: Pattern, atom: bool = False) -> str:
    """Print a pattern; `atom` parenthesizes a constructor with arguments."""
    match p:
        case PVar(name):
            return name
        case PWild():
            return "_"
        case PInt(n):
            return str(n)
        case PCon(name, ()):
            return name
        case PCon(name, args):
            s = " ".join([name] + [show_pattern(q, True) for q in args])
            return f"({s})" if atom else s


def pattern_vars(p: Pattern) -> list[str]:
    match p:
        case PVar(name):
            return [name]
        case PCon(_, args):
            return [n for q in args for n in pattern_vars(q)]
    return []


def instantiate(ctx: Context, t: Type) -> tuple[Context, Type]:
    """Open every outer forall with a fresh existential, as ∀App does."""
    while isinstance(t, Forall):
        a = fresh(t.var)
        ctx = ctx.extend(CExists(a))
        t = substitute(t.body, t.var, Exists(a))
    return ctx, t


def check_pattern(ctx: Context, p: Pattern, t: Type) -> Context:
    """Γ ⊢ p ⇐ A ⊣ Δ, with A already applied to Γ."""
    match p:
        case PVar(name):
            # A variable takes the whole type, even a polymorphic one: this
            # is what lets a field of type forall a. a -> a be used at two
            # types in the branch.
            return ctx.extend(CVar(name, t))
        case PWild():
            return ctx
        case PInt(_):
            ctx, t = instantiate(ctx, t)
            with rule_frame("PInt", f"matching {show_pattern(p)} against {show_type(t)}"):
                return subtype(ctx, t, IntType())
        case PCon(name, args):
            info = ctx.table.ctors.get(name)
            if info is None:
                raise TypeCheckError("PCon", f"unknown constructor {name}")
            if len(args) != len(info.fields):
                raise TypeCheckError(
                    "PCon",
                    f"{name} has {len(info.fields)} field(s) but the pattern"
                    f" {show_pattern(p)} gives {len(args)}",
                )
            ctx, t = instantiate(ctx, t)
            # Instantiate the constructor's scheme: its type parameters
            # become fresh existentials, giving fields F1..Fn and a result
            # T α̂1..α̂n. Relating the matched type to the result solves them,
            # and splits an unsolved matched α̂ into T β̂1..β̂n (InstLTCon).
            fields = info.fields
            params = ctx.table.types[info.type_name].params
            parts = []
            for param in params:
                a = fresh(param)
                ctx = ctx.extend(CExists(a))
                parts.append(Exists(a))
                fields = tuple(substitute(f, param, Exists(a)) for f in fields)
            result = TCon(info.type_name, tuple(parts))
            with rule_frame("PCon", f"matching {show_pattern(p)} against {show_type(t)}"):
                ctx = subtype(ctx, t, result)
                for q, f in zip(args, fields):
                    ctx = check_pattern(ctx, q, ctx.apply(f))
            return ctx
