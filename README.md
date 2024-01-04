# dependabot-paused-report

This Python script checks all or selected orgs that you have access to for repos in which Dependabot is [paused](https://github.blog/changelog/2023-01-12-dependabot-pull-requests-pause-for-inactivity/) and generates a JSON report with such repos sorted by org.

## Requirements

- Python 3
- `requests` library (install with `pip install requests`)

## Usage

1. Create a [**classic** GitHub personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) with `read:org` and `repo` scope.

2. Run the script with the following command:

```bash
export DEPENDABOT_PAUSED_REPORT_TOKEN="<your token>"

# Check repos in all orgs that the token can access
python3 dependabot-paused-report.py
# OR
# Check repos in specific orgs
python3 dependabot-paused-report.py -o org1 org2 org3

# OPTIONAL, get only repos with paused Dependabot in org2 from report
cat paused_dependabot_repos_YYYY-MM-DD_HH-MM-SS.json | jq '.org2'
```

### Options

- `-o` or `--orgs`: List of GitHub organizations to check. If not specified, all organizations that the token can access will be checked.
- `-j` or `--json`: Filename for JSON report. Default: `paused_dependabot_repos_YYYY-MM-DD_HH-MM-SS.json`

### Environment variables
- `DEPENDABOT_PAUSED_REPORT_TOKEN`: GitHub personal access token with `read:org` and `repo` scope
