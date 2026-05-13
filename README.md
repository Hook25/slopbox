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

By default the command talks to an OpenAI-compatible endpoint at `http://localhost:1234/v1/chat/completions`. You can override this by setting the `OPENAI_ENDPOINT` environment variable.
If your server requires a specific `model` name in the request body, set the `OPENAI_MODEL` environment variable. When unset, the request is sent without a `model` key.

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
