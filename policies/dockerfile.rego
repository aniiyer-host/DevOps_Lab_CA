package main

deny contains msg if {
    some i
    input[i].Cmd == "user"
    lower(input[i].Value[0]) == "root"

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

    not startswith(lower(input[i].Value[0]), "python:3.12-slim")

    msg := "Dockerfile must use the approved base image: python:3.12-slim"
}

deny contains msg if {
    count([i | input[i].Cmd == "user"]) == 0

    msg := "Dockerfile must explicitly define a non-root USER"
}