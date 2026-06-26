import os
import json
import getpass
import urllib.request
import urllib.error


def main():
    token = os.environ.get('GH_TOKEN')
    if not token:
        token = getpass.getpass('Enter GitHub PAT with repo scope: ')
    body = json.dumps({
        'name': 'Internship',
        'description': 'Uploaded project from local workspace',
        'private': False
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.github.com/user/repos',
        data=body,
        headers={
            'Authorization': f'token {token}',
            'User-Agent': 'VSCode-CoPilot',
            'Accept': 'application/vnd.github.v3+json'
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read().decode('utf-8'))
            print('REMOTE_URL=' + resp['clone_url'])
    except urllib.error.HTTPError as e:
        print('ERROR', e.code, e.reason)
        print(e.read().decode('utf-8'))
        raise


if __name__ == '__main__':
    main()
