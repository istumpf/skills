#!/usr/bin/env python3
"""Collect unhandled feedback for a stacked PR chain as JSON.

Rebuilds all state from GitHub and local Git on every run: the stack comes from
PR base/head links, and handled feedback is recognized by resolved threads or
by replies carrying MARKER. Needs `gh` (authenticated) and the stack's branches
fetched locally for owner attribution.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys

MARKER = "<!-- stacked-pr-feedback -->"
PR_FIELDS = "number,url,headRefName,baseRefName,headRefOid,state,title"
QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviews(first: 100) {
        totalCount
        nodes { id state body url submittedAt author { login } }
      }
      comments(first: 100) {
        totalCount
        nodes { id body url createdAt author { login } }
      }
      reviewThreads(first: 100) {
        totalCount
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first: 50) {
            nodes { id databaseId body url createdAt author { login } }
          }
        }
      }
    }
  }
}
"""


def run(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def gh_json(args, cwd=None):
    return json.loads(run(["gh", *args], cwd))


def build_stack(prs, start):
    """Return the chain of PRs containing `start`, ordered from trunk upward."""
    by_head = {pr["headRefName"]: pr for pr in prs}
    by_base = {}
    for pr in prs:
        by_base.setdefault(pr["baseRefName"], []).append(pr)
    current = next((pr for pr in prs if start in (str(pr["number"]), pr["headRefName"], pr["url"])), None)
    if current is None:
        raise ValueError(f"No open PR matches {start!r}")
    chain = [current]
    while chain[0]["baseRefName"] in by_head:
        chain.insert(0, by_head[chain[0]["baseRefName"]])
    while True:
        children = by_base.get(chain[-1]["headRefName"], [])
        if len(children) != 1:
            # Zero children ends the stack; several mean a branching tree the caller must choose from.
            if len(children) > 1:
                raise ValueError("Stack branches above #%d: %s" % (
                    chain[-1]["number"], ", ".join("#%d" % c["number"] for c in children)))
            return chain
        chain.append(children[0])


def author(node):
    return (node.get("author") or {}).get("login", "ghost")


def handled_comment_urls(nodes):
    """URLs our earlier top-level replies answered, via `in-reply-to: <url>` lines."""
    urls = set()
    for node in nodes:
        if MARKER in node["body"]:
            for line in node["body"].splitlines():
                if line.startswith("in-reply-to: "):
                    urls.add(line.split(" ", 1)[1].strip())
    return urls


def feedback_items(pr, data):
    items = []
    replies = data["comments"]["nodes"]
    answered = handled_comment_urls(replies)
    for thread in data["reviewThreads"]["nodes"]:
        comments = thread["comments"]["nodes"]
        if thread["isResolved"] or not comments or MARKER in comments[-1]["body"]:
            continue
        items.append({
            "id": thread["id"], "pr": pr["number"], "source": "thread",
            "author": author(comments[0]), "url": comments[0]["url"],
            "reply_to": comments[0]["databaseId"],
            "path": thread["path"], "line": thread["line"] or thread["originalLine"],
            "outdated": thread["isOutdated"],
            "comments": [{"author": author(c), "body": c["body"]} for c in comments],
        })
    for review in data["reviews"]["nodes"]:
        if review["body"].strip() and MARKER not in review["body"] and review["url"] not in answered:
            items.append({"id": review["id"], "pr": pr["number"], "source": "review",
                          "author": author(review), "url": review["url"], "state": review["state"],
                          "comments": [{"author": author(review), "body": review["body"]}]})
    for comment in replies:
        if MARKER not in comment["body"] and comment["url"] not in answered:
            items.append({"id": comment["id"], "pr": pr["number"], "source": "comment",
                          "author": author(comment), "url": comment["url"],
                          "comments": [{"author": author(comment), "body": comment["body"]}]})
    return items


def truncated(data):
    return [key for key in ("reviews", "comments", "reviewThreads")
            if data[key]["totalCount"] > len(data[key]["nodes"])]


def owner_pr(stack, path, line, ref, cwd=None):
    """Lowest PR whose own commits introduced `path:line` at `ref`, or None if it predates the stack."""
    if not path or not line:
        return None
    try:
        blame = run(["git", "blame", "--porcelain", "-L", f"{line},{line}", ref, "--", path], cwd)
    except subprocess.CalledProcessError:
        return None
    commit = blame.split()[0]
    for pr in stack:
        inside_head = subprocess.run(["git", "merge-base", "--is-ancestor", commit, pr["headRefOid"]],
                                     cwd=cwd).returncode == 0
        inside_base = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "origin/" + pr["baseRefName"]],
                                     cwd=cwd).returncode == 0
        if inside_head and not inside_base:
            return pr["number"]
    return None


def needs_sync(stack, merged):
    """The bottom PR targets a branch whose PR already merged: retarget and rebase it."""
    merged_heads = {pr["headRefName"]: pr["number"] for pr in merged}
    base = stack[0]["baseRefName"]
    return {"pr": stack[0]["number"], "merged_parent": merged_heads[base]} if base in merged_heads else None


def collect(start, local=None, cwd=None):
    info = gh_json(["repo", "view", "--json", "nameWithOwner,defaultBranchRef"], cwd)
    repo = info["nameWithOwner"]
    owner, name = repo.split("/")
    prs = gh_json(["pr", "list", "--state", "open", "--limit", "200", "--json", PR_FIELDS], cwd)
    merged = gh_json(["pr", "list", "--state", "merged", "--limit", "50", "--json", PR_FIELDS], cwd)
    if not any(start in (str(pr["number"]), pr["headRefName"], pr["url"]) for pr in prs):
        done = next((pr for pr in merged if start in (str(pr["number"]), pr["headRefName"], pr["url"])), None)
        if done:
            # The whole stack up to `start` has merged: nothing left to handle.
            return {"repository": repo, "trunk": info["defaultBranchRef"]["name"], "stack": [],
                    "merged": done["number"], "sync": None, "items": [], "warnings": []}
    stack = build_stack(prs, start)
    items, warnings = [], []
    for pr in stack:
        data = gh_json(["api", "graphql", "-f", "query=" + QUERY, "-F", "owner=" + owner,
                        "-F", "name=" + name, "-F", "number=%d" % pr["number"]], cwd)
        data = data["data"]["repository"]["pullRequest"]
        for key in truncated(data):
            warnings.append("#%d has more %s than fetched; check the PR page" % (pr["number"], key))
        items.extend(feedback_items(pr, data))
    if local:
        for finding in json.loads(Path(local).read_text()):
            items.append({"source": "local", **finding})
    heads = {pr["number"]: pr["headRefOid"] for pr in stack}
    for item in items:
        if item.get("path") and item.get("pr") in heads:
            item["owner_pr"] = owner_pr(stack, item["path"], item.get("line"), heads[item["pr"]], cwd)
    return {
        "repository": repo,
        "trunk": info["defaultBranchRef"]["name"],
        "stack": [{k: pr[k] for k in ("number", "url", "headRefName", "baseRefName", "headRefOid")}
                  for pr in stack],
        "merged": None,
        "sync": needs_sync(stack, merged),
        "items": items,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("start", nargs="?", help="any PR in the stack (number, URL, or head branch); "
                        "defaults to the current branch")
    parser.add_argument("--local", help="JSON list of local review findings to triage with GitHub feedback")
    args = parser.parse_args()
    start = args.start or run(["git", "branch", "--show-current"])
    try:
        print(json.dumps(collect(start, args.local), indent=2))
    except (ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"collect_feedback: {error}")


if __name__ == "__main__":
    main()
