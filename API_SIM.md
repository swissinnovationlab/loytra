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
        { "topic": "get_data", "data": "This is some data" }
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
