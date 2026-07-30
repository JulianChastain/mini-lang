# mini-lang

A small ML-style functional language with **higher-rank polymorphism**, built to implement Dunfield & Krishnaswami's *Complete and Easy Bidirectional Typechecking for Higher-Rank Polymorphism* (2013), and then extend it with algebraic data types and pattern matching in the same style.

```
> map (/x -> x * 2) [1, 2, 3]
  [2, 4, 6] : List Int

> type Poly = Poly (forall a. a -> a)
  declared Poly
> match Poly (/x -> x) with | Poly f -> (f 1, f True)
  (1, True) : (Int, Bool)

> /xs -> match xs with | [] -> 0 | [x] -> x
  type error [Match] match xs with ... doesn't cover every List Int; missing: Cons _ (Cons _ _)
```

## Quick start

    uv run python main.py --demo                  # tour of accepted and rejected programs
    uv run python main.py                         # REPL, with the prelude loaded
    uv run python main.py programs/bst.mini       # run a program file
    uv run python main.py 'length [1, 2, 3]'      # typecheck and run one expression

Results print as `value : type`. The prelude (`prelude.mini`) declares `Bool`, `Option` and `List` and defines `not`, `map`, `filter`, `foldr`, `length` and `append`; pass `--no-prelude` to start empty. In the REPL, `:t e` prints a type, `:env` lists definitions, `:help` lists the rest.

Example programs:

| File | Shows |
| --- | --- |
| `programs/bst.mini` | binary search trees generic in the element type, ordering passed as a value |
| `programs/eval.mini` | an expression language with an evaluator and a simplifier, in minilang |
| `programs/poly.mini` | polymorphic fields: a Church numeral stored in data, a record of polymorphic functions |
| `programs/church.mini` | rank-2 Church numerals as plain functions |

## The language

A program is a sequence of `type` declarations and `let` definitions, optionally ending in an expression. If it has no final expression, its answer is `main`.

```
-- comments run to the end of the line
type Tree a = Leaf | Node (Tree a) a (Tree a)

let rec insert : Tree Int -> Int -> Tree Int = /t -> /x -> match t with
  | Leaf -> Node Leaf x Leaf
  | Node l y r -> if x < y then Node (insert l x) y r else Node l y (insert r x)

let main = foldr (/x -> /t -> insert t x) Leaf [3, 1, 2]
```

Expressions:

    /x -> x                          lambda (the body extends as far right as possible)
    f x y                            application, left-associative
    1 + 2 * 3 - 4,  a == b,  a < b   integer arithmetic and comparison (== and < give Bool)
    (e : A)                          type annotation
    let x = e1 in e2                 monomorphic let
    let x : A = e1 in e2             annotated let, polymorphic if A is
    let rec f : A = e1 in e2         recursion; the annotation is required
    if c then a else b               sugar for match c with | True -> a | False -> b
    match e with | p1 -> e1 | ...    first matching branch wins
    Some 1,  Cons 1 Nil              constructors are curried functions
    (1, True),  [1, 2, 3]            tuples and lists

Patterns: `x`, `_`, integer literals, constructors with nested patterns (`Cons x (Cons y _)`), tuples `(a, b)` and lists `[x, y]`.

Types: `Int`, type variables `a`, `A -> B` (right-associative), `forall a b. A`, declared types `List a` and `Option (List Int)`, and tuples `(A, B)`.

A plain expression after a definition reads as more arguments to it (`let x = f a` followed by `g x` would mean `f a g x`). So a program's final expression has to start with a keyword such as `let`, `match` or `if`; otherwise, define `main`.

## The type system

The core is the 2013 paper, rule for rule. The ordered context is **immutable**: every judgment takes Γ and returns Δ, as in the paper's `Γ ⊢ … ⊣ Δ`. Every type error names the rule that failed, followed by the rules it was inside:

```
> ((/f -> f 1) : (forall a. a -> a) -> Int) (/x -> x + 1)
  type error [<:Var] a is not a subtype of Int
    while checking x against Int  (Sub)
    while checking x + 1 against a  (Sub)
    while checking /x -> x + 1 against a -> a  (→I)
    while checking /x -> x + 1 against forall a. a -> a  (∀I)
    while applying a function of type (forall a. a -> a) -> Int to /x -> x + 1  (→App)
```

### From the paper

| Judgment | Rules | Function |
| --- | --- | --- |
| Γ ⊢ A, applying [Γ]A | well-formedness, substitution | `Context.why_ill_formed`, `Context.apply` (`context.py`) |
| Γ ⊢ A <: B ⊣ Δ (Fig. 9) | <:Var, <:Unit (here <:Int), <:Exvar, <:→, <:∀L, <:∀R, <:InstantiateL/R | `subtype` (`subtyping.py`) |
| Γ ⊢ α̂ :≤= A ⊣ Δ (Fig. 10) | InstLSolve, InstLReach, InstLArr, InstLAllR | `inst_l` (`instantiation.py`) |
| Γ ⊢ A =≤: α̂ ⊣ Δ (Fig. 10) | InstRSolve, InstRReach, InstRArr, InstRAllL | `inst_r` |
| Γ ⊢ e ⇐ A ⊣ Δ (Fig. 11) | 1I, ∀I, →I, Sub | `check` (`type_checker.py`) |
| Γ ⊢ e ⇒ A ⊣ Δ | Var, Anno, 1I⇒, →I⇒, →E | `synth` |
| Γ ⊢ A • e ⇒⇒ C ⊣ Δ | ∀App, α̂App, →App | `app_synth` |

### Extensions in the same style

Declared types live in a global table of type parameters and constructor schemes (`types_table.py`), carried on Γ beside the ordered entries. Declarations never go out of scope, and every rule already passes Γ along, so nothing needed a new parameter.

**Declared types.** The arguments must be monotypes: Γ ⊢ T τ₁ … τₙ needs T declared with n parameters, and each τᵢ to be a monotype. Instantiation stays predicative as in the paper. Because subtyping between monotypes is just equality, one invariant rule is enough, with no variance to decide:

    Θ₀ = Γ     Θᵢ₋₁ ⊢ [Θᵢ₋₁]Aᵢ <: [Θᵢ₋₁]Bᵢ ⊣ Θᵢ
    ─────────────────────────────────────────────── <:TCon       subtype
    Γ ⊢ T A₁ … Aₙ <: T B₁ … Bₙ ⊣ Θₙ

    Γ[α̂ₙ, …, α̂₁, α̂ = T α̂₁ … α̂ₙ] = Θ₀     Θᵢ₋₁ ⊢ α̂ᵢ :≤= [Θᵢ₋₁]Aᵢ ⊣ Θᵢ
    ─────────────────────────────────────────────────────────────────── InstLTCon   inst_l
    Γ[α̂] ⊢ α̂ :≤= T A₁ … Aₙ ⊣ Θₙ

InstRTCon (`inst_r`) is the mirror image. Both split α̂ in place the way InstLArr splits it into an arrow (`Context.split`).

**Constructors** are looked up as polymorphic functions, so the existing application rules handle them unchanged:

    (K : ∀ā. F₁ → … → Fₙ → T ā) in the table
    ─────────────────────────────────────── Con          synth
    Γ ⊢ K ⇒ ∀ā. F₁ → … → Fₙ → T ā ⊣ Γ

**Recursion** requires an annotation, because the paper doesn't generalize:

    Γ, f : A ⊢ e₁ ⇐ A ⊣ Θ, f : A, Θ'     Θ, f : A ⊢ e₂ ⇒ C ⊣ Δ
    ───────────────────────────────────────────────────────── LetRec   _let_binding
    Γ ⊢ let rec f : A = e₁ in e₂ ⇒ C ⊣ Δ (without f : A)

**Patterns**, Γ ⊢ p ⇐ A ⊣ Δ (`check_pattern` in `patterns.py`):

    Γ ⊢ x ⇐ A ⊣ Γ, x : A        Γ ⊢ _ ⇐ A ⊣ Γ        Γ ⊢ n ⇐ A ⊣ Δ  if  Γ ⊢ A <: Int ⊣ Δ

    (K : ∀ā. F₁ → … → Fₙ → T ā)    Γ, β̂ ⊢ A <: T β̂ ⊣ Θ₀    Θᵢ₋₁ ⊢ pᵢ ⇐ [Θᵢ₋₁][β̂/ā]Fᵢ ⊣ Θᵢ
    ──────────────────────────────────────────────────────────────────────────── PCon
    Γ ⊢ K p₁ … pₙ ⇐ A ⊣ Θₙ

The pattern rules have three useful consequences:
- An unsolved α̂ being matched is split into T β̂ by InstLTCon inside the subtyping premise, so the first constructor pattern determines its type.
- A polymorphic matched type is instantiated first.
- A variable pattern takes its field's type as is. That's how `Poly f` gives `f : forall a. a -> a`.

**Match**, in `_check_match` (checking) and `synth` (synthesis):

    Γ ⊢ e ⇒ A ⊣ Θ₀    for each branch:  Θᵢ₋₁, ▶ ⊢ pᵢ ⇐ [Θᵢ₋₁]A ⊣ Θ'    Θ' ⊢ eᵢ ⇐ [Θ']C ⊣ Θᵢ, ▶, Θ''
    ────────────────────────────────────────────────────────────────────────────── Match⇐
    Γ ⊢ match e with | p₁ -> e₁ | … ⇐ C ⊣ Θₙ

    Γ, β̂ ⊢ match … ⇐ β̂ ⊣ Δ
    ─────────────────────── Match⇒
    Γ ⊢ match … ⇒ β̂ ⊣ Δ

The marker ▶ removes each branch's variables afterwards. Match⇒ treats a match like →I⇒ treats a lambda, so unannotated matches are inferred: `/o -> match o with | None -> 0 | Some n -> n + 1` gets `Option Int -> Int`.

**Checking matches.** During typing, each match records its scrutinee's type. After the whole program is typed, that type is resolved against the final context, because its existentials may only be solved later. Then Maranget's usefulness algorithm (*Warnings for pattern matching*, 2007; `exhaustiveness.py`) runs on it:
- **Missing cases are an error**, with an example of a missing value (`missing: Cons _ (Cons _ _)`).
- **Unreachable branches are a warning.** The program still runs.
- The table gives each type's full set of constructors. Integers count as having infinitely many, so a match on them needs a wildcard.

### Other decisions

- **Generalization only at the top level.** A whole program, and each top-level or REPL definition, generalizes its leftover existentials, so `/x -> x` gets `forall a. a -> a`. A `let` inside an expression doesn't generalize, as in the paper. Annotate it to make it polymorphic.
- **Predicativity.** Type variables are only ever instantiated to monotypes. For example, `three succ zero` on Church numerals is rejected, because it needs `a` to be the numeral type, which is polymorphic.
- **Tuples are declared types** (`Tuple2` to `Tuple7`), built in. `(a, b)` is sugar, so tuples needed no new typing or exhaustiveness rules.

## Project layout

| File | Role |
| --- | --- |
| `lexer.py`, `parser.py` | tokens, AST, recursive-descent parser |
| `context.py` | types, the ordered context, the type table's data |
| `types_table.py` | checking declarations and building constructor schemes |
| `subtyping.py`, `instantiation.py` | Fig. 9 and Fig. 10, plus the declared-type rules |
| `type_checker.py` | Fig. 11, let, let rec, match, generalization, printers |
| `patterns.py`, `exhaustiveness.py` | pattern typing; missing and unreachable cases |
| `evaluator.py` | environment-based interpreter |
| `program.py`, `main.py` | running programs; the CLI and REPL |
| `examples.py` | the demo programs, also run as tests |

## Running tests

    cd tests && PYTHONPATH=.. uv run python -m unittest discover -s .
