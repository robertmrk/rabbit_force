# build stage for installing all dependencies and for building wheels
FROM python:3.7.3-alpine3.9 AS build

# required pipenv version
ARG RF_PIPENV_VERSION=2018.11.26

# change the working directory
WORKDIR /build

# copy the Pipfiles from the build context
COPY Pipfile Pipfile.lock ./

# install compilers and build tools
RUN apk add --no-cache build-base && \
    # install pipenv
    pip install --no-cache-dir "pipenv==${RF_PIPENV_VERSION}" && \
    # install dependencies from the lock file,
    # create the virtual enviroment in the working directory
    sh -c "PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --ignore-pipfile" && \
    rm Pipfile Pipfile.lock


# final build stage
FROM python:3.7.3-alpine3.9

# user and group configuration
ARG USER_NAME=rabbit_force
ARG GROUP_NAME=rabbit_force
ARG USER_ID=1000
ARG GROUP_ID=1000

# create a user and group
RUN addgroup -g ${GROUP_ID} ${GROUP_NAME} && \
    adduser -D -H -G ${GROUP_NAME} -u ${USER_ID} ${USER_NAME}

# change the working directory
WORKDIR /app

# copy the contents of the working directory from the build stage
COPY --from=build /build /app
# copy the application package from the build context
COPY rabbit_force ./rabbit_force

# set the current user and group
USER ${USER_NAME}:${GROUP_NAME}

# execute the application using the virtual enviroment
ENTRYPOINT [".venv/bin/python", "-m", "rabbit_force"]
