import os
import glob
import argparse
from typing import List

from . import util
from .template import Template
from .json_validation import load_and_validate_schema
from .constants import SCHEMA_DIR


def main():
    args = interface()
    args.func(args)


def interface() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # Print out usage if no subcommands provided
    parser.set_defaults(func=lambda _: parser.print_usage(None))

    # Option to list available schemas
    list_parser = subparsers.add_parser(
        'list', help='List all available schemas')
    list_parser.set_defaults(func=lambda _: list_schemas())

    # Parser for template generation
    generate_parser = subparsers.add_parser(
        'generate_template', help='Create shipping manifest excel template from manifest configuration file')
    generate_parser.add_argument('-m', '--manifest_file',
                                 help='Path to yaml file containing template configuration', required=True)
    generate_parser.add_argument('-s', '--schemas_dir',
                                 help='Path to directory containing data entity schemas', required=False)
    generate_parser.add_argument(
        '-o', '--out_file', help='Where to write the resulting excel template', required=True)
    generate_parser.set_defaults(func=generate_template)

    # Parser for validating an excel template
    template_parser = subparsers.add_parser(
        'validate_template', help='Validate a populated excel template based on the given configuration files')
    template_parser.add_argument('-m', '--manifest_file',
                                 help='Path to yaml file containing template configuration', required=True)
    template_parser.add_argument('-s', '--schemas_dir',
                                 help='Path to directory containing data entity schemas')
    template_parser.add_argument('-x', '--xlsx_file', )
    template_parser.set_defaults(func=validate_template)

    # Parser for validation a JSON schema
    schema_parser = subparsers.add_parser(
        'validate_schema', help='Validate a JSON schema.')
    schema_parser.add_argument('-s', '--schemas_dir',
                               help='Path to the directory containing data entity schemas')
    schema_parser.add_argument('-f', '--schema_file',
                               help='Path to the schema file to validate', required=True)
    schema_parser.set_defaults(func=validate_schema)

    # Parser for schema file format conversion
    conversion_parser = subparsers.add_parser(
        'convert', help='Convert a yaml file to a json file, or vice versa')
    conversion_parser.add_argument(
        '--to_json', help='Path to yaml file to convert to json')
    conversion_parser.add_argument(
        '--to_yaml', help='Path to json file to convert to yaml')
    conversion_parser.set_defaults(func=convert)

    return parser.parse_args()


def list_schemas():
    for path in glob.glob(f'{SCHEMA_DIR}/**/*.json', recursive=True):
        print(path.replace(SCHEMA_DIR + '/', ''))


def get_schemas_dir(schemas_dir) -> str:
    return os.path.abspath(schemas_dir) if schemas_dir else SCHEMA_DIR


def build_manifest(args: argparse.Namespace) -> Template:
    schemas_dir = get_schemas_dir(args.schemas_dir)
    return Template.from_json(args.manifest_file, schemas_dir)


def generate_template(args: argparse.Namespace):
    manifest = build_manifest(args)
    manifest.to_excel(args.out_file)


def validate_template(args: argparse.Namespace):
    manifest = build_manifest(args)
    is_valid = manifest.validate_excel(args.xlsx_file)
    if is_valid:
        print(f'{args.xlsx_file} is valid with respect to {args.manifest_file}')


def validate_schema(args: argparse.Namespace):
    abs_schemas_dir = get_schemas_dir(args.schemas_dir)
    success = load_and_validate_schema(args.schema_file, abs_schemas_dir)
    if success:
        print(f'{args.schema_file} is valid')


def convert(args: argparse.Namespace):
    if args.to_json:
        json_file = util.yaml_to_json(args.to_json)
        print(f'Wrote {args.to_json} as json to {json_file}')
    elif args.to_yaml:
        yaml_file = util.json_to_yaml(args.to_yaml)
        print(f'Wrote {args.to_yaml} as yaml to {yaml_file}')


if __name__ == '__main__':
    main()
