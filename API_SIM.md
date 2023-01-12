# DM Cloud API client simulator
Use `loytra api-sim [PATH_TO_API_DEFINITION.JSON]` to start the DMCloud business logic backend API simulation.

## Definition file format
The definition file is a simple json file with the following format:
```
{
    "api": {
        "host": "DMCLOUS_API_HOST",
        "port": DMCLOUD_API_PORT,
        "use_ssl": true,
        "api_key": "YOUR_API_KEY",
        "app_key": "OPTIONAL_APP_KEY"
    },
    "monitor": [ "DEVICE_KEY_1", "DEVICE_KEY_2" ],
    "methods": [
        { "topic": "echo" },

        { "topic": "get_data", "data": "This is some data" },

        { "topic": "reply/request", "reply": "reply/response" },

        { "topic": "multi", "data": "Multi 1", "break": false },
        { "topic": "multi", "data": "Multi 2", "break": false },

        { "topic": "match/test", "match": { "value": "1" }, "data": "Matched 1" },
        { "topic": "match/test", "match": { "value": "2" }, "data": "Matched 2" },
        { "topic": "match/test", "data": "No match found!" }
    ]
}
```

### `api` - api access configuration
  - `host` - DMCloud API host
  - `port` - DMCloud API port
  - `use_ssl` - should use SSL when connecting to the DMCloud API - always true
  - `api_key` - DMCloud API access key
  - `app_key` - optional Application identification key, must be set to a valid DMCloud Application for the device-to-sim communication to work

### `monitor` - device state monitioring
Optional list of device keys for device connection state monitoring.

### `methods` - method simulation mapping
Each method can specify a match `topic` and optionally the response `data`. If the `data` field is not set, the simulator will echo the received data.
 - `topic` - match topic
 - `reply` - optional response topic, if not set will respond on the received topic
 - `data` - response data, if not set will respond with received data
 - `match` - optionally match received data, for list and dictionary, the match specification does not have to contain all items or keys from the data
 - `break` - set to false to not stop checking when a method specification is matched
