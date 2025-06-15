plugin "aws" {
  enabled = true
  version = "0.31.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# Configure core rules
rule "terraform_comment_syntax" { enabled = true }
rule "terraform_deprecated_index" { enabled = true }
rule "terraform_deprecated_interpolation" { enabled = true }
rule "terraform_documented_outputs" { enabled = true }
rule "terraform_documented_variables" { enabled = true }
rule "terraform_module_pinned_source" {
  enabled = true
  style = "semver"
}
rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"
}
rule "terraform_standard_module_structure" { enabled = true }
rule "terraform_typed_variables" { enabled = true }
rule "terraform_unused_required_providers" { enabled = true }

# Configure required providers check
rule "terraform_required_providers" {
  enabled = true
  # Don't require version constraints
  require_version_constraint = false
}

# Configure required version check
rule "terraform_required_version" {
  enabled = true
  # Don't require required_version
  require_version = false
}

# Configure unused declarations
rule "terraform_unused_declarations" {
  enabled = true

  # Ignore .terraform directory
  ignore_module = [".terraform/*"]

  # Ignore unused variables in modules
  ignore_module_unused_variables = true

  # Ignore unused locals
  ignore_unused_locals = true

  # Ignore unused variables
  ignore_unused_variables = true

  # Ignore unused variables in the root module
  ignore_variable = {
    source = true
  }

  # Ignore unused locals in the root module
  ignore_locals = {
    source = true
  }
}

# AWS specific rules
rule "aws_instance_invalid_type" { enabled = true }
rule "aws_instance_previous_type" { enabled = true }

# Ignore rules that are too strict for our use case
rule "aws_resource_missing_tags" { enabled = false }
rule "aws_resource_missing_required_tags" { enabled = false }
rule "aws_iam_policy_document_gov_friendly_arns" { enabled = false }

# Configure module handling
config {
  call_module_type = "all"
  force = false
}
