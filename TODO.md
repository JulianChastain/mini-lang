# Next actions

## Immediate: Polymorphism
The simply-typed bidirectional checker works for `Int` and function types.
Next step is extending it toward Dunfield & Krishnaswami (2013):

- [x] Type variables and `forall` types in the Type AST
- [x] Type annotations in the surface syntax so lambdas can be synthesized
- Ordered typing context with existential variables
- Subtyping / instantiation judgments (the checker currently compares types
  structurally, so `forall` annotations parse but don't check yet)

## After polymorphism
Algebraic data types and pattern matching.

## Known TODOs
- Integration tests (source → tokens → ast → type → value)
