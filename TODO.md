# Next actions

## Done in v0.2
- Declared types with arguments (`type List a = Nil | Cons a (List a)`), a
  global type table, and checks for arity, scope and duplicates
- <:TCon and InstL/RTCon; constructors typed as polymorphic functions
- `let rec` with a required annotation
- Pattern matching: syntax, evaluation, the pattern judgment, Match⇐/⇒
- Polymorphic fields (`type Poly = Poly (forall a. a -> a)`)
- Exhaustiveness and unreachable-branch checks (Maranget)
- `if`, `- * == <`, tuples, list syntax, and a prelude in minilang
- Example programs: bst, eval, poly

## Ideas
- let-generalization, so polymorphic lets don't need annotations
- Type aliases, so Church numerals can name their type
- Strings and a `print`, for programs with output
- Or-patterns and guards (the usefulness algorithm extends to both)
- Source positions in errors
