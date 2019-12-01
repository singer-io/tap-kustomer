from tap_kustomer.error import AssertionException


def denest(this_json, data_key, denest_keys):
    """Denest by path and key. Moves all elements at key to parent level if no target provided. 
    Target provided by dot syntax, e.g. key.target.
    
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
    i = 0
    for record in list(this_json.get(data_key, [])):
        for denest_key in denest_keys.split(","):
            if "." in denest_key:
                target_value = denest_key.split(".")[1]
                if denest_key.split(".")[0] in record:
                    target_key = denest_key.split(".")[0]
                    for key, val in record[target_key].copy().items():
                        if target_value in record[target_key][key].keys():
                            if key in new_json[data_key][i].keys():
                                raise AssertionException(
                                    'Denested key {} exists in parent {}'.format(key, new_json[data_key][i]))
                            new_json[data_key][i][key] = record[target_key][key][target_value].copy(
                            )
                    new_json[data_key][i].pop(target_key)
            else:
                for key, val in record[denest_key].copy().items():
                    if key in new_json[data_key][i].keys():
                        raise AssertionException(
                            'Denested key {} exists in parent {}'.format(key, new_json[data_key][i]))
                    new_json[data_key][i][key] = val
                new_json[data_key][i].pop(denest_key)
        i = i + 1

    return new_json


def transform_json(this_json, stream_name, endpoint_config, data_key):

    new_json = this_json

    for key in endpoint_config['denest'].split(","):
        denested_json = denest(new_json, data_key, key)
        new_json = denested_json
        if data_key in new_json:
            return new_json[data_key]
        else:
            return new_json
