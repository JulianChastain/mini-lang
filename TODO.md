# Next actions

## Done: Polymorphism
The checker follows Dunfield & Krishnaswami (2013): ordered context with
existential variables (`context.py`), instantiation (`instantiation.py`),
subtyping (`subtyping.py`), and the typing rules (`type_checker.py`).
Unannotated lambdas synthesize via →I⇒. Existentials still unsolved at the
end of a program are generalized (`/x -> x` gives `forall a. a -> a`); there
is no `let`, so nothing is generalized mid-program. Errors name the failing
rule and carry a trace; `examples.py` drives both `main.py --demo` and
`tests/test_examples.py`.

## Next: Algebraic data types and pattern matching

## Known TODOs
- `let` with generalization, so polymorphism doesn't need annotations
