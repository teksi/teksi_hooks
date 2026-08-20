# teksi_hooks

A lightweight capability-based framework for implementing TEKSI workflows.

## Documentation
See [https://teksi.github.io/teksi_hooks/index.html](https://teksi.github.io/teksi_hooks/index.html)

## Overview

`teksi_hooks` provides reusable building blocks for rights evaluation, validation,
configuration parsing, hook execution and capability-based dependency injection.

The framework is intentionally domain-agnostic and does not depend on QGIS,
PostgreSQL, INTERLIS, wastewater models or any specific application.

Applications compose the framework by providing capabilities and concrete
implementations for deployment-specific concerns.

## Features

- Dynamic hook loading and execution
- Capability-based dependency injection
- Rights and permission modelling
- Validation framework with findings and severity levels
- Configuration-driven workflows
- Parser and resolver infrastructure
- Extensible identifier types (`Oid`)
- Domain-independent architecture
- No dependency on QGIS
- No dependency on PostgreSQL
- No dependency on specific TEKSI business models

## Core Concepts

### Hooks

Hooks implement workflows and extension points.

```python
from teksi_hooks.hook import (
    HookBase,
    HookContext,
    HookMetadata,
)


class Hook(HookBase):

    required_capabilities = frozenset()

    @property
    def metadata(
        self,
    ) -> HookMetadata:
        return HookMetadata(
            name="Example Hook",
            description="Example hook implementation.",
        )

    def run_hook(
        self,
        context: HookContext,
    ) -> None:
        context.logger.info(
            "Hello from a hook.",
        )
```

### Capabilities

Capabilities provide application-specific services.

The framework depends on contracts rather than implementations.

```python
context = HookContext(
    parameters={},
    logger=logger,
    capabilities={
        SqlCapability: SqlCapability(
            connection,
        ),
    },
)
```

Access inside a hook:

```python
sql = context.capability(
    SqlCapability,
)
```

### Rights Definitions

Rights, privileges and validation rules can be defined declaratively.

```yaml
privileges:
  DBW_WI:
    labels:
      de: Datenbewirtschafter Werkinformation

classes:
  - id: wastewater_structure

    create_rules:
      - privileges:
          - DBW_WI
```

The parser produces typed model definitions which are subsequently resolved
and evaluated by framework services.

### Findings

Validation and evaluation produce structured findings.

```python
Finding(
    severity=Severity.ERROR,
    message="Invalid transition.",
)
```

Findings can be aggregated and raised through framework exceptions.

## Hook Execution

```python
from teksi_hooks.hook import (
    HookContext,
    HookHandler,
)

context = HookContext(
    parameters={},
    logger=logger,
    capabilities={},
)

HookHandler(
    file="example_hook.py",
).run(
    context,
)
```

## Architecture

```text
Application
     │
     ▼
Capabilities
     │
     ▼
Services / Evaluators
     │
     ▼
Resolvers
     │
     ▼
Models
     │
     ▼
Hooks
```

## Package Structure

```text
teksi_hooks/
├── capabilities/
├── evaluators/
├── models/
├── parser/
├── resolver/
├── services/
├── exceptions.py
└── hook.py
```

### Models

Typed domain contracts and value objects.

Examples:

- Oid
- RightsDefinition
- ClassDefinition
- Finding
- Validation rules

### Parsers

Convert external configuration formats into typed model definitions.

Examples:

- RightsParser
- ProviderRightsParser
- WildcardRightsParser

### Resolvers

Resolve inheritance, defaults and cross-references.

### Evaluators

Apply runtime evaluation logic.

Examples:

- Rights evaluation
- Validation evaluation
- Transition evaluation

### Services

Provide reusable orchestration and application services.

### Capabilities

Define extension points supplied by the hosting application.

## Design Principles

- Explicit over implicit
- Configuration over hard-coding
- No global state
- Capability-based dependency injection
- Strongly typed contracts
- Separation of parsing, resolution and evaluation
- Domain-independent framework core
- Application-defined integrations

## License

GPL-2.0-or-later
