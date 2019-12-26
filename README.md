# tap-kustomer

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from the [https://api.kustomerapp.com]([xxx](https://api.kustomerapp.com))
- Extracts the following resources:
  - Customers, Messages, Teams, Tags, Kobjects, Conversations, Shortcuts, Users
- Outputs the schema for each resource
- Incrementally pulls data based on the input state


## Streams

[Customers](https://api.kustomerapp.com/v1/customers/search)
- Endpoint: POST https://api.kustomerapp.com/v1/customers/search
- Body
  ```json
    {
    "and": [
        {
        "customer_updated_at": {
            "gte": "2017-01-01"
        }
        }
    ],
    "sort": [
        {
        "customer_updated_at": "asc"
        }
    ],
    "queryContext": "customer"
    }
  ```
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: end_window
  - Bookmark: date-time
- Transformations: Nodes attributes and relationships denested.

[Kobjects](https://api.kustomerapp.com/v1/customers/search)
- Endpoint: POST https://api.kustomerapp.com/v1/customers/search
- Body
  ```json
    {
    "and": [
        {
        "kobject_updated_at": {
            "gte": "2017-01-01"
        }
        }
    ],
    "sort": [
        {
        "kobject_updated_at": "asc"
        }
    ],
    "queryContext": "kobject"
    }
  ```
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: end_window
  - Bookmark: date-time
- Transformations: Nodes attributes and relationships denested.

[Conversations](https://api.kustomerapp.com/v1/customers/search)
- Endpoint: POST https://api.kustomerapp.com/v1/customers/search
- Body
  ```json
    {
    "and": [
        {
        "conversation_updated_at": {
            "gte": "2017-01-01"
        }
        }
    ],
    "sort": [
        {
        "conversation_updated_at": "asc"
        }
    ],
    "queryContext": "conversation"
    }
  ```
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: end_window
  - Bookmark: date-time
- Transformations: Nodes attributes and relationships denested.

[Messages](https://api.kustomerapp.com/v1/customers/search)
- Endpoint: POST https://api.kustomerapp.com/v1/customers/search
- Body
  ```json
    {
    "and": [
        {
        "message_updated_at": {
            "gte": "2017-01-01"
        }
        }
    ],
    "sort": [
        {
        "message_updated_at": "asc"
        }
    ],
    "queryContext": "message"
    }
  ```
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: end_window
  - Bookmark: date-time
- Transformations: Nodes attributes and relationships denested.

[Notes](https://api.kustomerapp.com/v1/customers/search)
- Endpoint: POST https://api.kustomerapp.com/v1/customers/search
- Body 
  ```json
    {
    "and": [
        {
        "note_updated_at": {
            "gte": "2017-01-01"
        }
        }
    ],
    "sort": [
        {
        "note_updated_at": "asc"
        }
    ],
    "queryContext": "note"
    }
  ```
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: end_window
  - Bookmark: date-time
- Transformations: Nodes attributes and relationships denested.

[Users](https://api.kustomerapp.com/v1/users?page=1)
- Endpoint: GET https://api.kustomerapp.com/v1/users?page=1
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: updated_at
  - Bookmark: date-time
- Transformations: Nodes attributes and relationships denested.

## Quick Start

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    > virtualenv -p python3 venv
    > source venv/bin/activate
    > python setup.py install
    OR
    > cd .../tap-kustomer
    > pip install .
    ```
2. Dependent libraries
    The following dependent libraries were installed.
    ```bash
    > pip install singer-python
    > pip install singer-tools
    > pip install target-stitch
    > pip install target-json
    
    ```
    - [singer-tools](https://github.com/singer-io/singer-tools)
    - [target-stitch](https://github.com/singer-io/target-stitch)

3. Create your tap's `config.json` file. The `api_sub_domain` is everything before `.kustomer.com.` in the KUSTOMER URL.  The `account_name` is everything between `.kustomer.co.com.` and `api` in the KUSTOMER URL. The `date_window_size` is the integer number of days (between the from and to dates) for date-windowing through the date-filtered endpoints (default = 60).

    ```json
    {
        "token": "YOUR_API_TOKEN",
        "account_name": "YOUR_ACCOUNT_NAME",
        "server_subdomain": "YOUR_SERVER_SUBDOMAIN",
        "start_date": "2019-01-01T00:00:00Z",
        "user_agent": "tap-kustomer <api_user_email@your_company.com>",
        "date_window_size": "60"
    }
    ```
    
    Optionally, also create a `state.json` file. `currently_syncing` is an optional attribute used for identifying the last object to be synced in case the job is interrupted mid-stream. The next run would begin where the last job left off.

    ```json
    {
        "currently_syncing": "registers",
        "bookmarks": {
            "customers": "2019-06-11T13:37:51Z",
            "conversations": "2019-06-19T19:48:42Z",
            "kobjects": "2019-06-18T18:23:53Z",
            "teams": "2019-06-20T00:52:44Z",
            "users": "2019-06-19T19:48:45Z"
        }
    }
    ```

4. Run the Tap in Discovery Mode
    This creates a catalog.json for selecting objects/fields to integrate:
    ```bash
    tap-kustomer --config config.json --discover > catalog.json
    ```
   See the Singer docs on discovery mode
   [here](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode).

5. Run the Tap in Sync Mode (with catalog) and [write out to state file](https://github.com/singer-io/getting-started/blob/master/docs/RUNNING_AND_DEVELOPING.md#running-a-singer-tap-with-a-singer-target)

    For Sync mode:
    ```bash
    > tap-kustomer --config tap_config.json --catalog catalog.json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To load to json files to verify outputs:
    ```bash
    > tap-kustomer --config tap_config.json --catalog catalog.json | target-json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To pseudo-load to [Stitch Import API](https://github.com/singer-io/target-stitch) with dry run:
    ```bash
    > tap-kustomer --config tap_config.json --catalog catalog.json | target-stitch --config target_config.json --dry-run > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```

6. Test the Tap
    
    While developing the KUSTOMER tap, the following utilities were run in accordance with Singer.io best practices:
    Pylint to improve [code quality](https://github.com/singer-io/getting-started/blob/master/docs/BEST_PRACTICES.md#code-quality):
    ```bash
    > pylint tap_kustomer -d missing-docstring -d logging-format-interpolation -d too-many-locals -d too-many-arguments
    ```
    Pylint test resulted in the following score:
    ```bash
    Your code has been rated at 9.83/10
    ```

    To [check the tap](https://github.com/singer-io/singer-tools#singer-check-tap) and verify working:
    ```bash
    > tap-kustomer --config tap_config.json --catalog catalog.json | singer-check-tap > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    Check tap resulted in the following:
    ```bash
    The output is valid.
    It contained 8240 messages for 16 streams.

        16 schema messages
    8108 record messages
        116 state messages

    Details by stream:
    +-----------------------------+---------+---------+
    | stream                      | records | schemas |
    +-----------------------------+---------+---------+
    | **ENDPOINT_A**              | 23      | 1       |
    +-----------------------------+---------+---------+
    ```
---

Copyright &copy; 2019 Stitch
