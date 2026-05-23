# Algorithmic subtyping (Dunfield & Krishnaswami 2013, Fig. 9).
#
#   subtype:  Γ ⊢ A <: B ⊣ Δ
#
# Expects A and B to already have Γ applied to them.
from parser import Type, IntType, FunType, TVar, Forall, Exists
from context import (
    Context,
    CTVar,
    CExists,
    CMarker,
    occurs,
    substitute,
    show_type,
    fresh,
)
from errors import TypeCheckError, rule_frame
from instantiation import inst_l, inst_r

# When no rule applies, blame the one the left-hand side would have needed.
_RULE_FOR_LHS = {TVar: "<:Var", IntType: "<:Int", FunType: "<:→", Exists: "<:Exvar"}


def _fail(a: Type, b: Type):
    raise TypeCheckError(
        _RULE_FOR_LHS[type(a)], f"{show_type(a)} is not a subtype of {show_type(b)}"
    )


def _check_occurs(name: str, t: Type, rule: str):
    if occurs(name, t):
        raise TypeCheckError(
            rule,
            f"occurs check: ^{name} appears in {show_type(t)}, so solving it"
            " would make an infinite type",
        )


def subtype(ctx: Context, a: Type, b: Type) -> Context:
    """Γ ⊢ A <: B ⊣ Δ"""
    judgment = f"checking {show_type(a)} <: {show_type(b)}"
    match a, b:
        case TVar(x), TVar(y) if x == y:
            # <:Var
            if not ctx.has_tvar(x):
                raise TypeCheckError("<:Var", f"type variable {x} is not in scope")
            return ctx
        case IntType(), IntType():
            # <:Int (the paper's <:Unit)
            return ctx
        case Exists(x), Exists(y) if x == y:
            # <:Exvar
            if not ctx.has_exists(x):
                raise TypeCheckError("<:Exvar", f"^{x} is not in context [{ctx}]")
            return ctx
        case FunType(a1, a2), FunType(b1, b2):
            # <:→: parameters are contravariant
            with rule_frame("<:→", judgment):
                theta = subtype(ctx, b1, a1)
                return subtype(theta, theta.apply(a2), theta.apply(b2))
        case _, Forall(var, body):
            # <:∀R, tried before ∀L so that ∀a. A <: ∀b. B keeps b rigid
            with rule_frame("<:∀R", judgment):
                beta = fresh(var) if ctx.has_tvar(var) else var
                ctx = ctx.extend(CTVar(beta))
                delta = subtype(ctx, a, substitute(body, var, TVar(beta)))
                return delta.drop(CTVar(beta))
        case Forall(var, body), _:
            # <:∀L: replace the bound variable with a fresh existential,
            # scoped by a marker
            with rule_frame("<:∀L", judgment):
                alpha = fresh(var)
                ctx = ctx.extend(CMarker(alpha), CExists(alpha))
                delta = subtype(ctx, substitute(body, var, Exists(alpha)), b)
                return delta.drop(CMarker(alpha))
        case Exists(x), _ if CExists(x) in ctx.entries:
            # <:InstantiateL
            _check_occurs(x, b, "<:InstantiateL")
            with rule_frame("<:InstantiateL", judgment):
                return inst_l(ctx, x, b)
        case _, Exists(x) if CExists(x) in ctx.entries:
            # <:InstantiateR
            _check_occurs(x, a, "<:InstantiateR")
            with rule_frame("<:InstantiateR", judgment):
                return inst_r(ctx, a, x)
    _fail(a, b)
