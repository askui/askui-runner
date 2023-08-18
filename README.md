# askui-runner

Runner for Workflows Defined in AskUI Studio

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Requirements

- Python 3.10 or higher
- Node.js 16 or higher
- [PDM](https://pdm.fming.dev/latest/) 2.8 or higher for contributing and creating the JSON schema of the config

## Installation

We have not yet published the AskUI Runner to PyPI. For now, you can install it directly from GitHub:

```bash
pip install git+https://github.com/askui/askui-runner.git
```

## Usage

Create a configuration file (`.y{a}ml` or `.json`) in a directory of your choosing. The configuration file should contain at least some credentials and the command with which you start the runner without the config file flag:

```yml
credentials:
  workspace_id: <workspace id> # replace with your workspace id
  access_token: <access token> # replace with your access token
runner:
  exec: python -m askui_runner # update if your command is different
```

Find out about all configuration options by taking a look at the JSON schema of the configuration. You can generate an up-to-date JSON schema by running:

```bash
pdm run python -m scripts.generate_config_schema_json
```

Start the runner using

```bash
python -m askui_runner -c <path to your config file, e.g., askui-runner.config.yaml>
```

Currently, the standard logging output of the AskUI runner is minimal - we are soon going to change that. But you should see the runner starting the running of workflows as soon as you schedule some runs through the AskUI Studio.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository.
2. Create a new branch: `git checkout -b your-feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push the branch: `git push origin your-feature-name`
5. Submit a pull request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
