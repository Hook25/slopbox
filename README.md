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
slopbox manifest generate --help
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

### `manifest generate`

The `manifest generate` subcommand analyzes a job and determines whether it requires hardware/firmware features (manifests). It returns a JSON object mapping feature names to descriptions.

```bash
slopbox manifest generate <job_id> [options]
```

**Arguments:**

- `job_id` – The ID of the job to evaluate (required).

**Options:**

- `--job-json <path>` – Path to a JSON file containing job definitions. If omitted, jobs are fetched from `checkbox-cli`.

**Example:**

```bash
# Use checkbox-cli data source
slopbox manifest generate wifi6/detect

# Use a local JSON file
slopbox manifest generate wifi6/detect --job-json jobs.json
```

**Output:**

- If features are detected:
  ```json
  {
    "has_wifi_adapter": "Machine has a wifi adapter",
    "has_wifi6": "Machine supports wifi 6"
  }
  ```
- If no features are needed: `No feature needed for this job.`

## Configuration

By default commands talk to an OpenAI-compatible endpoint at `http://localhost:1234/v1/chat/completions`. You can override this by setting the `OPENAI_ENDPOINT` environment variable.
