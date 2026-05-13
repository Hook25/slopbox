# slopbox

Slop produced during Canonical Hackaton

## Running the tool

`slopbox` is installed as a console script. After installing the package (e.g. with `uv pip install -e .` or `pip install -e .`), run it from the terminal:

```bash
slopbox <command>
```

Use `--help` to see available commands and options:

```bash
slopbox --help
slopbox manifest --help
slopbox manifest assign --help
```

### `manifest assign`

The `manifest assign` subcommand classifies a Checkbox job against manifest tags using an LLM.

```bash
slopbox manifest assign <job_id> [options]
```

**Arguments:**

- `job_id` – The ID of the job to classify (required).

**Options:**

- `--manifest-json <path>` – Path to a JSON file containing manifest entries. If omitted, manifests are fetched from `checkbox-cli`.
- `--job-json <path>` – Path to a JSON file containing job definitions. If omitted, jobs are fetched from `checkbox-cli`.

**Example:**

```bash
# Use checkbox-cli data sources
slopbox manifest assign ethernet/detect

# Use local JSON files
slopbox manifest assign ethernet/detect \
    --manifest-json manifests.json \
    --job-json jobs.json
```

By default the command talks to an OpenAI-compatible endpoint at `http://localhost:1234/v1/chat/completions`. You can override this by setting the `OPENAI_ENDPOINT` environment variable.  
The default model sent in requests is `gpt-3.5-turbo`. If your server requires a specific model name (e.g. `Gemma-4-E4B-it-GGUF`), set the `OPENAI_MODEL` environment variable.
