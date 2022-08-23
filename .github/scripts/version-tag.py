import sys
import re
import subprocess
import os.path
import argparse
from typing import Tuple, List

VERSION_PATTERN = re.compile(r'^v([0-9]+)\.([0-9]+)\.([0-9]+)$')
PR_VERSION_PATTERN = re.compile(r'^v([0-9]+)\.([0-9]+)\.([0-9]+)-PR-([0-9]+)\.([0-9]+)$')
VERSION_FORMAT = 'v%d.%d.%d'
PR_VERSION_FORMAT = 'v%d.%d.%d-PR-%d.%d'

NoVersion = Tuple[()]
Version = Tuple[int, int, int]
PRVersion = Tuple[int, int, int, int, int]

def list_history_tags(reference: str | None=None) -> List[str]:
    args = ['git', 'log', '--format=%D']
    if reference: args.append(reference)
    out = subprocess.run(args, text=True, capture_output=True, check=True)
    tags = []
    for line in out.stdout.split('\n'):
        line = line.strip()
        if not line: continue
        for tag in line.split(','):
            tag = tag.strip()
            if not tag.startswith('tag:'): continue
            tag = tag[len('tag:'):].strip()
            tags.append(tag)
    return tags

def list_all_tags() -> List[str]:
    args = ['git', 'tag', '-l']
    out = subprocess.run(args, text=True, capture_output=True, check=True)
    tags = []
    for line in out.stdout.split('\n'):
        line = line.strip()
        if not line: continue
        tags.append(line)
    return tags

def max_tag_version(tags: List[str]) -> Version | NoVersion:
    maxtag = ()
    for tag in tags:
        m = VERSION_PATTERN.match(tag)
        if not m: continue
        version = tuple(int(v) for v in m.group(1, 2, 3))
        if maxtag < version: maxtag = version
    if maxtag:
        print('latest tag version is "%s"' % (VERSION_FORMAT % maxtag), file=sys.stderr)
    return maxtag

def max_tag_pr_version(pr: int, tags: List[str]) -> PRVersion | NoVersion:
    maxtag = ()
    for tag in tags:
        m = PR_VERSION_PATTERN.match(tag)
        if not m: continue
        version = tuple(int(v) for v in m.group(1, 2, 3, 4, 5))
        if version[3] != pr: continue
        if maxtag[4] < version[4]: maxtag = version
    if maxtag:
        print('latest pr tag version is "%s"' % (PR_VERSION_FORMAT % maxtag), file=sys.stderr)
    return maxtag

def max_file_version(files: List[str]=()) -> Version | NoVersion:
    maxfile = ()
    for f in files:
        if not os.path.exists(f):
            print('file "%s" doesn\'t exist' % (f,), file=sys.stderr)
            continue
        if not os.path.isfile(f):
            print('"%s" isn\'t a file' % (f,), file=sys.stderr)
            continue
        with open(f) as r:
            content = r.read().strip()
        if not content:
            print('file "%s" is empty' % (f,), file=sys.stderr)
            continue
        m = VERSION_PATTERN.match(content)
        if not m:
            print('file "%s" doesn\'t contain a valid version' % (f,), file=sys.stderr)
            continue
        version = tuple(int(v) for v in m.group(1, 2, 3))
        print('file "%s" has version "%s"' % (f, VERSION_FORMAT % version), file=sys.stderr)
        if maxfile < version: maxfile = version
    return maxfile

def next_version(reference: str | None=None, files: List[str]=()) -> Version:
    maxtag = max_tag_version(list_history_tags(reference=reference))
    maxfile = max_file_version(files)
    if maxfile and maxfile > maxtag:
        version = maxfile
    elif maxtag:
        version = (*maxtag[:-1], maxtag[-1]+1)
    else:
        version = (0, 0, 0)
    alltags = set(list_all_tags())
    while VERSION_FORMAT % version in alltags:
        version = (*version[:-1], version[-1]+1)
    return version

def next_pr_version(pr: int, reference: str | None=None, files: List[str]=()) -> PRVersion:
    maxtagpr = max_tag_pr_version(pr, list_all_tags())
    nextver = next_version(reference=reference, files=files)
    nextsub = maxtagpr[4] + 1 if maxtagpr else 0
    return (*nextver, pr, nextsub)

GITHUB_SET_TAG = '::set-output name=TAG::%s'

def cmd_version(args: argparse.Namespace):
    version = next_version(reference=args.reference, files=args.file)
    print(GITHUB_SET_TAG % (VERSION_FORMAT % version))

def cmd_pr(args: argparse.Namespace):
    version = next_pr_version(pr=args.pr, reference=args.reference, files=args.file)
    print(GITHUB_SET_TAG % (PR_VERSION_FORMAT % version))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    def cmd_default(args: argparse.Namespace):
        parser.print_help()
        sys.exit(2)
    parser.set_defaults(cmd=cmd_default)

    subparsers = parser.add_subparsers()

    version_parser = subparsers.add_parser('version')
    version_parser.add_argument('--reference', type=str, nargs='?', default=None)
    version_parser.add_argument('--file', type=str, nargs='*', default=())
    version_parser.set_defaults(cmd=cmd_version)

    pr_parser = subparsers.add_parser('pr')
    pr_parser.add_argument('pr', type=int)
    pr_parser.add_argument('--reference', type=str, nargs='?', default=None)
    pr_parser.add_argument('--file', type=str, nargs='*', default=())
    pr_parser.set_defaults(cmd=cmd_pr)

    args = parser.parse_args()
    args.cmd(args)
