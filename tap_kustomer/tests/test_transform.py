import json
import pytest
import re
import singer
from tap_kustomer.transform import denest
from tap_kustomer.transform import transform_json
from tap_kustomer.transform import transform_for_key
from tap_kustomer.tests.denest_nodes_data import *
from tap_kustomer.tests.stream_configs import STREAMS
from tap_kustomer.error import AssertionException

LOGGER = singer.get_logger()


def key_iterator_assert_no_snake(data):
    """Asserts no snake case in nested list or dictionary
    """
    pattern = '([a-z0-9])([A-Z])'

    if isinstance(data, list):
        for object in data:
            if isinstance(object, dict):
                key_iterator_assert_no_snake(object)
    elif isinstance(data, dict):
        for key, value in list(data.items()):
            if isinstance(value, dict):
                key_iterator_assert_no_snake(value)
                assert not (re.search(pattern, key))


def test_transform():
    """Test snake to camel transformation.
    """
    transformed_data = transform_json(NESTED_VALID_DICTS,
                                      STREAMS.get('customers_no_denest'),
                                      'data')
    key_iterator_assert_no_snake(transformed_data)


def test_transform_camel():
    transformed_data = transform_for_key(NESTED_VALID_DICTS,
                                         STREAMS.get('customers_no_denest'),
                                         'data')
    key_iterator_assert_no_snake(transformed_data)


def test_transform_for_key_dict_list():
    transformed_data = transform_for_key(DICTIONARY_LIST,
                                         STREAMS.get('customers_no_denest'),
                                         '')
    key_iterator_assert_no_snake(transformed_data)


def test_denest_nodes():
    """Test that requests nodes are denested. Test that individual node child denested as 
       referenced by dot notation. Assert duplicate keys for 'sla' in multiple nodes 
       denested with second renamed 'sla_data'.
    """
    transformed_data = denest(NESTED_VALID_DICTS, 'data',
                              'attributes,relationships.data')
    assert not (any('attributes' in data for data in transformed_data))
    assert not (any('relationships' in data for data in transformed_data))
    assert '5a79d3e2c8b66e0001ba953e' == transformed_data['data'][0]['org'][
        'id']
    assert 'sla_data' in transformed_data['data'][0]
    assert transformed_data['data'][0]['sla_data'][
        'id'] == '5a7b6d7067cd0a00013a7982'
    assert 'sla' in transformed_data['data'][0]
    assert 'matchedAt' in transformed_data['data'][0]['sla']
