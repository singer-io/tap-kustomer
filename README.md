# tap-kustomer

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from the [https://api.kustomerapp.com](https://api.kustomerapp.com)
- Extracts the following resources:
  - Conversations, Customers, Kobjects, Messages, Notes, Teams, Tags, Shortcuts, Users
- Pagination for Conversations, Custoemrs, Kobjects, Messages, Note
  - Next request based on last `updatedAt` in respose.
  - See, https://dev.kustomer.com/v1/customers/customer-search#pagination
  - `pageSize` set to 300 to circumvent large numbers of records with same `updatedAt`
- Outputs the schema for each resource
- Incrementally pulls data based on the input state


## Streams

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
  - Bookmark query fields: gte
  - Bookmark: date-time
- Transformations: Nodes attributes and relationships denested.
  - `attributes.sla` renamed to `sla_data`
  - Snake to camel case

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
  - Bookmark query fields: gte
  - Bookmark: date-time
- Transformations: 
  - Nodes attributes and relationships denested.
  - Snake to camel case

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
  - Bookmark query fields: gte
  - Bookmark: date-time
- Transformations
  - Nodes attributes and relationships denested.
  - Snake to camel case

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
  - Bookmark query fields: gte
  - Bookmark: date-time
- Transformations
  - Nodes attributes and relationships denested.
  - Snake to camel case

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
  - Bookmark query fields: gte
  - Bookmark: date-time
- Transformations
  - Nodes attributes and relationships denested.
  - Snake to camel case

[Shortcuts](https://api.kustomerapp.com/v1/shortcuts?page=1)
- Endpoint: GET https://api.kustomerapp.com/v1/shortcuts?page=1
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: updated_at
  - Bookmark: date-time
- Transformations
  - Nodes attributes and relationships denested
  - Snake to camel case

[Tags](https://api.kustomerapp.com/v1/tags?page=1)
- Endpoint: GET https://api.kustomerapp.com/v1/tag?page=1
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: updated_at
  - Bookmark: date-time
- Transformations
  - Nodes attributes and relationships denested
  - Snake to camel case

[Teams](https://api.kustomerapp.com/v1/teams?page=1)
- Endpoint: GET https://api.kustomerapp.com/v1/teams?page=1
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: updated_at
  - Bookmark: date-time
- Transformations
  - Nodes attributes and relationships denested
  - Snake to camel case

[Users](https://api.kustomerapp.com/v1/users?page=1)
- Endpoint: GET https://api.kustomerapp.com/v1/users?page=1
- Primary key fields: id
- Replication strategy: INCREMENTAL (query filtered)
  - Bookmark query fields: updated_at
  - Bookmark: date-time
- Transformations
  - Nodes attributes and relationships denested
  - Snake to camel case

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

3. Create your tap's `config.json` file. The `token` is the credential supplied from the Kustomer integration. The `date_window_size` is the integer number of days (between the from and to dates) for date-windowing through the date-filtered endpoints (default = 60). The `page_size_limit` is the integer number of records to return per API request. 

    ```json
    {
        "token": "YOUR_API_TOKEN",
        "start_date": "2019-01-01T00:00:00Z",
        "user_agent": "tap-kustomer <api_user_email@your_company.com>",
        "date_window_size": "60",
        "page_size_limit": "100"
    }
    ```
    
    Optionally, also create a `state.json` file. `currently_syncing` is an optional attribute used for identifying the last object to be synced in case the job is interrupted mid-stream. The next run would begin where the last job left off.

    ```json
      {
        "bookmarks": {
          "conversations": "2019-12-26T18:35:41.583Z",
          "customers": "2019-12-26T18:39:38.186Z",
          "kobjects": "2019-12-26T18:24:18.283Z",
          "messages": "2019-12-26T18:39:45.018Z",
          "shortcuts": "2019-12-25T18:00:00Z",
          "tags": "2019-12-25T18:00:00Z",
          "users": "2019-12-25T18:00:00Z"
        },
        "currently_syncing": "teams"
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
    It contained 35416 messages for 16 streams.

    16 schema messages
    35416 record messages
    116 state messages

    Details by stream:
   +---------------+---------+---------+
   | stream        | records | schemas |
   +---------------+---------+---------+
   | conversations | 1274    | 1       |
   | kobjects      | 258     | 1       |
   | tags          | 0       | 1       |
   | notes         | 0       | 1       |
   | users         | 0       | 1       |
   | customers     | 32300   | 1       |
   | shortcuts     | 0       | 1       |
   | teams         | 0       | 1       |
   | messages      | 1584    | 1       |
   +---------------+---------+---------+
    ```
---

Copyright &copy; 2019 Stitch
