# Next actions

## Done: Polymorphism
The checker follows Dunfield & Krishnaswami (2013): ordered context with
existential variables (`context.py`), instantiation (`instantiation.py`),
subtyping (`subtyping.py`), and the typing rules (`type_checker.py`).
Unannotated lambdas synthesize via →I⇒; there's no let-generalization, so
leftover existentials show up in the result type (e.g. `/x -> x` gives
`^a -> ^a`).

## Next: Algebraic data types and pattern matching

## Known TODOs
- Integration tests (source → tokens → ast → type → value)
