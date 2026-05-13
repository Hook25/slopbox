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
slopbox submission --help
slopbox submission bugs --help
slopbox submission results --help
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

### `submission results`

The `submission results` subcommand fetches test results from the C3 API.

```bash
slopbox submission results <submission_id>
```

**Arguments:**

- `submission_id` – The submission ID to query (required).

**Environment variables:**

- `C3_ACCESS_TOKEN` – Required. Bearer token used to authenticate with the C3 API.

**Example:**

```bash
C3_ACCESS_TOKEN="<your-token>" slopbox submission results 486444
```
### `submission bugs`

The `submission bugs` subcommand fetches bugs from a Launchpad project.

```bash
slopbox submission bugs <launchpad_project>
```

**Arguments:**

- `launchpad_project` – Launchpad project name to query (required).

**Options:**

- `--milestones <names>` – Comma-separated list of milestone names to filter by. If omitted, all bugs are returned.

**Example:**

```bash
# All bugs in a project
slopbox submission bugs checkbox

# Bugs filtered by milestone
slopbox submission bugs my-project --milestones alpha,beta
```

**Authentication:**

This command requires you to be authenticated to Launchpad. If you haven't authenticated before, run `lp-shell` once to cache your OAuth credentials, then try again.

## Configuration

By default commands talk to an OpenAI-compatible endpoint at `http://localhost:1234/v1/chat/completions`. You can override this by setting the `OPENAI_ENDPOINT` environment variable.
If your server requires a specific `model` name in the request body, set the `OPENAI_MODEL` environment variable. When unset, the request is sent without a `model` key.
