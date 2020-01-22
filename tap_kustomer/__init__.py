# coding: utf-8

__author__ = 'Scott Coleman'
__email__ = 'scott.coleman@bytecode.io'

import sys
import json
import argparse
import singer
from singer import metadata, utils
from tap_kustomer.client import KustomerClient
from tap_kustomer.discover import discover
from tap_kustomer.sync import sync

LOGGER = singer.get_logger()

REQUIRED_CONFIG_KEYS = [
    'api_token',
    'start_date',
]


def do_discover():

    LOGGER.info('Starting discover')
    catalog = discover()
    json.dump(catalog.to_dict(), sys.stdout, indent=2)
    LOGGER.info('Finished discover')


@singer.utils.handle_top_exception(LOGGER)
def main():

    parsed_args = singer.utils.parse_args(REQUIRED_CONFIG_KEYS)

    with KustomerClient(parsed_args.config['api_token'],
                        parsed_args.config['user_agent']) as client:

        state = {}
        if parsed_args.state:
            state = parsed_args.state

        if parsed_args.discover:
            do_discover()
        elif parsed_args.catalog:
            sync(client=client,
                 config=parsed_args.config,
                 catalog=parsed_args.catalog,
                 state=state)


if __name__ == '__main__':
    main()
