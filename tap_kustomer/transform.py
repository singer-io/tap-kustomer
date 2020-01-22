import re
import singer

LOGGER = singer.get_logger()


def transform_for_key(this_json, endpoint_config, data_key):
    transformed_json = transform_json(this_json, endpoint_config,
                                      data_key)
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


def denest_node_all_elements(index, record, denest_key, data_key, new_json):
    for key, val in record[denest_key].items():
        new_json[data_key][index][key] = val
    new_json[data_key][index].pop(denest_key)


def denest_targeted_nodes(index, data_key, record, new_json, denest_key):
    """Denest element in child. denest key in dot notation where prefix
    is node to denest and postfix is the object which becomes the value.
    Changes any node named 'sla' to 'sla_data' to prevent collision from
    denested as key name already known to exist in another node.

    Arguments:
        index {[type]} -- index of record in response
        record {[type]} -- the record
        denest_key {[type]} -- key to denest
        data_key {[type]} -- data path in response
        new_json {[type]} -- json to denest
    """

    target_key = denest_key.split(".")[0]
    target_value = denest_key.split(".")[1]
    if target_key in record:
        for key in record[target_key].copy().keys():
            if isinstance(
                    record[target_key][key],
                    dict) and target_value in record[target_key][key].keys():
                # Transform sla keyname if exists
                if key == 'sla':
                    new_key = key + "_" + target_value
                    new_json[data_key][index][new_key] = record[target_key][
                        key][target_value].copy()
                else:
                    new_json[data_key][index][key] = record[target_key][key][
                        target_value].copy()
    new_json[data_key][index].pop(target_key)


def denest(this_json, data_key, denest_keys):
    """Denest by path and key. Moves all elements at key to parent level if
    no target provided. Target provided by dot syntax, e.g. key.target. If
    target exists node is taken as value for key.

    Arguments:
        this_json {[type]} -- JSON to denest
        data_key {[type]} -- Path to data in JSON
        denest_keys {[type]} -- Keys to denest

    Returns:
        json -- Transformed json with denested keys.
    """
    new_json = this_json
    index = 0
    for record in list(this_json.get(data_key, [])):
        for denest_key in denest_keys.split(","):
            if "." in denest_key:
                denest_targeted_nodes(index, data_key, record, new_json,
                                      denest_key)
            else:
                denest_node_all_elements(index, record, denest_key, data_key,
                                         new_json)
        index = index + 1
    return new_json


def transform_json(this_json, endpoint_config, data_key):
    converted_json = convert_json(this_json)
    if 'denest' in endpoint_config:
        for key in endpoint_config.get('denest', []):
            denest(converted_json, data_key, key)
    if data_key:
        return converted_json[data_key]
    return converted_json
