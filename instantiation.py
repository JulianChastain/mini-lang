# Instantiation (Dunfield & Krishnaswami 2013, Fig. 10).
#
#   inst_l:  Γ ⊢ α̂ :≤= A ⊣ Δ   instantiate α̂ so that α̂ <: A
#   inst_r:  Γ ⊢ A =≤: α̂ ⊣ Δ   instantiate α̂ so that A <: α̂
#
# Both expect A to already have Γ applied to it, α̂ to be unsolved in Γ, and
# α̂ not to occur in A. Subtyping does that occurs check before calling in.
from parser import Type, FunType, Forall, Exists, TVar, TCon
from context import (
    Context,
    CExists,
    CSolved,
    CTVar,
    CMarker,
    is_monotype,
    substitute,
    show_type,
    fresh,
)
from errors import TypeCheckError


def _try_solve(ctx: Context, name: str, t: Type) -> Context | None:
    """InstLSolve / InstRSolve: Γ, α̂, Γ' becomes Γ, α̂ = τ, Γ'.

    Only applies when τ is a monotype that is well-formed in Γ, the part of
    the context to the left of α̂.
    """
    if is_monotype(t) and ctx.drop(CExists(name)).well_formed(t):
        return ctx.replace(CExists(name), CSolved(name, t))
    return None


def _reach(ctx: Context, name: str, other: str, rule: str) -> Context:
    """InstLReach / InstRReach: Γ[α̂][β̂] becomes Γ[α̂][β̂ = α̂].

    β̂ must come after α̂, otherwise Solve would have applied instead.
    """
    entries = ctx.entries
    if (
        CExists(other) not in entries
        or entries.index(CExists(other)) < entries.index(CExists(name))
    ):
        raise TypeCheckError(
            rule, f"cannot instantiate ^{name} to ^{other} in [{ctx}]"
        )
    return ctx.replace(CExists(other), CSolved(other, Exists(name)))


def _check_unsolved(ctx: Context, name: str, rule: str):
    if CExists(name) not in ctx.entries:
        raise TypeCheckError(rule, f"^{name} is not an unsolved existential in [{ctx}]")


def _out_of_scope(ctx: Context, name: str, t: Type, rule: str):
    # Solve was the only rule left, and it needs t to be well-formed to the
    # left of α̂. A rigid type variable introduced later can't escape there.
    raise TypeCheckError(
        rule,
        f"cannot solve ^{name} := {show_type(t)}: {show_type(t)} is not in scope"
        f" where ^{name} was introduced",
    )


def inst_l(ctx: Context, name: str, t: Type) -> Context:
    """Γ ⊢ α̂ :≤= A ⊣ Δ"""
    _check_unsolved(ctx, name, "InstLSolve")
    solved = _try_solve(ctx, name, t)
    if solved is not None:
        return solved
    match t:
        case Exists(other):
            return _reach(ctx, name, other, "InstLReach")
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
        case TCon(con, args):
            # InstLTCon: like InstLArr, split α̂ into T α̂₁ … α̂ₙ in place.
            # Arguments are monotypes, so each one is just an equation and
            # the direction doesn't matter.
            ctx, parts = ctx.split_tcon(name, con, len(args))
            for part, arg in zip(parts, args):
                ctx = inst_l(ctx, part.name, ctx.apply(arg))
            return ctx
    _out_of_scope(ctx, name, t, "InstLSolve")


def inst_r(ctx: Context, t: Type, name: str) -> Context:
    """Γ ⊢ A =≤: α̂ ⊣ Δ"""
    _check_unsolved(ctx, name, "InstRSolve")
    solved = _try_solve(ctx, name, t)
    if solved is not None:
        return solved
    match t:
        case Exists(other):
            return _reach(ctx, name, other, "InstRReach")
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
        case TCon(con, args):
            # InstRTCon
            ctx, parts = ctx.split_tcon(name, con, len(args))
            for part, arg in zip(parts, args):
                ctx = inst_r(ctx, ctx.apply(arg), part.name)
            return ctx
    _out_of_scope(ctx, name, t, "InstRSolve")
