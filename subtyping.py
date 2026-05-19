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
from instantiation import inst_l, inst_r


def _fail(ctx: Context, a: Type, b: Type):
    raise TypeError(f"{show_type(a)} is not a subtype of {show_type(b)} in [{ctx}]")


def _check_occurs(name: str, t: Type):
    if occurs(name, t):
        raise TypeError(f"Occurs check: ^{name} appears in {show_type(t)}")


def subtype(ctx: Context, a: Type, b: Type) -> Context:
    """Γ ⊢ A <: B ⊣ Δ"""
    match a, b:
        case TVar(x), TVar(y) if x == y:
            # <:Var
            if not ctx.has_tvar(x):
                raise TypeError(f"Type variable {x} is not in scope in [{ctx}]")
            return ctx
        case IntType(), IntType():
            # <:Int (the paper's <:Unit)
            return ctx
        case Exists(x), Exists(y) if x == y:
            # <:Exvar
            if not ctx.has_exists(x):
                raise TypeError(f"^{x} is not in context [{ctx}]")
            return ctx
        case FunType(a1, a2), FunType(b1, b2):
            # <:→: parameters are contravariant
            theta = subtype(ctx, b1, a1)
            return subtype(theta, theta.apply(a2), theta.apply(b2))
        case _, Forall(var, body):
            # <:∀R, tried before ∀L so that ∀a. A <: ∀b. B keeps b rigid
            beta = fresh(var)
            ctx = ctx.extend(CTVar(beta))
            delta = subtype(ctx, a, substitute(body, var, TVar(beta)))
            return delta.drop(CTVar(beta))
        case Forall(var, body), _:
            # <:∀L: replace the bound variable with a fresh existential,
            # scoped by a marker
            alpha = fresh(var)
            ctx = ctx.extend(CMarker(alpha), CExists(alpha))
            delta = subtype(ctx, substitute(body, var, Exists(alpha)), b)
            return delta.drop(CMarker(alpha))
        case Exists(x), _ if CExists(x) in ctx.entries:
            # <:InstantiateL
            _check_occurs(x, b)
            return inst_l(ctx, x, b)
        case _, Exists(x) if CExists(x) in ctx.entries:
            # <:InstantiateR
            _check_occurs(x, a)
            return inst_r(ctx, a, x)
    _fail(ctx, a, b)
