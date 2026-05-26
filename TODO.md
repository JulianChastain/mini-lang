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

## Done: let and a REPL
`let x [: A] = e1 in e2`. Without an annotation x is monomorphic, like the
paper; with one it can be polymorphic. `main.py` prints `value : type` and
has a REPL with session definitions, file mode, and `--demo`.
`programs/church.mini` shows rank-2 Church numerals.

## Known TODOs
- Optional: let-generalization, so polymorphic lets don't need annotations
- Type aliases, so `programs/church.mini` can name its numeral type
