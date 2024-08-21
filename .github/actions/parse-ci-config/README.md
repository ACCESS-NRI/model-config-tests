# parse-ci-config

This action parses the CI testing configuration file. The caller of the action needs to checkout the branch where the config file is defined before running this action.

## Inputs

| Name | Type | Description | Required | Example |
| ---- | ---- | ----------- | -------- | ------- |
| check | `string` | The type of check/test to run | true | `scheduled` |
| branch-or-tag | `string` | The name of git branch or tag | true | `release-1deg_jra55_ryf-2.0` |
| config-filepath | `string` | Path to configuration file | true | `config/ci.json` |

## Outputs

| Name | Type | Description |  Example |
| ---- | ---- | ----------- | -------- |
| markers | `string` | Markers used for the pytest checks, in the python format | `checksum` |
| model-config-tests-version | `string` | The version of the model-config-tests | `0.0.1` |
| python-version | `string` | The python version used to create local test virtual environment (e.g. QA tests) | `3.11.0` |
| payu-version | `string` | The payu version used to create local remote test virtual environment (e.g. reproducibility tests) | `1.1.4` |

## Example usage

```yaml
# ---------
    steps:
      - name: Checkout main
        uses: actions/checkout@v4
        with:
          ref: main
      
      - name: Read scheduled test config
        id: scheduled-config
        uses: access-nri/model-config-tests/.github/actions/parse-ci-config@main
        with:
          check: scheduled
          branch-or-tag: "release-1deg_jra55_ryf-2.0"
          config-filepath: "config/ci.json"
```
