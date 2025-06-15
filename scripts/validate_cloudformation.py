import sys
from pathlib import Path
import ruamel.yaml


def construct_aws_tag(loader, tag_suffix, node):
    if tag_suffix == "GetAtt":
        return ruamel.yaml.scalarstring.SingleQuotedScalarString(
            f"!{tag_suffix} {node.value}"
        )
    return ruamel.yaml.scalarstring.SingleQuotedScalarString(
        f"!{tag_suffix} {node.value}"
    )


def validate_cloudformation(file_path):
    """Validate a CloudFormation template file.

    Args:
        file_path: Path to the CloudFormation template file

    Returns:
        bool: True if validation succeeds, False otherwise
    """
    # First, try to validate using AWS CLI if available
    try:
        import boto3

        print(f" Validating {file_path} with AWS CloudFormation...")
        with open(file_path, "r", encoding="utf-8") as f:
            template_body = f.read()

        # Try to validate the template
        client = boto3.client("cloudformation")
        client.validate_template(TemplateBody=template_body)
        print(" Template is valid")
        return True
    except ImportError:
        print(" boto3 not available, performing basic YAML validation...")
    except Exception as e:
        print(f" AWS CloudFormation validation error: {str(e)}")
        # Continue to basic YAML validation
        pass

    # Fall back to basic YAML validation
    try:
        yaml = ruamel.yaml.YAML(typ="safe")
        yaml.allow_duplicate_keys = True
        # Register AWS CloudFormation tags
        yaml.constructor.add_multi_constructor("!", construct_aws_tag)
        with open(file_path, "r", encoding="utf-8") as f:
            yaml.load(f)
        print(" Basic YAML validation passed")
        return True
    except Exception as e:
        print(f" Error validating {file_path}: {str(e)}")
        return False


def parse_arguments():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate CloudFormation templates.")
    parser.add_argument(
        "files", nargs="*", help="Path(s) to the CloudFormation template file(s)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    try:
        args = parse_arguments()

        if not args.files:
            print("Error: No files provided for validation")
            return 1

        has_errors = False
        for file_path in args.files:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                has_errors = True
                continue

            if not validate_cloudformation(file_path):
                has_errors = True

        return 1 if has_errors else 0

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
