# Next actions

## Immediate: Evaluator
Tree-walking, environment-based (not substitution-based).

- Environment is `dict[str, Value]`, immutable (copy on bind)
- Values: closures (`Closure(param, body, env)`), that's it for now
- `eval(expr: Expr, env: Env) -> Value`
  - `Var`: lookup in env
  - `Lam`: returns `Closure`
  - `App`: eval function, eval arg, apply (extend closure's env with param=arg, eval body)
- Tests: identity `(/x -> x) y` with y bound to something
- Tests: constant `(/x -> /y -> x) a b` evaluates to `a`
- Tests: application chain

## After evaluator
Switch to typing. Start with simple types (no polymorphism): build the
Type AST, then implement `check` and `synth` for the bidirectional pair
on the simply-typed lambda calculus. Then add polymorphism.

## Known TODOs
- Integration tests (source → tokens → ast)