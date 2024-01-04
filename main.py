#!/usr/bin/env python3

import argparse
import json
import math
import os
import re
import sys

from datetime import datetime, timedelta
from time import sleep, time

import requests

TOKEN_ENV_VAR = 'PAUSED_DEPENDABOT_REPOS_TOKEN'
API_BASE = 'https://api.github.com'

def get_timestamp():
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d_%H-%M-%S')
    return now_str

def setup_parser():
    parser = argparse.ArgumentParser(description='Check if Dependabot is paused for any repos in all accessible or one specific org(s)')
    parser.add_argument('-o', '--orgs', help='Specific GitHub org(s) to check repos in', nargs='*')
    parser.add_argument('-j', '--json', help='Output results to a json file', default=f'paused_dependabot_repos_{get_timestamp()}.json')
    args = parser.parse_args()
    return args

def get_token():
    token = os.getenv(TOKEN_ENV_VAR)
    if not token:
        print(f"ERROR: Token not found in environment variable: {TOKEN_ENV_VAR}")
        sys.exit(1)
    if token.startswith('github_pat_'):
        print("This script requires a classic PAT but a fine-grained PAT was provided.")
        sys.exit(1)
    return token

def make_request(endpoint, token=get_token(), custom_headers=None):
    headers = {"Accept": "application/vnd.github+json",  "X-GitHub-Api-Version": "2022-11-28"}
    url = f'{API_BASE}{endpoint}'
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if custom_headers:
        headers.update(custom_headers)

    all_results = []
    while url:
        try:
            response = requests.get(url, headers=headers)
            while response.status_code == 403:
                # handle rate limit
                remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                if remaining == 0:
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                        sleep_time = max(reset_time - time(), 0)
                        now = datetime.now()
                        resume_time = now + timedelta(seconds=sleep_time)
                        print(f"Rate limit exceeded at {now.strftime('%Y-%m-%d %H:%M:%S')}, sleeping for {math.ceil(sleep_time / 60)} minutes until {resume_time.strftime('%Y-%m-%d %H:%M:%S')}. Hit Ctrl-C to exit.")
                        sleep(sleep_time)
                        response = requests.get(url, headers=headers)
                else:
                    #print(response.headers)
                    #print(response.json())
                    print(f"ERROR: Token doesn't have permission for API resource: {url}")
                    print("You might need to authorize SSO for your token to access non-public repos in this org.")
                    return []
            if response.status_code == 404:
                # Dependabot is not enabled for repo
                return []
            else:
                response.raise_for_status()
            if isinstance(response.json(), dict):
                return response.json()
            # if response is a list, extend all_results with it and see if there's a next page
            all_results.extend(response.json())
            link_header = response.headers.get('Link')
            if link_header is None:
                break
            links = link_header.split(', ')
            url = None
            for link in links:
                if 'rel="last"' in link:
                    last_page = re.match(r'.*page=([0-9]+)', link).group(1)
            for link in links:
                if 'rel="next"' in link:
                    url = link[link.index('<') + 1:link.index('>')]
                    #print(url)
                    current_page = re.match(r'.*page=(\d+)', url).group(1)
                    print(f'\r  {current_page}/{last_page} pages with max 100 repos each in org parsed for checking...', end='')
        except requests.exceptions.RequestException as e:
            print(f'Error occurred while making the request: {e}')
            sys.exit(1)
    print()
    #print(all_results)
    return all_results

def get_orgs():
    response = make_request('/user/orgs')
    orgs = [org['login'] for org in response]
    if not orgs:
        print("ERROR: No orgs found with provided token.")
        sys.exit(1)
    return orgs

def get_org_repos(org):
    print(f'Getting repos for org: {org}')
    response = make_request(f'/orgs/{org}/repos?type=all?per_page=100')
    return [repo['name'] for repo in response]

def dependabot_is_paused(org, repo):
    response = make_request(f'/repos/{org}/{repo}/automated-security-fixes')
    if isinstance(response, dict):
        if 'paused' in response:
            return response['paused']
    return False

def cleanup_results(paused_repos):
    if paused_repos:
        for org in list(paused_repos.keys()):
            if not paused_repos[org]:
                paused_repos.pop(org)
    return paused_repos

def write_to_json(paused_repos, json_output):
    with open(json_output, 'w') as f:
        json.dump(paused_repos, f, indent=4)
    print(f'\nWrote results to {json_output}')

def main():
    paused_repos = {}
    args = setup_parser()
    if args.orgs:
        orgs = args.orgs
    else:
        orgs = get_orgs()
    print(f'Checking repos in orgs: {", ".join(orgs)}\n')
    for org in orgs:
        repos = get_org_repos(org)
        print(f'  Checking if Dependabot is paused in any repos in {org}...')
        for repo in repos:
            if dependabot_is_paused(org, repo):
                if not org in paused_repos:
                    paused_repos[org] = []
                paused_repos[org].append(repo)
            print(f'\r    {repos.index(repo)}/{len(repos) - 1} repos checked...', end='')
        print()
        print(f'Done checking repos in org {org}.')
    paused_repos = cleanup_results(paused_repos)
    if paused_repos:
        write_to_json(paused_repos, args.json)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nKeyboard interrupt detected, exiting...')
        sys.exit(1)
