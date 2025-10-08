
# streams: API URL endpoints to be called
# properties:
#   <root node>: Plural stream name for the endpoint
#   path: API endpoint relative path, when added to the base URL, creates the full path,
#       default = stream_name
#   key_properties: Primary key fields for identifying an endpoint record.
#   replication_method: INCREMENTAL or FULL_TABLE
#   replication_keys: bookmark_field(s), typically a date-time, used for filtering the results
#        and setting the state
#   params: Query, sort, and other endpoint specific parameters; default = {}
#   data_key: JSON element containing the results list for the endpoint;
#        default = root (no data_key)
#   bookmark_query_field: From date-time field used for filtering the query
#   bookmark_type: Data type for bookmark, integer or datetime

STREAMS = {
    "customers": {
        "api_method": "POST",
        "data_key": "data",
        "bookmark_type": "datetime",
        "key_properties": ["id"],
        "denest": ["attributes", "relationships.data"],
        "params": {
            "pageSize": "pageSize"
        },
        "body": {
            "and": [
                {"customer_updated_at": {"gte": '{end_window}'}}
            ],
            "sort": [{"customer_updated_at": "asc"}],
            "queryContext": "customer"
        },
        "path": "customers/search",
        "replication_method": "INCREMENTAL",
        "replication_keys": ["updated_at"],
        "bookmark_query_field": "customer_updated_at"
    },
    "kobjects": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "pageSize": "pageSize"
        },
        "body": {
            "and": [
                {"kobject_updated_at": {"gte": '{end_window}'}}
            ],
            "sort": [{"kobject_updated_at": "asc"}],
            "queryContext": "kobject"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "customers/search",
        "replication_keys": ["updated_at"],
        "api_method": "POST",
        "data_key": "data",
        "bookmark_query_field": "kobject_updated_at",
        "bookmark_type": "datetime"
    },
    "conversations": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "pageSize": "pageSize"
        },
        "body": {
            "and": [
                {"conversation_updated_at": {"gte": '{end_window}'}}
            ],
            "sort": [{"conversation_updated_at": "asc"}],
            "queryContext": "conversation"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "customers/search",
        "replication_keys": ["updated_at"],
        "api_method": "POST",
        "data_key": "data",
        "bookmark_query_field": "conversation_updated_at",
        "bookmark_type": "datetime"
    },
    "messages": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "pageSize": "pageSize"
        },
        "body": {
            "and": [
                {"message_updated_at": {"gte": '{end_window}'}}
            ],
            "sort": [{"message_updated_at": "asc"}],
            "queryContext": "message"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "customers/search",
        "replication_keys": ["updated_at"],
        "api_method": "POST",
        "data_key": "data",
        "bookmark_query_field": "message_updated_at",
        "bookmark_type": "datetime"
    },
    "users": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "page": "{page}"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "users",
        "replication_keys": ["updated_at"],
        "api_method": "GET",
        "data_key": "data",
        "bookmark_query_field": "updated_at",
        "bookmark_type": "datetime"
    },
    "teams": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "page": "{page}",
            "pageSize": "pageSize"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "teams",
        "replication_keys": ["updated_at"],
        "api_method": "GET",
        "data_key": "data",
        "bookmark_query_field": "updated_at",
        "bookmark_type": "datetime"
    },
    "tags": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "page": "{page}",
            "pageSize": "pageSize"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "tags",
        "replication_keys": ["updated_at"],
        "api_method": "GET",
        "data_key": "data",
        "bookmark_query_field": "updated_at",
        "bookmark_type": "datetime"
    },
    "shortcuts": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "page": "{page}",
            "pageSize": "pageSize"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "shortcuts",
        "replication_keys": ["updated_at"],
        "api_method": "GET",
        "data_key": "data",
        "bookmark_query_field": "updated_at",
        "bookmark_type": "datetime"
    },
    "notes": {
        "denest": ["attributes", "relationships.data"],
        "params": {
            "pageSize": "pageSize"
        },
        "body": {
            "and": [
                {"note_updated_at": {"gte": '{end_window}'}}
            ],
            "sort": [{"note_updated_at": "asc"}],
            "queryContext": "note"
        },
        "replication_method": "INCREMENTAL",
        "key_properties": ["id"],
        "path": "customers/search",
        "replication_keys": ["updated_at"],
        "api_method": "POST",
        "data_key": "data",
        "bookmark_query_field": "note_updated_at",
        "bookmark_type": "datetime"
    }
}
