import re
import hashlib
import json
import singer
from tap_kustomer.error import AssertionException

LOGGER = singer.get_logger()

def transform_for_key(this_json, stream_name, endpoint_config, data_key):
    # LOGGER.info("Transforming for stream {} endpoint_config {} data_key {}: ".format(
    #     stream_name, endpoint_config, data_key))
    transformed_json = transform_json(
        this_json, stream_name, endpoint_config, data_key)
    data = []
    if isinstance(transformed_json, dict):
        for record in list(transformed_json.get(data_key, [])):
            data.append(record)
        return data
    return transformed_json


# Convert camelCase to snake_case
def convert(name):
    regsub = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', regsub).lower()


# Convert keys in json array
def convert_array(arr):
    new_arr = []
    for i in arr:
        if isinstance(i, list):
            new_arr.append(convert_array(i))
        elif isinstance(i, dict):
            new_arr.append(convert_json(i))
        else:
            new_arr.append(i)
    return new_arr


# Convert keys in json
def convert_json(this_json):
    out = {}
    if isinstance(this_json, dict):
        for key in this_json:
            new_key = convert(key)
            if isinstance(this_json[key], dict):
                out[new_key] = convert_json(this_json[key])
            elif isinstance(this_json[key], list):
                out[new_key] = convert_array(this_json[key])
            else:
                out[new_key] = this_json[key]
    else:
        return convert_array(this_json)
    return out


def denest(this_json, data_key, denest_keys):
    """Denest by path and key. Moves all elements at key to parent level if
    no target provided. Target provided by dot syntax, e.g. key.target.

    Arguments:
        this_json {[type]} -- [description]
        data_key {[type]} -- [description]
        denest_keys {[type]} -- [description]

    Raises:
        AssertionException: If denested key exists in parent.

    Returns:
        json -- Transformed json with denested keys.
    """
    new_json = this_json
    index = 0
    for record in list(this_json.get(data_key, [])):
        for denest_key in denest_keys.split(","):
            if "." in denest_key:
                denest_targeted_nodes(
                    index, data_key, record, new_json, denest_key)
            else:
                denest_node_all_elements(
                    index, record, denest_key, data_key, new_json)
        index = index + 1
    return new_json


def denest_node_all_elements(index, record, denest_key, data_key, new_json):
    """[summary]

    Arguments:
        index {[type]} -- [description]
        record {[type]} -- [description]
        denest_key {[type]} -- [description]
        data_key {[type]} -- [description]
        new_json {[type]} -- [description]

    Raises:
        AssertionException: [description]
    """
    for key, val in record[denest_key].copy().items():
        if key in new_json[data_key][index].keys():
            raise AssertionException(
                'Denested key {} exists in parent {}'.format(key, new_json[data_key][index]))
        if val == None:
            new_json[data_key][index][key] = ''
        else:
            new_json[data_key][index][key] = val
    new_json[data_key][index].pop(denest_key)


def denest_targeted_nodes(index, data_key, record, new_json, denest_key):
    """[summary]

    Arguments:
        index {[type]} -- [description]
        data_key {[type]} -- [description]
        record {[type]} -- [description]
        new_json {[type]} -- [description]
        denest_key {[type]} -- [description]

    Raises:
        AssertionException: [description]
    """

    target_value = denest_key.split(".")[1]
    if denest_key.split(".")[0] in record:
        target_key = denest_key.split(".")[0]
        for key in record[target_key].copy().keys():
            if isinstance(record[target_key][key], dict) and target_value in record[target_key][key].keys():
                if key in new_json[data_key][index].keys():
                    # raise AssertionException('Denested key {} exists in parent {}'.format(
                    #     key, new_json[data_key][index]))
                    LOGGER.info('Denested key {} exists in parent'.format(key))
                else:
                    new_json[data_key][index][key] = record[target_key][key][target_value].copy()
    new_json[data_key][index].pop(target_key)


def transform_json(this_json, stream_name, endpoint_config, data_key):
    """[summary]

    Arguments:
        this_json {[type]} -- [description]
        stream_name {[type]} -- [description]
        endpoint_config {[type]} -- [description]
        data_key {[type]} -- [description]

    Returns:
        [type] -- [description]
    """

    LOGGER.info("Transforming response for data key {}: stream: {}".format(data_key, stream_name))


    # response = this_json
    converted_json = convert_json(this_json)
    if endpoint_config['denest']:
        LOGGER.info("Denesting for keys {}:".format(endpoint_config['denest']))
        for key in endpoint_config['denest'].split(","):
            denest(converted_json, data_key, key)
    if data_key is not None:
        return converted_json[data_key]
    else:
        return converted_json
