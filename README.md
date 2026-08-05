# mini-lang

[![tests](https://github.com/JulianChastain/mini-lang/actions/workflows/tests.yml/badge.svg)](https://github.com/JulianChastain/mini-lang/actions/workflows/tests.yml)

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

### Rule by rule

Every rule of the paper's algorithmic system, and every rule added for data, names the function that implements it. In the code, each rule's name appears in a comment on its branch or in the errors it raises, so you can search for it. `tests/test_readme.py` checks that every rule in these tables appears in the source of the function listed.

**Algorithmic subtyping, Γ ⊢ A <: B ⊣ Δ (Fig. 9)**

| Rule | What it does | Function |
| --- | --- | --- |
| <:Var | α <: α, if α is in scope | `subtyping.subtype` |
| <:Unit | the base type; here `Int <: Int` | `subtyping.subtype` |
| <:Exvar | α̂ <: α̂ | `subtyping.subtype` |
| <:→ | contravariant in the parameter, then [Θ] applied to the results | `subtyping.subtype` |
| <:∀L | ∀α. A <: B: open α with a fresh α̂ behind a marker ▶α̂ | `subtyping.subtype` |
| <:∀R | A <: ∀α. B: put α in scope, then drop it; tried before ∀L | `subtyping.subtype` |
| <:InstantiateL | α̂ <: A becomes α̂ :≤= A, after the occurs check | `subtyping.subtype` |
| <:InstantiateR | A <: α̂ becomes A =≤: α̂, after the occurs check | `subtyping.subtype` |

**Instantiation, Γ ⊢ α̂ :≤= A ⊣ Δ and Γ ⊢ A =≤: α̂ ⊣ Δ (Fig. 10)**

| Rule | What it does | Function |
| --- | --- | --- |
| InstLSolve | α̂ := τ, if τ is a monotype well-formed left of α̂ | `instantiation.inst_l` |
| InstLReach | α̂ :≤= β̂ with β̂ later: β̂ := α̂ | `instantiation.inst_l` |
| InstLArr | split α̂ into α̂₁ → α̂₂, then A₁ =≤: α̂₁ and α̂₂ :≤= [Θ]A₂ | `instantiation.inst_l` |
| InstLAllR | α̂ :≤= ∀β. B: put β in scope, instantiate, then drop it | `instantiation.inst_l` |
| InstRSolve | τ =≤: α̂: α̂ := τ | `instantiation.inst_r` |
| InstRReach | β̂ =≤: α̂ with β̂ later: β̂ := α̂ | `instantiation.inst_r` |
| InstRArr | split α̂, then α̂₁ :≤= A₁ and [Θ]A₂ =≤: α̂₂ | `instantiation.inst_r` |
| InstRAllL | ∀β. B =≤: α̂: open β with a fresh β̂ behind ▶β̂ | `instantiation.inst_r` |

**Typing (Fig. 11)**

| Rule | Judgment | Function |
| --- | --- | --- |
| Var | Γ ⊢ x ⇒ A, for x : A in Γ | `type_checker.synth` |
| Sub | e ⇐ B, from e ⇒ A and [Θ]A <: [Θ]B | `type_checker.check` |
| Anno | (e : A) ⇒ A, from Γ ⊢ A and e ⇐ A | `type_checker.synth` |
| 1I | the unit introduction, checking; here `n ⇐ Int` | `type_checker.check` |
| 1I⇒ | the unit introduction, synthesizing; here `n ⇒ Int` | `type_checker.synth` |
| ∀I | e ⇐ ∀α. A, from Γ, α ⊢ e ⇐ A | `type_checker.check` |
| ∀App | ∀α. A • e: instantiate α with a fresh α̂ | `type_checker.app_synth` |
| →I | λx. e ⇐ A → B, from Γ, x : A ⊢ e ⇐ B | `type_checker.check` |
| →I⇒ | λx. e ⇒ α̂ → β̂, from Γ, α̂, β̂, x : α̂ ⊢ e ⇐ β̂ | `type_checker.synth` |
| →E | e₁ e₂: synthesize e₁, then apply its type to e₂ | `type_checker.synth` |
| α̂App | α̂ • e: split α̂ into α̂₁ → α̂₂ and check e ⇐ α̂₁ | `type_checker.app_synth` |
| →App | A → C • e: check e ⇐ A, giving C | `type_checker.app_synth` |

**Added for data, lets and operators**

| Rule | What it does | Function |
| --- | --- | --- |
| Decl | checks a group of declarations and builds constructor schemes | `types_table.declare_group` |
| <:TCon | T A₁…Aₙ <: T B₁…Bₙ, argument by argument | `subtyping.subtype` |
| InstLTCon | α̂ :≤= T A₁…Aₙ: split α̂ into T α̂₁…α̂ₙ in place | `instantiation.inst_l` |
| InstRTCon | the mirror image of InstLTCon | `instantiation.inst_r` |
| Con | K ⇒ its scheme ∀ā. F₁ → … → Fₙ → T ā | `type_checker.synth` |
| Let⇒ | let, synthesizing; removes only the x : A entry afterwards | `type_checker.synth` |
| Let⇐ | let, checking the body against the expected type | `type_checker.check` |
| LetRec | e₁ ⇐ A with f : A already in scope; the annotation is required | `type_checker._let_binding` |
| BinOp | `+ - *` on Int; `== <` give Bool | `type_checker.synth` |
| Match⇐ | each branch between a marker ▶ and a drop back to it | `type_checker._check_match` |
| Match⇒ | a fresh β̂ for the result, then Match⇐ | `type_checker.synth` |
| PVar | x ⇐ A extends Γ with x : A, polymorphic or not | `patterns.check_pattern` |
| PWild | _ ⇐ A leaves Γ unchanged | `patterns.check_pattern` |
| PInt | n ⇐ A, from A <: Int | `patterns.check_pattern` |
| PCon | K p₁…pₙ ⇐ A, from A <: T β̂, then each pᵢ against its field | `patterns.check_pattern` |

The supporting operations:
- Γ ⊢ A, well-formedness: `Context.why_ill_formed`
- [Γ]A, applying a context: `Context.apply`
- splitting α̂: `Context.split`
- the occurs check: `subtyping._check_occurs`
- top-level generalization: `type_checker.generalize`
- missing and unreachable cases: `exhaustiveness.missing_case` and `exhaustiveness.useless_branches`

### The new rules in the paper's notation

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

GitHub Actions (`.github/workflows/tests.yml`) runs this on Python 3.12 and 3.13 for every push and pull request, then runs `--demo` and every program in `programs/`.
