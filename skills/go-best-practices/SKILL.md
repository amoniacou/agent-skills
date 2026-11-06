---
name: go-best-practices
description: Best practices for writing Go code. Load it yourself, without being asked, before writing or changing Go code.
when_to_use: Before writing, editing or reviewing a .go file. Also on "golang", "go code", "idiomatic go", "go best practices".
---

# Go best practices

## 1. No reflection when the types are known

When the code knows the types at compile time, write plain code. `reflect` is many times slower, skips the compiler's type checks and hides which fields are used.

- compare two fields with `a.Name == b.Name`, not `reflect.DeepEqual(a.Name, b.Name)`
- compare structs whose fields are all comparable with `a == b`
- compare slices and maps with `slices.Equal` and `maps.Equal`
- branch on a type with a type switch, not `reflect.TypeOf` or `reflect.ValueOf(x).Kind()`
- write a shared function with type parameters, not `any` plus `reflect`
- copy a struct with assignment, not by walking its fields

Use `reflect` only when the type is unknown until runtime and nothing else works: a serializer, a struct-tag parser, an ORM mapper. In tests, `reflect.DeepEqual` and `cmp.Diff` are fine.

## 2. Look up code with gopls and go doc, not grep

- Where a symbol of this repository is defined or used: the LSP tool (gopls) — `definition`, `references`, `documentSymbol`, `hover`. It is exact; grep matches text and misses or over-matches.
- What a library exports: `go doc <pkg>`, `go doc <pkg>.<Type>`, `go doc <pkg>.<Type>.<Method>`, or LSP hover. Never read or grep sources under `$GOMODCACHE` (`pkg/mod`). If `go doc` says the package is not in the main module, `go get <module>@<version>` first.
- grep and rg are for text: strings, log messages, annotations, yaml, docs.
