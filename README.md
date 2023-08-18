# askui-runner
Runner for askui Workflows Defined  in askui Studio

AskUI Runner - Getting Started Guide
Welcome to the first release of the AskUI Runner! This guide is designed to walk you through the setup and usage of our new runner. We're thrilled to have you on board!

Table of Contents
Setting up Your Workspace
Installing the Runner
Starting the Runner
Scheduling Runner Jobs
Setting up Your Workspace
Before you can dive into using the runner, you'll need to configure your workspace and workflows. Here's how:

Navigate to app.askui.com.
If you haven't already, create a new workspace.
Ensure that the workspace has sufficient steps remaining for testing.
Generate an access token. Keep it handy as you'll need it later.
If necessary, set up workflows that you can run on your local machine.
Installing the Runner
Follow these steps to get the runner installed on your machine:

Ensure you have access to the askui-user-portal repository. If not, request it.

Obtain a Github Personal Access Token (Classic) with repo access.

Install Python on your machine. If you're unsure how, check out the installation guide at pyenv.

Ensure Node.js is already installed on your machine. If not, get it.

Install the runner using the following command in your console:

bash
Copy code
pip install git+https://<GITHUB_USERNAME>:<GITHUB_PERSONAL_ACCESS_TOKEN>@github.com/askui/askui-user-portal.git@CL-301-pickup-run-jobs#subdirectory=runner
Starting the Runner
Once you've installed the runner, you'll need to configure and start it:

Set up the runner using the provided JSON schema askui_runner.config_schema.json.

Create a configuration file (either .json or .y{a}ml format) anywhere on your system. For instance, askui-runner.config.yml.

Here's a basic configuration template:

yml
Copy code
credentials:
  access_token: <ASKUI ACCESS TOKEN>
  workspace_id: <ASKUI WORKSPACE ID>
Start the runner using the following command, making sure to reference your configuration file:

bash
Copy code
python -m runner -c askui-runner.config.yml
Scheduling Runner Jobs
With everything set up, you can now schedule jobs for the runner:

Download and import the Postman collection from the provided file: askui-api-gateway-dev-swagger-postman.json.
Create a new schedule using the POST schedules route. You can find detailed instructions in the OpenAPI documentation askui_scheduling_openapi.yml.
When making API calls, remember to authenticate using the BEARER token. You can find this token within the Chrome Dev Tools:
Navigate to Network > Headers.
Look for the Authorization header of any AskUI API request (excluding OPTIONS requests).
Thanks for choosing AskUI Runner. We look forward to receiving your feedback and seeing the amazing workflows you'll create! If you run into any issues or have questions, please reach out to our support team.
