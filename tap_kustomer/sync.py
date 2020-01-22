from datetime import timedelta
import json
import math
import singer
from singer import metrics, metadata, Transformer, utils
from singer.utils import strptime_to_utc, strftime
from tap_kustomer.transform import transform_json
from tap_kustomer.streams import STREAMS

LOGGER = singer.get_logger()

DATE_WINDOW_DEFAULT = 60
RESULT_RETURN_LIMIT = 100


def write_schema(catalog, stream_name):
    stream = catalog.get_stream(stream_name)
    schema = stream.schema.to_dict()
    try:
        singer.write_schema(stream_name, schema, stream.key_properties)
    except OSError as err:
        LOGGER.info('OS Error writing schema for: %s', stream_name)
        raise err


def write_record(stream_name, record, time_extracted):
    try:
        singer.messages.write_record(stream_name,
                                     record,
                                     time_extracted=time_extracted)
    except OSError as err:
        LOGGER.info('OS Error writing record for: %s', stream_name)
        LOGGER.info('record: %s', record)
        raise err


def get_bookmark(state, stream, default):
    if (state is None) or ('bookmarks' not in state):
        return default
    return state.get('bookmarks', {}).get(stream, default)


def write_bookmark(state, stream, value):
    if 'bookmarks' not in state:
        state['bookmarks'] = {}
    state['bookmarks'][stream] = value
    LOGGER.info('Write state for stream: %s, value: %s', stream, value)
    singer.write_state(state)


def transform_datetime(this_dttm):
    with Transformer() as transformer:
        new_dttm = transformer._transform_datetime(  # pylint: disable=protected-access
            this_dttm)
    return new_dttm


def process_records(catalog,  # pylint: disable=too-many-branches
                    stream_name,
                    records,
                    time_extracted,
                    bookmark_field=None,
                    max_bookmark_value=None,
                    last_datetime=None):
    stream = catalog.get_stream(stream_name)
    schema = stream.schema.to_dict()
    stream_metadata = metadata.to_map(stream.metadata)

    with metrics.record_counter(stream_name) as counter:
        for record in records:
            # Transform record for Singer.io
            with Transformer() as transformer:
                transformed_record = transformer.transform(
                    record, schema, stream_metadata)

                # Reset max_bookmark_value to new value if higher
                if transformed_record.get(bookmark_field):
                    if max_bookmark_value is None or transformed_record[
                            bookmark_field] > transform_datetime(
                                max_bookmark_value):
                        max_bookmark_value = transformed_record[bookmark_field]

                if bookmark_field and (bookmark_field in transformed_record):
                    last_dttm = transform_datetime(last_datetime)
                    bookmark_dttm = transform_datetime(
                        transformed_record[bookmark_field])
                    # Keep only records whose bookmark is after the last_datetime
                    if bookmark_dttm >= last_dttm:
                        write_record(stream_name,
                                     transformed_record,
                                     time_extracted=time_extracted)
                        counter.increment()
                else:
                    write_record(stream_name,
                                 transformed_record,
                                 time_extracted=time_extracted)
                    counter.increment()

        return max_bookmark_value, counter.value


# Sync a specific endpoint
def sync_endpoint(client,  # pylint: disable=too-many-branches, too-many-statements
                  catalog,
                  state,
                  start_date,
                  stream_name,
                  path,
                  endpoint_config,
                  static_params,
                  bookmark_query_field_from=None,
                  bookmark_query_field_to=None,
                  bookmark_field=None,
                  bookmark_type=None,
                  data_key=None,
                  id_fields=None,
                  days_interval=None,
                  page_size_limit=None):
    # Get the latest bookmark for the stream and set the last_integer/datetime
    last_datetime = None
    last_integer = None
    max_bookmark_value = None
    if bookmark_type == 'integer':
        last_integer = get_bookmark(state, stream_name, 0)
        max_bookmark_value = last_integer
    else:
        last_datetime = get_bookmark(state, stream_name, start_date)
        max_bookmark_value = last_datetime

    write_schema(catalog, stream_name)

    # windowing: loop through date days_interval date windows from last_datetime to now_datetime
    now_datetime = utils.now()
    page = 1
    start_window = strptime_to_utc(last_datetime)
    end_window = now_datetime
    diff_sec = (end_window - start_window).seconds
    # round-up difference to days
    days_interval = math.ceil(diff_sec / (3600 * 24))
    endpoint_total = 0

    offset = 0  # Starting offset value for each batch API call
    # pagination: loop thru all pages of data using next (if not None)
    next_url = '{}/{}'.format(client.base_url, path)

    # next page is next url for page 1
    next_page = next_url
    total_records = 0

    # Tap configurable page size. 300 value currently as API often returns
    # 200+ which have the same date time.
    limit = page_size_limit
    # Initialize total; set to actual total on subsequent API calls
    total_page = limit

    # Retrieve pages until response header indicates no next page
    while next_page:
        params = static_params  # adds in endpoint specific, sort, filter params
        if bookmark_query_field_from:
            # For datetime bookmark_type, tap allows from/to date window
            # For integer bookmark_type, tap allows from last_integer
            if bookmark_type == 'datetime':
                params[bookmark_query_field_from] = strftime(start_window)
            elif bookmark_type == 'integer':
                params[bookmark_query_field_from] = last_integer
            if bookmark_query_field_to:
                if bookmark_type == 'integer':
                    params[bookmark_query_field_to] = strftime(end_window)

        # Need URL querystring for 1st page; subsequent pages provided by next_url
        # querystring: Squash query params into string
        if page == 1 and not params == {}:
            querystring = '&'.join(
                ['%s=%s' % (key, value) for (key, value) in params.items()])
        else:
            querystring = None
        LOGGER.info('URL for Stream %s: %s%s%s',
                    stream_name,
                    next_url,
                    '/' if page == 1 else '',
                    '?{}'.format(querystring) if querystring else '')

        # API request data
        # Set request params
        params = {}
        for key, _ in endpoint_config.get('params').items():
            if key == 'page':
                params[key] = page
            if key == 'pageSize':
                params[key] = limit

        # Need URL querystring for 1st page; subsequent pages provided by next_url
        # querystring: Squash query params into string
        # if page != 1:
        querystring = '&'.join(
            ['%s=%s' % (key, value) for (key, value) in params.items()])
        LOGGER.info('URL for Stream %s: %s%s',
                    stream_name,
                    path,
                    '?{}'.format(querystring) if querystring else '')

        # Set POST request body
        body = endpoint_config.get('body')
        if body:
            body['and'][0][endpoint_config.get(
                'bookmark_query_field')]['gte'] = strftime(start_window)

        response = {}
        response = client.fetch(endpoint_config.get('api_method'),
                                url=next_url,
                                path=path,
                                params=querystring,
                                endpoint=stream_name,
                                data=json.dumps(body))

        # time_extracted: datetime when the data was extracted from the API
        time_extracted = utils.now()
        if not response or response is None or response == {}:
            total_page = 0
            break  # No data results

        # set total_records and and last updated for pagination
        total_page = len(response.get('data'))
        if 'total' in response.get('meta'):
            total_records = response.get('meta').get('total')
        if len(response.get('data')) > 0:
            last_updated = response.get('data')[-1]['attributes']['updatedAt']
        # Get next link for end of pagination indication across all endpoints
        next_page = response.get('links').get('next', None)

        # Transform data with transform_json from transform.py
        # The data_key identifies the array/list of records below the <root> element
        # LOGGER.info('data = {}'.format(data)) # TESTING, comment out
        transformed_data = []  # initialize the record list
        # If a single record dictionary, append to a list[]
        if data_key is None:
            transformed_data = transform_json(response, endpoint_config, 'results')
        elif data_key in response:
            transformed_data = transform_json(response, endpoint_config, data_key)
        # LOGGER.info('transformed_data = {}'.format(transformed_data))  # TESTING, comment out
        if not transformed_data or transformed_data is None:
            LOGGER.info('No transformed data for data = %s', response)
            # total_records = 0
            break  # No data results
        for record in transformed_data:
            for key in id_fields:
                if not record.get(key):
                    LOGGER.info('Missing key %s in record: %s', key, record)

        # Process records and get the max_bookmark_value and record_count for the set of records
        max_bookmark_value, record_count = \
            process_records(catalog=catalog,
                            stream_name=stream_name, records=transformed_data,
                            time_extracted=time_extracted, bookmark_field=bookmark_field,
                            max_bookmark_value=max_bookmark_value,
                            last_datetime=last_datetime)
        LOGGER.info('Stream %s, batch processed %s records', stream_name, record_count)

        # Update the state with the max_bookmark_value for the stream
        if bookmark_field:
            write_bookmark(state, stream_name, max_bookmark_value)

        # to_rec: to record; ending record for the batch page
        to_rec = offset + limit
        if total_page < limit:
            to_rec = to_rec + total_page

        LOGGER.info('Synced Stream: %s, page: %s, %s to %s of total records: %s',
                    stream_name,
                    page,
                    offset,
                    to_rec,
                    total_records)

        # Pagination: increment the offset by the limit (batch-size) and page
        offset = offset + limit
        page = page + 1

        # Increment date window
        start_window = strptime_to_utc(last_updated)
        next_end_window = end_window + timedelta(days=days_interval)
        if next_end_window > now_datetime:
            end_window = now_datetime
        else:
            end_window = next_end_window
        endpoint_total = endpoint_total + total_page

    # Return endpoint_total across all batches
    return endpoint_total


# Currently syncing sets the stream currently being delivered in the state.
# If the integration is interrupted, this state property is used to identify
#  the starting point to continue from.
# Reference: https://github.com/singer-io/singer-python/blob/master/singer/bookmarks.py#L41-L46
def update_currently_syncing(state, stream_name):
    if (stream_name is None) and ('currently_syncing' in state):
        del state['currently_syncing']
    else:
        singer.set_currently_syncing(state, stream_name)
    singer.write_state(state)


def sync(client, config, catalog, state):
    if 'start_date' in config:
        start_date = config['start_date']

    # Get selected_streams from catalog, based on state last_stream
    #   last_stream = Previous currently synced stream, if the load was interrupted
    last_stream = singer.get_currently_syncing(state)
    LOGGER.info('last/currently syncing stream: %s', last_stream)
    selected_streams = []
    for stream in catalog.get_selected_streams(state):
        selected_streams.append(stream.stream)
    LOGGER.info('selected_streams: %s', selected_streams)

    if not selected_streams:
        return

    # Loop through selected_streams
    for stream_name in selected_streams:
        LOGGER.info('START Syncing: %s', stream_name)
        update_currently_syncing(state, stream_name)
        endpoint_config = STREAMS[stream_name]
        path = endpoint_config.get('path', stream_name)
        bookmark_field = next(
            iter(endpoint_config.get('replication_keys', [])), None)
        total_records = sync_endpoint(
            client=client,
            catalog=catalog,
            state=state,
            start_date=start_date,
            stream_name=stream_name,
            path=path,
            endpoint_config=endpoint_config,
            static_params=endpoint_config.get('params', {}),
            bookmark_query_field_from=endpoint_config.get(
                'bookmark_query_field_from'),
            bookmark_field=bookmark_field,
            bookmark_type=endpoint_config.get('bookmark_type'),
            data_key=endpoint_config.get('data_key', 'results'),
            id_fields=endpoint_config.get('key_properties'),
            days_interval=int(
                config.get('date_window_size', DATE_WINDOW_DEFAULT)),
            page_size_limit=int(
                config.get('page_size_limit', RESULT_RETURN_LIMIT)))

        update_currently_syncing(state, None)
        LOGGER.info('FINISHED Syncing: %s, total_records: %s', stream_name, total_records)
