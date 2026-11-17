"""Exercise the stacked-pr-feedback collector with canned GitHub data and a real Git stack."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "skills/stacked-pr-feedback/scripts/collect_feedback.py"
spec = importlib.util.spec_from_file_location("collect_feedback", SCRIPT)
collect_feedback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect_feedback)
MARKER = collect_feedback.MARKER


def pr(number, head, base, oid="0" * 40):
    return {"number": number, "url": f"https://example.invalid/pull/{number}", "headRefName": head,
            "baseRefName": base, "headRefOid": oid, "state": "OPEN", "title": head}


def comment(body, login="reviewer", url="u", database_id=1):
    return {"id": url, "databaseId": database_id, "body": body, "url": url,
            "createdAt": "2026-11-03T00:00:00Z", "author": {"login": login}}


def review(body, url, state="COMMENTED"):
    return {**comment(body, url=url), "state": state}


def thread(comments, resolved=False, outdated=False, path="invoice.py", line=3):
    return {"id": "T" + comments[0]["url"], "isResolved": resolved, "isOutdated": outdated,
            "path": path, "line": line, "originalLine": line, "comments": {"nodes": comments}}


def pr_data(threads=(), reviews=(), comments=()):
    return {"reviews": {"totalCount": len(reviews), "nodes": list(reviews)},
            "comments": {"totalCount": len(comments), "nodes": list(comments)},
            "reviewThreads": {"totalCount": len(threads), "nodes": list(threads)}}


class BuildStackTests(unittest.TestCase):
    prs = [pr(3, "g3", "g2"), pr(1, "g1", "main"), pr(2, "g2", "g1"), pr(9, "other", "main")]

    def test_orders_from_trunk_starting_anywhere(self):
        for start in ("2", "g3", "https://example.invalid/pull/1"):
            self.assertEqual([p["number"] for p in collect_feedback.build_stack(self.prs, start)], [1, 2, 3])

    def test_rejects_unknown_and_branching_stacks(self):
        with self.assertRaisesRegex(ValueError, "No open PR"):
            collect_feedback.build_stack(self.prs, "nope")
        with self.assertRaisesRegex(ValueError, "branches above #1"):
            collect_feedback.build_stack(self.prs + [pr(4, "g2b", "g1")], "1")


class FeedbackItemTests(unittest.TestCase):
    def test_skips_handled_feedback_and_keeps_the_rest(self):
        data = pr_data(
            threads=[
                thread([comment("fix rounding", url="t1", database_id=11)]),
                thread([comment("old", url="t2")], resolved=True),
                thread([comment("nit", url="t3"), comment("done\n" + MARKER, login="me", url="t3r")]),
                thread([comment("still wrong", url="t4"), comment("done\n" + MARKER, url="t4r"),
                        comment("no, still wrong", url="t4x")], outdated=True),
            ],
            reviews=[review("", "r-empty", "APPROVED"), review("please add tests", "r1", "CHANGES_REQUESTED"),
                     review("answered", "r2")],
            comments=[comment("general question", url="c1"),
                      comment("see commit\nin-reply-to: r2\n" + MARKER, login="me", url="c2")],
        )
        items = collect_feedback.feedback_items(pr(1, "g1", "main"), data)
        self.assertEqual([(i["source"], i["url"]) for i in items],
                         [("thread", "t1"), ("thread", "t4"), ("review", "r1"), ("comment", "c1")])
        self.assertEqual(items[0]["reply_to"], 11)
        self.assertTrue(items[1]["outdated"])
        self.assertEqual(len(items[1]["comments"]), 3)

    def test_edited_feedback_resurfaces_after_our_reply(self):
        later = "2026-11-04T00:00:00Z"
        mine = comment("done\n" + MARKER, login="me", url="t1r")
        mine["createdAt"] = "2026-11-03T12:00:00Z"
        edited = comment("nit", url="t1")
        edited["lastEditedAt"] = later
        rev = {**review("looks bad", "r1"), "lastEditedAt": later}
        issue = {**comment("summary", url="c1"), "lastEditedAt": later}
        stale = {**comment("summary", url="c3"), "lastEditedAt": "2026-11-03T06:00:00Z"}
        data = pr_data(
            threads=[thread([edited, mine])],
            reviews=[rev],
            comments=[issue, stale,
                      {**comment("ok\nin-reply-to: r1\n" + MARKER, login="me", url="c2"),
                       "createdAt": "2026-11-03T12:00:00Z"},
                      {**comment("ok\nin-reply-to: c1\nin-reply-to: c3\n" + MARKER, login="me", url="c4"),
                       "createdAt": "2026-11-03T12:00:00Z"}],
        )
        items = collect_feedback.feedback_items(pr(1, "g1", "main"), data)
        self.assertEqual([(i["source"], i["url"], i["edited"]) for i in items],
                         [("thread", "t1", True), ("review", "r1", True), ("comment", "c1", True)])

    def test_editing_our_reply_rehandles_an_edited_summary(self):
        summary = {**comment("walkthrough v2", url="c1"), "lastEditedAt": "2026-11-04T00:00:00Z"}
        ours = {**comment("ok\nin-reply-to: c1\n" + MARKER, login="me", url="c2", database_id=42),
                "createdAt": "2026-11-03T12:00:00Z"}
        items = collect_feedback.feedback_items(pr(1, "g1", "main"), pr_data(comments=[summary, ours]))
        self.assertEqual([(i["url"], i["edited"], i["our_reply"]) for i in items], [("c1", True, 42)])
        ours["lastEditedAt"] = "2026-11-04T01:00:00Z"
        self.assertEqual(collect_feedback.feedback_items(pr(1, "g1", "main"),
                                                         pr_data(comments=[summary, ours])), [])

    def test_thread_edited_before_our_reply_stays_handled(self):
        early = comment("nit", url="t1")
        early["lastEditedAt"] = "2026-11-03T06:00:00Z"
        mine = {**comment("done\n" + MARKER, login="me", url="t1r"), "createdAt": "2026-11-03T12:00:00Z"}
        items = collect_feedback.feedback_items(pr(1, "g1", "main"), pr_data(threads=[thread([early, mine])]))
        self.assertEqual(items, [])

    def test_reports_truncation(self):
        data = pr_data()
        data["reviewThreads"]["totalCount"] = 150
        self.assertEqual(collect_feedback.truncated(data), ["reviewThreads"])

    def test_needs_sync_after_parent_merge(self):
        stack = [pr(2, "g2", "g1")]
        self.assertEqual(collect_feedback.needs_sync(stack, [pr(1, "g1", "main")]),
                         {"pr": 2, "merged_parent": 1})
        self.assertIsNone(collect_feedback.needs_sync([pr(1, "g1", "main")], []))


class GitStackTests(unittest.TestCase):
    """Owner attribution and the full collector against a local stack: main <- g1 <- g2."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="stacked-feedback-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.repo = root / "repo"
        self.git("init", "--bare", "--initial-branch=main", str(root / "origin.git"), cwd=root)
        self.git("init", "--initial-branch=main", str(self.repo), cwd=root)
        for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                           ("commit.gpgsign", "false"), ("core.hooksPath", str(root / "no-hooks"))):
            self.git("config", key, value)
        self.git("remote", "add", "origin", str(root / "origin.git"))
        self.commit("main", ["CURRENCY = 'USD'"])
        self.git("switch", "-c", "g1")
        g1 = self.commit("g1", ["CURRENCY = 'USD'", "def parse(): pass"])
        self.git("switch", "-c", "g2")
        g2 = self.commit("g2", ["CURRENCY = 'USD'", "def parse(): pass", "def total(): pass"])
        self.git("push", "origin", "main", "g1", "g2")
        self.stack = [pr(1, "g1", "main", g1), pr(2, "g2", "g1", g2)]

    def git(self, *args, cwd=None):
        return subprocess.check_output(["git", *args], cwd=cwd or self.repo, text=True,
                                       stderr=subprocess.DEVNULL).strip()

    def commit(self, message, lines):
        (self.repo / "invoice.py").write_text("\n".join(lines) + "\n")
        self.git("add", "invoice.py")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def test_owner_is_the_pr_that_introduced_the_line(self):
        head = self.stack[1]["headRefOid"]
        owner = lambda line: collect_feedback.owner_pr(self.stack, "invoice.py", line, head, self.repo)
        self.assertIsNone(owner(1))  # Predates the stack.
        self.assertEqual(owner(2), 1)  # Commented on PR 2, introduced by PR 1.
        self.assertEqual(owner(3), 2)
        self.assertIsNone(collect_feedback.owner_pr(self.stack, "invoice.py", None, head, self.repo))

    def test_collect_merges_local_findings_and_attributes_owners(self):
        findings = self.repo.parent / "findings.json"
        findings.write_text(json.dumps([{"pr": 2, "path": "invoice.py", "line": 2, "body": "parse floats"}]))
        responses = {
            ("repo", "view"): {"nameWithOwner": "acme/app", "defaultBranchRef": {"name": "main"}},
            ("pr", "list", "open"): self.stack + [pr(7, "unrelated", "main")],
            ("pr", "list", "merged"): [],
        }

        def fake_gh(args, cwd=None):
            if args[0] == "api":
                number = int(args[-1].split("=")[1])
                threads = [thread([comment("total is wrong", url="t", database_id=5)], line=3)] if number == 2 else []
                return {"data": {"repository": {"pullRequest": pr_data(threads=threads)}}}
            key = tuple(args[:2]) + ((args[3],) if args[:2] == ["pr", "list"] else ())
            return responses[key]

        with mock.patch.object(collect_feedback, "gh_json", side_effect=fake_gh):
            result = collect_feedback.collect("g2", str(findings), cwd=self.repo)
        self.assertEqual(result["trunk"], "main")
        self.assertEqual([p["number"] for p in result["stack"]], [1, 2])
        self.assertIsNone(result["sync"])
        self.assertEqual([(i["source"], i["pr"], i["owner_pr"]) for i in result["items"]],
                         [("thread", 2, 2), ("local", 2, 1)])

    def test_fully_merged_stack_reports_done(self):
        responses = {
            ("repo", "view"): {"nameWithOwner": "acme/app", "defaultBranchRef": {"name": "main"}},
            ("pr", "list", "open"): [],
            ("pr", "list", "merged"): self.stack,
        }
        fake_gh = lambda args, cwd=None: responses[tuple(args[:2]) + ((args[3],) if args[:2] == ["pr", "list"] else ())]
        with mock.patch.object(collect_feedback, "gh_json", side_effect=fake_gh):
            result = collect_feedback.collect("g2", cwd=self.repo)
        self.assertEqual((result["stack"], result["items"], result["merged"]), ([], [], 2))
