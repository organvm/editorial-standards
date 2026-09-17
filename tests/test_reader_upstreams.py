import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "upstreams", Path(__file__).parents[1] / "scripts/check_reader_upstreams.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class UpstreamTests(unittest.TestCase):
    def fake(self, path):
        identities = {repo_id: (f"owner/repo-{repo_id}", "main")
                      for _, repo_id, _ in module.UPSTREAMS}
        if path.startswith("repositories/"):
            repo_id = int(path.split("/", 1)[1])
            full_name, branch = identities[repo_id]
            return {"id": repo_id, "full_name": full_name, "default_branch": branch}
        if "/pulls/" in path:
            repo = path.split("repos/", 1)[1].split("/pulls/", 1)[0]
            repo_id = next(key for key, value in identities.items() if value[0] == repo)
            return {"merged": True, "merge_commit_sha": "a" * 40,
                    "base": {"repo": {"id": repo_id}}}
        if "/commits/" in path:
            return {"sha": "b" * 40}
        if "/compare/" in path:
            return {"status": "ahead"}
        raise AssertionError(path)

    def test_missing_executable_is_unmeasured_and_redacted(self):
        def get(path):
            raise FileNotFoundError("PRIVATE_EXECUTABLE_PATH")
        report = module.inspect(get)
        self.assertEqual(report["status"], "unmeasured")
        self.assertNotIn("PRIVATE_EXECUTABLE_PATH", str(report))
        self.assertEqual(len(report["inputs"]), 3)

    def test_repository_identity_must_match_pull_base(self):
        def get(path):
            value = self.fake(path)
            if "/pulls/" in path:
                value["base"]["repo"]["id"] += 1
            return value
        self.assertEqual(module.inspect(get)["status"], "unmeasured")

    def test_default_branch_change_invalidates_snapshot(self):
        calls = {}
        def get(path):
            value = self.fake(path)
            if path.startswith("repositories/"):
                calls[path] = calls.get(path, 0) + 1
                if calls[path] > 1:
                    value["default_branch"] = "replacement"
            return value
        self.assertEqual(module.inspect(get)["status"], "unmeasured")

    def test_accepted_inputs_are_immutable_refs(self):
        report = module.inspect(self.fake)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(len(report["inputs"]), 3)
        self.assertTrue(all(r["merge_commit"] == "a" * 40 for r in report["inputs"]))
        self.assertTrue(all(type(r["repository_id"]) is int for r in report["inputs"]))

    def test_unmerged_and_nonboolean_are_not_accepted(self):
        for merged in (False, 1, "true", None):
            def get(path):
                value = self.fake(path)
                if "/pulls/" in path:
                    value["merged"] = merged
                return value
            self.assertEqual(module.inspect(get)["status"], "unmeasured")

    def test_diverged_default_does_not_accept_closed_pr(self):
        def get(path):
            return {"status": "diverged"} if "/compare/" in path else self.fake(path)
        self.assertEqual(module.inspect(get)["status"], "unmeasured")

    def test_failure_is_redacted_and_other_inputs_still_inspected(self):
        seen = []
        first_id = module.UPSTREAMS[0][1]
        def get(path):
            seen.append(path)
            if path == f"repositories/{first_id}":
                raise ValueError("PRIVATE_CREDENTIAL")
            return self.fake(path)
        report = module.inspect(get)
        self.assertNotIn("PRIVATE_CREDENTIAL", str(report))
        self.assertEqual(report["inputs"][-1]["status"], "accepted")

    def test_head_movement_rejects_observation(self):
        calls = {}
        def get(path):
            if "/commits/" in path:
                calls[path] = calls.get(path, 0) + 1
                return {"sha": ("b" if calls[path] == 1 else "c") * 40}
            return self.fake(path)
        self.assertEqual(module.inspect(get)["status"], "unmeasured")

    def test_repository_rename_invalidates_snapshot(self):
        calls = {}
        def get(path):
            value = self.fake(path)
            if path.startswith("repositories/"):
                calls[path] = calls.get(path, 0) + 1
                if calls[path] > 1:
                    value["full_name"] += "-renamed"
            return value
        self.assertEqual(module.inspect(get)["status"], "unmeasured")

    def test_every_github_read_pins_public_host(self):
        def run(command, **kwargs):
            return module.subprocess.CompletedProcess(
                command, 0, stdout=module.json.dumps(self.fake(command[-1])))

        with patch.dict(os.environ, {"GH_HOST": "github.enterprise.invalid"}):
            with patch.object(module.subprocess, "run", side_effect=run) as request:
                report = module.inspect(module.github)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(request.call_count, 6 * len(module.UPSTREAMS))
        for invocation in request.call_args_list:
            self.assertEqual(invocation.args[0][:4],
                             ["gh", "api", "--hostname", "github.com"])
            self.assertEqual(invocation.kwargs,
                             {"capture_output": True, "text": True, "timeout": 15})
