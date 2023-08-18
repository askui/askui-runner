#!/bin/bash

version=$1
if [ -z "${version}" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi
echo "Building version ${version}"

dockerfile_path="docker/Dockerfile"

if [ ! -f "$dockerfile_path" ]; then
    echo "This script must be run from the root of the repository."
    exit 1
fi

tag="askuigmbh/askui-runner:latest"
versioned_tag="askuigmbh/askui-runner:${version}"
docker pull "${tag}"
docker build \
    --cache-from "${tag}" \
    --build-arg BASE_IMAGE="askuigmbh/askui-ui-controller:v0.11.2-chrome-100.0.4896.60-amd64" \
    -f "$dockerfile_path" \
    -t "${versioned_tag}" .
docker tag "${versioned_tag}" "${tag}"
docker push "${versioned_tag}"
docker push "${tag}"
