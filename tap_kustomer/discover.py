import json
import copy
from datetime import datetime, timedelta, timezone
import singer
from singer.catalog import Catalog, CatalogEntry, Schema
from tap_kustomer.schema import get_schemas, STREAMS
from tap_kustomer.client import KustomerForbiddenError

LOGGER = singer.get_logger()


def _check_stream_access(client, stream_name, stream_config):
    """Check if the API credentials have read access to a specific stream."""
    method = stream_config.get('api_method', 'GET')
    path = stream_config.get('path', stream_name)
    body = None
    if method == 'POST' and 'body' in stream_config:
        body_copy = copy.deepcopy(stream_config['body'])
        # Replace placeholder with a valid timestamp for the access probe
        bookmark_field = stream_config.get('bookmark_query_field')
        if body_copy.get('and'):
            for condition in body_copy['and']:
                if bookmark_field and bookmark_field in condition:
                    # Use 1 day ago to keep the access probe lightweight
                    one_day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                    condition[bookmark_field]['gte'] = one_day_ago
        body = json.dumps(body_copy)
    return client.check_stream_access(stream_name, method, path, body=body)


def _apply_access_checks(client, schemas, field_metadata):
    """
    Probe each stream for read access and remove inaccessible streams
    from schemas and field_metadata in place.
    Raises KustomerForbiddenError if no streams are accessible.
    """
    inaccessible_streams = [
        stream_name
        for stream_name in list(schemas.keys())
        if stream_name in STREAMS
        and not _check_stream_access(client, stream_name, STREAMS[stream_name])
    ]

    for stream_name in inaccessible_streams:
        schemas.pop(stream_name, None)
        field_metadata.pop(stream_name, None)

    if not schemas:
        raise KustomerForbiddenError(
            "No streams are accessible. Ensure the credentials have read "
            "permission for at least one stream."
        )
    elif inaccessible_streams:
        LOGGER.warning(
            "Unauthorized streams have been excluded: %s",
            ", ".join(inaccessible_streams),
        )


def discover(client):
    """
    Run the discovery mode, prepare the catalog file and return the catalog.
    Access to each stream is verified using the provided client and streams
    the credentials cannot read are excluded from the returned catalog.
    """
    schemas, field_metadata = get_schemas()
    _apply_access_checks(client, schemas, field_metadata)
    catalog = Catalog([])

    for stream_name, schema_dict in schemas.items():
        schema = Schema.from_dict(schema_dict)
        mdata = field_metadata[stream_name]

        catalog.streams.append(CatalogEntry(
            stream=stream_name,
            tap_stream_id=stream_name,
            key_properties=STREAMS[stream_name]['key_properties'],
            schema=schema,
            metadata=mdata
        ))

    return catalog
