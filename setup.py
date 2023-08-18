from setuptools import setup

setup(
    data_files=[
        (
            "src/askui_runner/project_template",
            [
                "src/askui_runner/project_template/package-lock.json",
                "src/askui_runner/project_template/package.json",
                "src/askui_runner/project_template/tsconfig.json",
                "src/askui_runner/project_template/helper/jest.setup.ts.jinja",
                "src/askui_runner/project_template/jest.config.ts.jinja",
            ],
        ),
    ]
)
