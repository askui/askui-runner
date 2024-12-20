# Need to use _PYTHON_VERSION instead of PYTHON_VERSION because PYTHON_VERSION is a reserved environment variable
ARG _PYTHON_VERSION="3.11"
ARG NODE_VERSION="22"

#########
# BUILD #
#########

# Using slim because other image is in slim
FROM python:${_PYTHON_VERSION}-slim AS builder

RUN pip install -U pip setuptools wheel pdm

COPY pyproject.toml pdm.lock README.md setup.py LICENSE /project/
COPY src/ /project/src

WORKDIR /project
RUN mkdir __pypackages__ && pdm sync --prod --no-editable

#######
# RUN #
#######

# Using slim instead of alpine because there is a manifest for arm as well and is only ~20MB larger
FROM nikolaik/python-nodejs:python${_PYTHON_VERSION}-nodejs${NODE_VERSION}-slim
ARG _PYTHON_VERSION
ARG PYTHONPATH=/project/pkgs

RUN groupadd -r askui && \
    useradd -r -g askui -s /bin/false askui --create-home
# Necessary for cloning (with git) and running (with pdm) vision agent experiments
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -U pdm

COPY --from=builder --chown=askui:askui /project/__pypackages__/${_PYTHON_VERSION}/lib ${PYTHONPATH}
COPY --from=builder --chown=askui:askui /project/__pypackages__/${_PYTHON_VERSION}/bin/* /bin/
    
USER askui

ENV PYTHONPATH=${PYTHONPATH}

ENTRYPOINT ["python", "-m", "askui_runner"]
