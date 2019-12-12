STREAMS = {
    "customers_no_denest": {
        "api_method": "POST",
        "data_key": "data",
        "bookmark_type": "datetime",
        "key_properties": "id",
        "denest": "attributes,relationships.data",
        "params": {},
        "path": "customers/search",
        "body": {
            "and": [
                {"customer_updated_at": {"gte": '{next_date}'}}
            ],
            "sort": [{"customer_updated_at": "asc"}],
            "queryContext": "customer"
        },
        "replication_method": "INCREMENTAL",
        "replication_keys": "updated_at",
        "bookmark_query_field": "customer_updated_at"
    },
    "buckets": {
        "api_method": "GET",
        "data_key": "results",
        "bookmark_type": "datetime",
        "key_properties": "_id",
        "denest": "",
        "params": {},
        "path": "buckets",
        "body": {
        },
        "replication_method": "INCREMENTAL",
        "replication_keys": "updated",
        "bookmark_query_field": "updated"
    },
    "no_denest_no_data_key": {
        "api_method": "GET",
        "data_key": "",
        "bookmark_type": "datetime",
        "key_properties": "_id",
        "denest": "",
        "params": {},
        "path": "abc",
        "body": {
        },
        "replication_method": "FULL_TABLE",
        "replication_keys": "updated",
        "bookmark_query_field": "updated"
    }
}