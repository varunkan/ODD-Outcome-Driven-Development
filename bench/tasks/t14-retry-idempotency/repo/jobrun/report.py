"""A plain-text summary of a journal, for the night shift: `python3 -m jobrun report <journal>`."""

import argparse
import sys

from .queue import JobQueue, STATES


def summarize(queue):
    counts = queue.counts()
    lines = ['%d jobs: %s' % (len(queue), ', '.join('%d %s' % (counts[s], s) for s in STATES))]
    for job in queue.jobs():
        if job.state == 'failed':
            lines.append('  failed  %s (%s): %s' % (job.id, job.kind, job.error))
    for job in queue.jobs():
        if job.state == 'queued':
            lines.append('  waiting %s (%s)' % (job.id, job.kind))
    return '\n'.join(lines)


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog='jobrun')
    sub = parser.add_subparsers(dest='command')
    report = sub.add_parser('report', help='summarize a journal')
    report.add_argument('journal')
    args = parser.parse_args(argv)
    if args.command != 'report':
        parser.print_help(out)
        return 2
    out.write(summarize(JobQueue(args.journal)) + '\n')
    return 0
