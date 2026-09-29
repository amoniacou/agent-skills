---
name: naming
description: Naming rules for files, directories, classes, modules, structs, errors, methods, functions and variables. Load it yourself, without being asked, before writing code that introduces a new name.
when_to_use: Before creating or renaming a file or directory, a class, module, struct, interface, error type, method or function. Also when adding a member to an existing family (a new *Type, *Validator, *Error), or reviewing a diff that adds names. Also on "how to name", "naming", "rename", "what should I call".
---

# Naming

Follow the language's own conventions first. The rules below fill the gaps.

## Classes, modules, structs

- Name by the role in the domain, as a noun: `Consumer`, `Publisher`, `Executor`, `Launcher`. Say what it is, not how it is built.
- A family of classes shares one suffix: `*Type`, `*Validator`, `*Generator`, `*Error`. Every member gets the suffix, no exceptions.
- A parent meant only for subclassing gets the `Base` prefix: `BaseType`, `BaseSelectType`.
- Ruby mixins: `ClassMethods`, `InstanceMethods`.
- `Manager`, `Helper`, `Holder` are fine when the class owns one clear thing and the name says which: `SubscriptionManager` owns subscriptions, `ChannelHolder` holds a channel. They are not fine as a bucket for unrelated functions.
- An interface is named by its role: `DatabaseConnector`, `TablesProvider`. An implementation puts the technology in front of the role: `PGConnector`, `MSSQLTablesProvider`.
- Do not put the kind of type in its name: no `Struct`, `Interface`, `Impl`, `Class`, `Object`. `FakeCompanies`, not `FakeCompaniesStruct`.

## Errors

State first, then the subject, then `Error`:

```
Invalid   ┐
Unknown   │
Missing   ├─ <Subject> Error
Duplicate │
Empty     ┘
```

`InvalidPayloadError`, `UnknownValueTypeError`, `MissingColumnError`, `DuplicateFieldNameError`, `EmptyValueError`.

A failed action: `<Action>Error`, like `PublishError`, `GeneratorError`.

## Methods and functions

- Verb plus noun: `fetch_values`, `load_schema`, `register_consumer`, `start_consumers`.
- One verb per action across the codebase. If validation methods are `validate_*`, do not add `check_*` for the same kind of work.
- Ruby: a question ends with `?` (`healthy?`, `valid?`, `migration_exists?`). A method that raises or changes state ends with `!` (`validate!`, `reset!`). Pair them: `valid?` returns a boolean, `validate!` raises.
- Lookup by key: `fields_by_ids`, `fields_by_permissions`. Lookup for something: `settings_for`, `exchange_for`.
- Collections are plural: `consumers`, `names`.
- Mapping and filtering: `mapSecretsToManagers`, `filterManagersUsingIngresses`.
- A getter has no `Get`: `Company()`, not `GetCompany()`. `Get`, `Fetch` or `Load` are for real I/O: a database, an API, a cluster.
- No `Get`/`Set` pairs that only read and write a field. Expose the field, or name the method after the real action. If an outside library defines the interface with `Get`/`Set`, follow the library.

## Files and directories

- Use the language's case for file names: Ruby, Python and Go `snake_case`, never `-` in Go. In other languages, match the files next to it.
- The file is named after the main thing inside it. The path follows the module nesting: `MyApp::Messaging::SubscriptionManager` lives in `lib/my_app/messaging/subscription_manager.rb`.
- A directory may carry the family suffix, so the file can drop it: `types/email.rb` holds `EmailType`. Do this for the whole family or not at all.
- Tests mirror the source path: `lib/my_app/messaging/consumer.rb` → `spec/my_app/messaging/consumer_spec.rb`, `client.go` → `client_test.go`. The test name repeats the source name exactly: `decryptor.go` → `decryptor_test.go`, not `descryptor_test.go`.
- No bucket names for files or packages: `utils`, `helpers`, `misc`, `common`, `stuff`. Name them after what they do. Test-only helpers are the one exception: `tests/utils` is fine.
- No version or state in the name: `_v2`, `_new`, `_old`, `_final`, `_copy`, `_tmp`. Change the file or delete it. Versions of a public API are different and fine: `apiv1`, `apiv2`.

## Go

- Constructor: `New<Type>`, or `new<type>` for an unexported type (`newS3Downloader`). Variants: `New<Type>For<X>`, `New<Type>With<Y>` (`NewCredentialForCompanyWithScopes`).
- Options: `With<Thing>` (`WithTables`, `WithClientDBDriver`).
- Errors: sentinel values `ErrNotFound`, `ErrNoContent`. Error types follow the Errors section above.
- Booleans: `IsPodReady`, `HasBinding`, `UsesSecret`.
- Receiver: one or two letters from the type (`p PostgresProvider`, `r Repo`, `c ConnectionCache`). One receiver name per type, the same in every method.

## Internal methods

Keep internals out of reach so nobody calls them by accident.

- Use `private` where the language has it.
- In Ruby, when a method cannot be private (class-level DSL registries, methods shared across mixins), wrap the name in double underscores: `__types__`, `__executors__`. Use one form only, do not mix `__name` and `__name__`.

## Consistency

- Before naming something new, look at how its neighbours are named and match them.
- One concept, one name across the project. Not `postgres` in one package and `postgresql` in another, not `ODataProvider` next to `OdataProvider`.
- An acronym is all upper or all lower case, never mixed: `HTTPHandler`, `APIV1`, `userID`, `MSSQLConnector`, not `HttpHandler`, `ApiV1`, `MsSQL`, `Mssql`.
- In camelCase every word starts with a capital: `EventuallyExecCommand`, not `EventuallyexecCommand`.
- Spell-check names. A typo in a name spreads to every caller.
