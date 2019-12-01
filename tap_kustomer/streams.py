
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
  }
}
