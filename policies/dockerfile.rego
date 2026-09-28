package main

deny contains msg if {
    some i
    input[i].Cmd == "user"
    user := lower(input[i].Value[0])
    regex.match(`^(root(:.*)?|0(:.*)?)$`, user)

    msg := "Container must not run as root"
}

deny contains msg if {
    some i
    input[i].Cmd == "from"
    endswith(lower(input[i].Value[0]), ":latest")

    msg := "Base images must not use the latest tag"
}

deny contains msg if {
    some i
    input[i].Cmd == "from"

    lower(input[i].Value[0]) != "python:3.12-slim"

    msg := "Dockerfile must use the approved base image: python:3.12-slim"
}

deny contains msg if {
    count([i | input[i].Cmd == "user"]) == 0

    msg := "Dockerfile must explicitly define a non-root USER"
}

has_active_healthcheck if {
    some i
    input[i].Cmd == "healthcheck"
    count(input[i].Value) > 1
    lower(input[i].Value[0]) != "none"
}

deny contains msg if {
    not has_active_healthcheck

    msg := "Dockerfile must define a HEALTHCHECK"
}

deny contains msg if {
    count([i | input[i].Cmd == "workdir"]) == 0

    msg := "Dockerfile must explicitly define a WORKDIR"
}

# Prevent common local secrets and repository metadata from entering the image.
deny contains msg if {
    some i
    input[i].Cmd in {"copy", "add"}
    count(input[i].Value) > 1
    some j
    j < count(input[i].Value) - 1
    source := lower(input[i].Value[j])
    some component in split(source, "/")
    component in {".git", ".env", ".ssh"}

    msg := "COPY/ADD must not include .git, .env, or .ssh paths"
}

# Only inspect secret-like assignments in ENV/ARG; placeholders and variable references are allowed.
deny contains msg if {
    some i
    input[i].Cmd in {"env", "arg"}
    some j
    j < count(input[i].Value) - 1
    key := lower(input[i].Value[j])
    regex.match(`(^|_)(password|passwd|secret|token|api[_-]?key|private[_-]?key)$`, key)
    value := input[i].Value[j + 1]
    value != "="
    not regex.match(`(?i)^(\$\{?[a-z_][a-z0-9_]*\}?|<[^>]+>|changeme|change_me|replace[_-]?me|your[_-].+|example|password|secret|token)$`, value)

    msg := "Do not hardcode secret values in Dockerfile ENV or ARG instructions"
}