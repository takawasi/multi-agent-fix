"""LLM agent for generating fixes - BYOM (Bring Your Own Model)."""

import os
import json
import httpx
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class FixAttempt:
    """A fix attempt from an agent."""

    agent_id: int
    file: str
    new_content: str
    explanation: str
    success: bool = False


def get_api_config() -> tuple[str, str, str]:
    """Get API configuration from environment."""
    # Check for various API providers
    if os.environ.get("OPENAI_API_KEY"):
        return (
            "openai",
            os.environ["OPENAI_API_KEY"],
            os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        )
    if os.environ.get("ANTHROPIC_API_KEY"):
        return (
            "anthropic",
            os.environ["ANTHROPIC_API_KEY"],
            os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        )
    if os.environ.get("GEMINI_API_KEY"):
        return (
            "gemini",
            os.environ["GEMINI_API_KEY"],
            os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        )
    if os.environ.get("OPENROUTER_API_KEY"):
        return (
            "openrouter",
            os.environ["OPENROUTER_API_KEY"],
            os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514"),
        )

    raise ValueError(
        "No API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, "
        "GEMINI_API_KEY, or OPENROUTER_API_KEY"
    )


def call_llm(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    temperature: float = 0.7,
) -> str:
    """Call LLM API and return response."""
    headers = {}
    url = ""
    payload = {}

    if provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

    elif provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

    elif provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }

    elif provider == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

    else:
        raise ValueError(f"Unknown provider: {provider}")

    with httpx.Client(timeout=120) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    # Extract text based on provider
    if provider == "anthropic":
        return data["content"][0]["text"]
    elif provider == "gemini":
        return data["candidates"][0]["content"]["parts"][0]["text"]
    else:  # openai, openrouter
        return data["choices"][0]["message"]["content"]


def generate_fix(
    agent_id: int,
    test_name: str,
    test_file: str,
    test_source: str,
    test_output: str,
    temperature: float,
) -> FixAttempt:
    """Generate a fix for a failing test."""
    provider, api_key, model = get_api_config()

    prompt = f"""You are a debugging expert. A test is failing. Fix the code.

## Failed Test
Name: {test_name}
File: {test_file}

## Test Source
```
{test_source}
```

## Test Output
```
{test_output}
```

## Instructions
1. Analyze why the test is failing
2. Provide the COMPLETE fixed file content
3. Respond in this exact JSON format:

```json
{{
  "file": "{test_file}",
  "content": "COMPLETE FILE CONTENT HERE",
  "explanation": "Brief explanation of the fix"
}}
```

Return ONLY the JSON, no other text."""

    try:
        response = call_llm(provider, api_key, model, prompt, temperature)

        # Parse JSON from response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(response[json_start:json_end])
            return FixAttempt(
                agent_id=agent_id,
                file=data.get("file", test_file),
                new_content=data.get("content", ""),
                explanation=data.get("explanation", ""),
            )
    except Exception as e:
        return FixAttempt(
            agent_id=agent_id,
            file=test_file,
            new_content="",
            explanation=f"Error: {e}",
        )

    return FixAttempt(
        agent_id=agent_id,
        file=test_file,
        new_content="",
        explanation="Failed to parse response",
    )


def run_parallel_agents(
    test_name: str,
    test_file: str,
    test_source: str,
    test_output: str,
    num_agents: int = 3,
) -> list[FixAttempt]:
    """Run multiple agents in parallel to generate fixes."""
    # Use different temperatures for diversity
    temperatures = [0.3, 0.5, 0.7, 0.9, 1.0][:num_agents]

    fixes = []
    with ThreadPoolExecutor(max_workers=num_agents) as executor:
        futures = {
            executor.submit(
                generate_fix,
                i,
                test_name,
                test_file,
                test_source,
                test_output,
                temperatures[i % len(temperatures)],
            ): i
            for i in range(num_agents)
        }

        for future in as_completed(futures):
            try:
                fix = future.result()
                if fix.new_content:
                    fixes.append(fix)
            except Exception:
                pass

    return fixes
