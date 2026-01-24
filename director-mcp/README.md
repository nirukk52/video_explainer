# Director MCP - Varun Mayya-Style Short-Form Video Planning

An MCP server that provides AI-powered tools for creating high-retention short-form videos.

## Skills

### 1. `director_plan_short` - Ultra-Tight Visual Storytelling
Transform any topic into a 15-60 second script with proof beats.

```json
{
  "topic": "DeepSeek's pricing is crashing the AI market",
  "style": "varun_mayya",
  "duration_seconds": 45,
  "evidence_urls": ["https://deepseek.com/pricing"]
}
```

### 2. `director_analyze_hook` - Hook & Loop Instincts
Evaluate and improve the first 3 seconds of a script.

```json
{
  "script_json": "{...}",
  "scene_id": 1
}
```

### 3. `director_generate_beats` - Stakes-Rising Structure
Break a script into 5-7 second visual beats with escalating stakes.

```json
{
  "script_json": "{...}",
  "beat_interval_seconds": 5
}
```

### 4. `director_validate_retention` - Retention Engineering
Score a script's retention potential and flag drop-off risks.

```json
{
  "script_json": "{...}",
  "target_retention_pct": 70
}
```

## Installation

```bash
cd director-mcp
pip install -r requirements.txt
```

## Usage

### stdio transport (local)
```bash
python -m src.server
```

### HTTP transport (remote)
```bash
python -m src.server --http --port 8001
```

### Test with MCP Inspector
```bash
npx @modelcontextprotocol/inspector python -m src.server
```

## Environment Variables

```bash
OPENAI_API_KEY=sk-...  # Required for LLM calls
```

## Varun Mayya Style Rules

1. **Hook in 3 seconds**: Bold claim with specific number
2. **Evidence-first**: Every claim has visual proof
3. **Stakes escalation**: Each beat raises stakes
4. **Max 20 words**: Per voiceover segment
5. **Visual change**: Every 2-4 seconds
