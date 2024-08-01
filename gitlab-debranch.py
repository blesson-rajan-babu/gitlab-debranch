import argparse
import datetime
import urllib

import requests


def matches(value, patterns):
    return True if patterns is not None and len([x for x in patterns if value.startswith(x)]) > 0 else False


def get_projects(group_id, headers, ignored_projects, only_projects):
    group_link = f'https://gitlab.com/api/v4/groups/{group_id}'
    response = requests.get(group_link, headers=headers)
    if response.status_code != 200:
        print('Failed to access group. Confirm group and check token permissions.')
        exit(1)
    all_projects = response.json()['projects']
    filtered_projects = [x for x in all_projects if x['archived'] is False]
    filtered_projects = [x for x in filtered_projects if not matches(x['path'], ignored_projects)]
    if only_projects is not None:
        filtered_projects = [x for x in filtered_projects if matches(x['path'], only_projects)]
    return [{'name': x['path'], 'link': x['_links']['self']} for x in filtered_projects]


def remove_branches(project, headers, ignored_branches, only_branches, ignored_days, dry_run):
    now = datetime.datetime.today()
    response = requests.get(f'{project["link"]}/repository/branches', headers=headers)
    if response.status_code != 200:
        print('Failed to fetch branches. Check token permissions.')
        exit(1)
    all_branches = response.json()
    filtered_branches = [x for x in all_branches if x['default'] is False or x['protected'] is False]
    filtered_branches = [x for x in filtered_branches if not matches(x['name'], ignored_branches)]
    if only_branches is not None:
        filtered_branches = [x for x in filtered_branches if matches(x['name'], only_branches)]
    filtered_branches = [x for x in filtered_branches if
                         (now - datetime.datetime.strptime(x['commit']['committed_date'][:10], '%Y-%m-%d')).days > ignored_days]
    print(f'> {project["name"]}')
    for branch in filtered_branches:
        branch_id = urllib.parse.quote_plus(branch['name'])
        if dry_run is False:
            response = requests.delete(f'{project["link"]}/repository/branches/{branch_id}', headers=headers)
            if response.status_code != 204:
                print('Failed to delete branches. Check token permissions.')
                exit(1)
        print(f'  |- {branch["name"]}')


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('-t', '--token', help='GitLab token (usually a personal access token) with api access scope.', required=True)
    parser.add_argument('-g', '--group', help='GitLab group to clean-up.', required=True)
    parser.add_argument('--ignored-days', type=int,
                        help='Ignore branches where last commit is recent. Defaults to 90.', default=90)
    parser.add_argument('--ignored-projects', nargs='*',
                        help='Ignore these projects. Exact or partial matching (begins with) allowed.')
    parser.add_argument('--ignored-branches', nargs='*',
                        help='Ignore these branches. Exact or partial matching (begins with) allowed.')
    parser.add_argument('--only-projects', nargs='*',
                        help='Include only these projects. Exact or partial matching (begins with) allowed.')
    parser.add_argument('--only-branches', nargs='*',
                        help='Include only these branches. Exact or partial matching (begins with) allowed.')
    parser.add_argument('--dry-run', help='Dry-run mode (default) does not apply any changes.',
                        action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    ignored_days = args.ignored_days if args.ignored_days >= 0 else 90
    dry_run = False if args.dry_run is False else True
    print('Running with the following arguments:')
    print(f'--group           : {args.group}')
    print(f'--ignored-days    : {ignored_days}')
    print(f'--ignored-projects: {args.ignored_projects}')
    print(f'--ignored-branches: {args.ignored_branches}')
    print(f'--only-projects   : {args.only_projects}')
    print(f'--only-branches   : {args.only_branches}')
    print(f'--dry-run         : {dry_run}')
    print()
    headers = {'PRIVATE-TOKEN': args.token}
    projects = get_projects(args.group, headers, args.ignored_projects, args.only_projects)
    for project in projects:
        remove_branches(project, headers, args.ignored_branches, args.only_branches, ignored_days, dry_run)
    print('Done!')


if __name__ == '__main__':
    main()
