import json
import pytest
import singer
from tap_kustomer.transform import denest
from tap_kustomer.tests.denest_nodes_data import *
from tap_kustomer.error import AssertionException

LOGGER = singer.get_logger()


def test_denest_nodes():
    """Test that requests nodes are denested. Test that individual node child denested as 
       referenced by dot notation. 
    """
    transformed_data = denest(
        NESTED_VALID_DICTS, 'data', 'attributes,relationships.data')
    assert not (any('attributes' in data for data in transformed_data))
    assert not (any('relationships' in data for data in transformed_data))
    assert '5a79d3e2c8b66e0001ba953e' == transformed_data['data'][0]['org']['id']


def test_denest_nodes_invalid():
    """Test that exception is raised for denesting keys which pre-existence in parent."""
    with pytest.raises(AssertionException) as e:
        assert denest(NESTED_INVALID_DICTS, 'data', 'attributes')
    assert "Denested key displayName exists in parent" in str(e.value)
