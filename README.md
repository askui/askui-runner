# AskUI Runner - Getting Started Guide

Welcome to the first release of the **AskUI Runner**! This guide is designed to walk you through the setup and usage of our new runner. We're thrilled to have you on board!

---

## Table of Contents
1. [Setting up Your Workspace](#setting-up-your-workspace)
2. [Installing the Runner](#installing-the-runner)
3. [Starting the Runner](#starting-the-runner)
4. [Scheduling Runner Jobs](#scheduling-runner-jobs)

---

## Setting up Your Workspace

Before you can dive into using the runner, you'll need to configure your workspace and workflows. Here's how:

1. Navigate to [app-dev.askui.com](https://app-dev.askui.com).
2. If you haven't already, create a new workspace.
3. Ensure that the workspace has sufficient steps remaining for testing.
4. Generate an access token. Keep it handy as you'll need it later.
5. If necessary, set up workflows that you can run on your local machine.

## Installing the Runner

Follow these steps to get the runner installed on your machine:

1. Ensure you have access to the `askui-user-portal` repository. If not, request it.
2. Obtain a Github Personal Access Token (Classic) with repo access.
3. Install Python on your machine. If you're unsure how, check out the installation guide at [pyenv](https://github.com/pyenv/pyenv#installation).
4. Ensure Node.js is already installed on your machine. If not, get it.
5. Install the runner using the following command in your console:

   ```bash
   pip install git+https://<GITHUB_USERNAME>:<GITHUB_PERSONAL_ACCESS_TOKEN>@github.com/askui/askui-user-portal.git@CL-301-pickup-run-jobs#subdirectory=runner


## Starting the Runner

Once you've installed the runner, you'll need to configure and start it:

1. Set up the runner using the provided JSON schema `askui_runner.config_schema.json`.
2. Create a configuration file (either `.json` or `.y{a}ml` format) anywhere on your system. For instance, `askui-runner.config.yml`.

   ```yml
   credentials:
     access_token: <ASKUI ACCESS TOKEN>
     workspace_id: <ASKUI WORKSPACE ID>
   ```

3. Start the runner using the following command, making sure to reference your configuration file:

   ```bash
   python -m runner -c askui-runner.config.yml
   ```

## Scheduling Runner Jobs

With everything set up, you can now schedule jobs for the runner:

1. Download and import the Postman collection from the provided file: `askui-api-gateway-dev-swagger-postman.json`.
2. Create a new schedule using the POST schedules route. You can find detailed instructions in the OpenAPI documentation `askui_scheduling_openapi.yml`.
3. When making API calls, remember to authenticate using the BEARER token. You can find this token within the Chrome Dev Tools:
   - Navigate to **Network** > **Headers**.
   - Look for the **Authorization** header of any AskUI API request (excluding OPTIONS requests).

---

Thanks for choosing **AskUI Runner**. We look forward to receiving your feedback and seeing the amazing workflows you'll create! If you run into any issues or have questions, please reach out to our support team.
