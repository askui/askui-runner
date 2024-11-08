ARG PYTHON_VERSION=3.10
ARG NODE_VERSION=20

#########
# BUILD #
#########

FROM python:${PYTHON_VERSION}-alpine AS builder
ARG PYTHON_VERSION

RUN pip install -U pip setuptools wheel 
RUN pip install pdm

COPY pyproject.toml pdm.lock README.md setup.py LICENSE /project/
COPY src/ /project/src

WORKDIR /project
RUN mkdir __pypackages__ && pdm sync --prod --no-editable

#######
# RUN #
#######

FROM nikolaik/python-nodejs:python${PYTHON_VERSION}-nodejs${NODE_VERSION}-alpine
ARG PYTHON_VERSION
ARG NODE_VERSION

ENV PYTHONPATH=/project/pkgs
COPY --from=builder /project/__pypackages__/${PYTHON_VERSION}/lib /project/pkgs
COPY --from=builder /project/__pypackages__/${PYTHON_VERSION}/bin/* /bin/

ENTRYPOINT ["python", "-m", "askui_runner"]
