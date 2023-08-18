ARG BASE_IMAGE
ARG PROJECT_NAME=runner
ARG PYTHON_VERSION_MAJOR=3
ARG PYTHON_VERSION_MINOR=10
ARG PYTHON_VERSION_PATCH=12
ARG PYTHON_VERSION=${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}

#############
# BUILD APP #
#############
FROM python:${PYTHON_VERSION} AS builder

ARG PROJECT_NAME

ENV ROOT=/src

RUN mkdir -p $ROOT

WORKDIR $ROOT

RUN pip install -U pip setuptools wheel 
RUN pip install pdm

COPY pyproject.toml pdm.lock README.md ./
COPY src/${PROJECT_NAME} ./${PROJECT_NAME}

RUN mkdir __pypackages__ && pdm sync --clean --prod --no-editable

###########
# RUN APP #
###########

FROM ${BASE_IMAGE}

ARG PROJECT_NAME
ARG PYTHON_VERSION_MAJOR
ARG PYTHON_VERSION

USER root

ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get -y dist-upgrade \
    && wget -O- https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y build-essential nodejs \
    && apt-get clean

################
# SETUP PYTHON #
################

RUN apt update \
    && apt upgrade -y \
    && apt install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION_MAJOR}-pip

#############
# SETUP APP #
#############

USER askui
ENV ROOT=/home/askui

RUN mkdir -p $ROOT

WORKDIR $ROOT

ENV PYTHONPATH=${ROOT}/pkgs
COPY --from=builder /src/__pypackages__/${PYTHON_VERSION}/lib ${PYTHONPATH}

####################
# SETUP ENTRYPOINT #
####################

COPY entrypoint.sh /entrypoint.sh
