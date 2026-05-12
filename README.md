# mini-lang

A tiny ML-style typed functional language. Built as a learning project so I could implement bidirectional typechecking à la Dunfield & Krishnaswami (2013).

## Status

Work in progress. Currently implemented:

- Lexer for the lambda calculus core, integer literals, `+`, and type syntax
- Recursive-descent parser producing an AST
- Tree-walking, environment-based evaluator
- Bidirectional typechecker (`check` / `synth`) for the simply-typed lambda calculus with `Int`
- Type annotations `(e : T)` and a `typecheck(src)` entry point
- Immutable ordered typing context with existential variables, the groundwork for polymorphism

## Roadmap

- [x] Lexer
- [x] Parser (lambda core: variables, lambdas, application)
- [x] Integer literals and addition
- [x] Tree-walking evaluator
- [x] Bidirectional typechecking (simple types)
- [x] Type annotations and type syntax (`Int`, `a`, `->`, `forall a. A`)
- [ ] Polymorphism
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

`forall` and `Int` are reserved words.

Identifiers start with a letter or `_` and may contain letters, digits, and `_`.

## Running tests

    cd tests && PYTHONPATH=.. uv run python -m unittest discover -s .
