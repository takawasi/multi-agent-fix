# multi-agent-fix

Parallel AI agents race to fix your failing tests.

Multiple agents generate different fixes simultaneously. First one that passes wins.

## Quick Start

```bash
# 1. Install
pip install multi-agent-fix

# 2. Set API key (any provider)
export OPENAI_API_KEY=sk-...
# or: ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY

# 3. Fix
multi-agent-fix ./my-project
```

## How It Works

1. Runs your tests
2. Detects failing tests
3. Spawns N agents (default: 3) with different temperatures
4. Each agent generates a fix in parallel
5. Tests each fix
6. First fix that passes wins

## Usage

```bash
# Basic usage
multi-agent-fix ./my-project

# More agents = more diversity
multi-agent-fix --agents 5 ./my-project

# Specify framework
multi-agent-fix --framework pytest ./my-project

# Dry run (show fixes without applying)
multi-agent-fix --dry-run ./my-project

# Max attempts per test
multi-agent-fix --max-attempts 5 ./my-project
```

## Supported Frameworks

| Framework | Detection |
|-----------|-----------|
| pytest | `pytest.ini` or `pyproject.toml` |
| npm | `package.json` |
| cargo | `Cargo.toml` |
| go | `go.mod` |

## Supported LLM Providers (BYOM)

Set one of these environment variables:

| Provider | Variable | Default Model |
|----------|----------|---------------|
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 |
| Google | `GEMINI_API_KEY` | gemini-2.0-flash |
| OpenRouter | `OPENROUTER_API_KEY` | anthropic/claude-sonnet-4-20250514 |

Override model with `*_MODEL` env var (e.g., `OPENAI_MODEL=gpt-4o`).

## Why Multiple Agents?

Different temperatures produce different fixes:
- Low temp (0.3): Conservative, obvious fixes
- High temp (0.9): Creative, unconventional fixes

Running them in parallel means you get the fastest fix that works.

## License

MIT
