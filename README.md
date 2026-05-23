# mini-lang

A tiny ML-style typed functional language. Built as a learning project so I could implement bidirectional typechecking à la Dunfield & Krishnaswami (2013).

## Status

Work in progress. Currently implemented:

- Lexer for the lambda calculus core, integer literals, `+`, and type syntax
- Recursive-descent parser producing an AST
- Tree-walking, environment-based evaluator
- Bidirectional typechecker following Dunfield & Krishnaswami (2013): ordered context with
  existential variables, instantiation, subtyping, and higher-rank polymorphism via annotations
- Type annotations `(e : T)` and a `typecheck(src)` entry point
- Leftover existentials are generalized at the top level, so `/x -> x` gets `forall a. a -> a`
- Type errors name the paper rule that failed, with a trace of the rules around it
- A command-line runner with a REPL and a guided demo

## Roadmap

- [x] Lexer
- [x] Parser (lambda core: variables, lambdas, application)
- [x] Integer literals and addition
- [x] Tree-walking evaluator
- [x] Bidirectional typechecking (simple types)
- [x] Type annotations and type syntax (`Int`, `a`, `->`, `forall a. A`)
- [x] Polymorphism (higher-rank, via annotations)
- [ ] Algebraic data types and pattern matching

## Syntax

    /x -> x              -- identity function
    (/x -> x) y          -- applied to y
    f x y                -- left-associative application
    1 + 2                -- integer addition
    /x -> x + 1          -- lambda bodies extend as far right as possible
    (e : Int -> Int)     -- type annotation (parentheses required)
    ((/x -> x + 1) : Int -> Int) 2

Types:

    Int                  -- integers
    a                    -- type variable
    Int -> Int -> Int    -- functions; `->` is right-associative
    forall a. a -> a     -- polymorphic type; extends as far right as possible
    forall a b. a -> b   -- shorthand for forall a. forall b. a -> b

`forall` and `Int` are reserved words.

Identifiers start with a letter or `_` and may contain letters, digits, and `_`.

## Usage

    uv run python main.py --demo          # tour of accepted and rejected programs
    uv run python main.py '/x -> x'       # typecheck and run one expression
    uv run python main.py                 # REPL

Example error:

    > ((/f -> f 1) : (forall a. a -> a) -> Int) (/x -> x + 1)
      type error [<:Var] a is not a subtype of Int
        while checking x against Int  (Sub)
        while checking x + 1 against a  (Sub)
        while checking /x -> x + 1 against a -> a  (→I)
        while checking /x -> x + 1 against forall a. a -> a  (∀I)
        while applying a function of type (forall a. a -> a) -> Int to /x -> x + 1  (→App)

## Running tests

    cd tests && PYTHONPATH=.. uv run python -m unittest discover -s .
