# askui-runner

Runner for Workflows Defined in AskUI Studio.

<p align="center">
  <img src="askui-runner-simple-architecture.png" width="80%" alt="Architecture drawing how the AskUI-Runner fits into AskUI Studio, AskUI SDK and AskUI Remote Device Controller. The AskUI-Runner fetches Workflows from AskUI Studio and uploads the results back to it. The Runner uses the AskUI SDK which passes the instructions from the workflow steps to the AskUI Remote Device Controller.">
</p>

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Requirements

- Python 3.10 or higher
- Node.js 16 or higher

## Installation

We recommend using a virtual environment for Python. Make sure `python --version` returns 3.10 or higher:

```bash
python -m venv venv
source venv/bin/activate
```

We have not yet published the AskUI Runner to PyPI. For now, you can install it directly from GitHub:

```bash
pip install git+https://github.com/askui/askui-runner.git
```

Currently, the standard logging output of the AskUI runner is minimal - we are soon going to change that. But you should see the runner starting the running of workflows as soon as you schedule some runs through the AskUI Studio.

## Usage

Create a configuration file (`.y{a}ml` or `.json`) in a directory of your choosing. The configuration file should contain at least some credentials and the command with which you start the runner without the config file flag:

```yml
runner:
  exec: python -m askui_runner # update if your command is different
  tags: [<tag 1>, <tag 2>, ..] # replace with your own runner tags
queue:
  api_url: https://workspaces.askui.com/api/v1/runner-jobs
  credentials:
    workspace_id: <workspace id> # replace with your workspace id
    access_token: <access token> # replace with your access token
```

See [Generating up-to-date Configuration Schema](#generating-up-to-date-configuration-schema)

Start the runner using

```bash
python -m askui_runner start -c <path to your config file, e.g., askui-runner.config.yaml>
```

## Start UiController

If you want to run your workflows on the same system as the runner you need to start an UiController that listens on port `6769`. Please download the one for your operating system and start it:

- For Windows please use our AskUI Installer: [Windows Getting Started](https://docs.askui.com/docs/general/Getting%20Started/Installing%20AskUI/getting-started)
- [Linux](https://files.askui.com/releases/askui-ui-controller/latest/linux/x64/askui-ui-controller.AppImage)

> ℹ️ **macOS** After installation to `Applications` remove the quarantine flag with the following command run from a terminal: `xattr -d com.apple.quarantine /Applications/askui-ui-controller.app`

- [macOS(intel)](https://files.askui.com/releases/askui-ui-controller/latest/darwin/x64/askui-ui-controller.dmg)
- [macOS(silicon)](https://files.askui.com/releases/askui-ui-controller/latest/darwin/arm64/askui-ui-controller.dmg)

### Execute Workflows on a Remote System: Change UiController URL

You can change the UiController-URL so the runner can talk to a UiController that runs on a remote machine or on a different port:

```yml
...
runner:
  ...
  controller:
    host: "127.0.0.1"
    port: 7000
```

## Generating up-to-date Configuration Schema

Requirements:

- [PDM](https://pdm.fming.dev/latest/) 2.8 or higher for contributing and creating the JSON schema of the config

Find out about all configuration options by taking a look at the JSON schema of the configuration. You can generate an up-to-date JSON schema by cloning this repository and running the following commands.

```bash
## Install and initialize pdm
pip install pdm
pdm install

pdm run python -m scripts.generate_config_schema_json
```

## AskUI Agents

### Sync

The Agent sync command helps sync agent files between local and remote storage. You can specify the direction (up or down) for syncing and control other sync options.

```bash
python -m askui_runner agent sync <parameters>
```

- Parameters:
  - `--config`: Path to your config file in .json, .yaml, or .yml format or a raw JSON config.
  - direction: The direction of the sync:
    - `down`: Sync files from remote storage to local.
    - `up`: Sync files from local storage to remote.
  - `--dry`: Display the operations that would be performed without executing them.
  - `--delete`: Delete files not found in the source of truth during sync.
  - `--help`: Display the help message.
  
example:

```bash
# Sync agent files from remote storage to local in dry-run mode.
python -m askui_runner agent sync down --config askui-runner.config.yaml --dry
```

#### Sync Configuration

The sync command requires a configuration file to be passed in. The configuration file should contain the following fields:

```json
{
  "credentials": {
    "workspace_id": "<workspace_id>",
    "access_token": "<access_token>"
  }
}
```

To display the configuration schema, run the following command:

```bash
python -m askui_runner agent print-config-schema
```

### Logging Configuration

You can configure the logging behavior of the AskUI Runner through environment variables:

```bash
# Set logging level
export ASKUI_RUNNER__LOG__LEVEL=INFO # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Set custom log format
export ASKUI_RUNNER__LOG__FORMAT="%(asctime)s - %(levelname)s - %(message)s"
```

The default logging level is `INFO` and the default format is `%(asctime)s - %(levelname)s - %(message)s`. The log format is a [Python logging format string](https://docs.python.org/3/library/logging.html). Check the link for more information on how to customize the log format and which attributes, e.g., `asctime` and `levelname`, are available.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository.
2. Create a new branch: `git checkout -b your-feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push the branch: `git push origin your-feature-name`
5. Submit a pull request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
