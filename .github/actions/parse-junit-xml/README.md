# parse-junit-xml

This action parses the Pytest generated JUnit XML test report file
and outputs a simple multiline string of name of each test ran, and the outcome of the test (e.g. pass, fail or error).

## Inputs

| Name | Type | Description | Required | Example |
| ---- | ---- | ----------- | -------- | ------- |
| filepath | `string` | Path to JUnit XML test report file | true | `test_report.xml` |

## Outputs

| Name | Type | Description |  Example |
| ---- | ---- | ----------- | -------- |
| summary | `string` | Multiline string for each test run | ``:fire: `errored_test`\n:x: `failed_test`\n:white-check-mark: `passed_test`\n`` |
## Example usage

```yaml
# ---------
    steps:
      # <Run Tests to generate test_report.xml>
 
      - name: Parse test report
        id: scheduled-config
        uses: access-nri/model-config-tests/.github/actions/parse-junit-xml@main
        with:
          filepath: test_report.xml
```
