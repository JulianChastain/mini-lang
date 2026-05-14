# Instantiation (Dunfield & Krishnaswami 2013, Fig. 10).
#
#   inst_l:  Γ ⊢ α̂ :≤= A ⊣ Δ   instantiate α̂ so that α̂ <: A
#   inst_r:  Γ ⊢ A =≤: α̂ ⊣ Δ   instantiate α̂ so that A <: α̂
#
# Both expect A to already have Γ applied to it, and α̂ to be unsolved in Γ.
from parser import Type, FunType, Forall, Exists, TVar
from context import (
    Context,
    CExists,
    CSolved,
    CTVar,
    CMarker,
    is_monotype,
    occurs,
    substitute,
    show_type,
    fresh,
)


def _try_solve(ctx: Context, name: str, t: Type) -> Context | None:
    """InstLSolve / InstRSolve: Γ, α̂, Γ' becomes Γ, α̂ = τ, Γ'.

    Only applies when τ is a monotype that is well-formed in Γ, the part of
    the context to the left of α̂.
    """
    if is_monotype(t) and ctx.drop(CExists(name)).well_formed(t):
        return ctx.replace(CExists(name), CSolved(name, t))
    return None


def _reach(ctx: Context, name: str, other: str) -> Context:
    """InstLReach / InstRReach: Γ[α̂][β̂] becomes Γ[α̂][β̂ = α̂].

    β̂ must come after α̂, otherwise Solve would have applied instead.
    """
    entries = ctx.entries
    if (
        CExists(other) not in entries
        or entries.index(CExists(other)) < entries.index(CExists(name))
    ):
        raise TypeError(f"Cannot instantiate ^{name} to ^{other} in [{ctx}]")
    return ctx.replace(CExists(other), CSolved(other, Exists(name)))


def _check_occurs(ctx: Context, name: str, t: Type):
    if CExists(name) not in ctx.entries:
        raise TypeError(f"^{name} is not an unsolved existential in [{ctx}]")
    if occurs(name, t):
        raise TypeError(f"Occurs check: ^{name} appears in {show_type(t)}")


def inst_l(ctx: Context, name: str, t: Type) -> Context:
    """Γ ⊢ α̂ :≤= A ⊣ Δ"""
    _check_occurs(ctx, name, t)
    solved = _try_solve(ctx, name, t)
    if solved is not None:
        return solved
    match t:
        case Exists(other):
            return _reach(ctx, name, other)
        case FunType(param, result):
            # InstLArr: the parameter flips direction (contravariance).
            ctx, a1, a2 = ctx.split_arrow(name)
            theta = inst_r(ctx, param, a1.name)
            return inst_l(theta, a2.name, theta.apply(result))
        case Forall(var, body):
            # InstLAllR: put β in scope, instantiate against the body, then
            # drop β and everything after it.
            beta = fresh(var)
            ctx = ctx.extend(CTVar(beta))
            delta = inst_l(ctx, name, substitute(body, var, TVar(beta)))
            return delta.drop(CTVar(beta))
    raise TypeError(f"Cannot instantiate ^{name} to {show_type(t)} in [{ctx}]")


def inst_r(ctx: Context, t: Type, name: str) -> Context:
    """Γ ⊢ A =≤: α̂ ⊣ Δ"""
    _check_occurs(ctx, name, t)
    solved = _try_solve(ctx, name, t)
    if solved is not None:
        return solved
    match t:
        case Exists(other):
            return _reach(ctx, name, other)
        case FunType(param, result):
            # InstRArr
            ctx, a1, a2 = ctx.split_arrow(name)
            theta = inst_l(ctx, a1.name, param)
            return inst_r(theta, theta.apply(result), a2.name)
        case Forall(var, body):
            # InstRAllL: open the forall with a fresh existential, scoped by
            # a marker so it's dropped afterwards.
            beta = fresh(var)
            ctx = ctx.extend(CMarker(beta), CExists(beta))
            delta = inst_r(ctx, substitute(body, var, Exists(beta)), name)
            return delta.drop(CMarker(beta))
    raise TypeError(f"Cannot instantiate ^{name} to {show_type(t)} in [{ctx}]")
