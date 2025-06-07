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
    try:
        yaml = ruamel.yaml.YAML(typ="safe")
        yaml.allow_duplicate_keys = True
        # Register AWS CloudFormation tags
        yaml.constructor.add_multi_constructor("!", construct_aws_tag)
        with open(file_path, "r") as f:
            yaml.load(f)
        return True
    except Exception as e:
        print(f"Error validating {file_path}: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_cloudformation.py <file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    if not validate_cloudformation(file_path):
        sys.exit(1)
