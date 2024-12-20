# Need to use _PYTHON_VERSION instead of PYTHON_VERSION because PYTHON_VERSION is a reserved environment variable
ARG _PYTHON_VERSION="3.11"
ARG NODE_VERSION="22"

#########
# BUILD #
#########

FROM python:${_PYTHON_VERSION}-alpine AS builder

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
# Necessary for running vision agent experiments with pdm
RUN pip install -U pdm
 
COPY --from=builder --chown=askui:askui /project/__pypackages__/${_PYTHON_VERSION}/lib ${PYTHONPATH}
COPY --from=builder --chown=askui:askui /project/__pypackages__/${_PYTHON_VERSION}/bin/* /bin/
    
USER askui

ENV PYTHONPATH=${PYTHONPATH}

ENTRYPOINT ["python", "-m", "askui_runner"]
