terraform {
  backend "s3" {
    # This is the default configuration for the dev environment.
    # To use a different environment, run:
    # terraform init -backend-config=environments/<env>/backend.hcl

    # The actual values will be loaded from environments/dev/backend.hcl
    # This is just a placeholder that will be overridden
    bucket         = ""
    key            = ""
    region         = ""
    dynamodb_table = ""
    encrypt        = true
  }
}

# Load the dev backend configuration by default
# This allows running terraform commands directly without specifying the backend config
# To use a different environment, run:
# terraform init -backend-config=environments/<env>/backend.hcl
locals {
  backend_config = fileexists("environments/dev/backend.hcl") ? {
    for line in split("\n", file("environments/dev/backend.hcl")) :
    split(" = ", line)[0] => replace(split(" = ", line)[1], "\"", "")
    if length(split(" = ", line)) == 2 && !startswith(trimspace(line), "#")
  } : {}
}
