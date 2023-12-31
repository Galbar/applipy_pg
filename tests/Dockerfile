ARG PY_VERSION
FROM python:$PY_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl wget \
    ca-certificates \
    apt-transport-https \
    gnupg-agent \
    software-properties-common

# Install docker
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | \
    gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/debian $(lsb_release -cs) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    docker-ce  \
    docker-ce-cli
