#!/usr/bin/env python3
"""Offline original-surface review: validate, compare or package explicit files."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from phy_ref.glb import strict_json
from phy_ref.original_review import OriginalReview, json_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--draft',type=Path)
    parser.add_argument('--compare',type=Path)
    parser.add_argument('--packet',type=Path)
    parser.add_argument('--output',type=Path,help='write a deterministic packet or comparison JSON')
    args = parser.parse_args()
    ctx = OriginalReview(ROOT,args.original)
    def read(path,limit):
        if path.stat().st_size > limit: raise ValueError('Input exceeds byte budget')
        return strict_json(path.read_bytes())
    if args.packet:
        if args.draft or args.compare: parser.error('--packet is separate from --draft/--compare')
        result = ctx.validate_packet(read(args.packet,ctx.contract['max_packet_bytes']))
    elif args.draft:
        a = read(args.draft,ctx.contract['max_draft_bytes'])
        reviews = [a]
        if args.compare: reviews.append(read(args.compare,ctx.contract['max_draft_bytes']))
        packet = ctx.make_packet(reviews)
        result = packet['comparison'] or packet['validation'][0]
        if args.output: args.output.write_bytes(json_bytes(packet))
    else:
        if args.compare or args.output: parser.error('--draft is required for comparison/output')
        result = {'status':'pinned_original_verified_only','source_sha256':ctx.contract['source']['sha256']}
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__ == '__main__':
    try: main()
    except (ValueError,KeyError,TypeError,IndexError,OSError) as exc:
        print('Original review blocked: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
