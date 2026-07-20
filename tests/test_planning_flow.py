import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


TEST_DB = Path(tempfile.gettempdir()) / "weouc_planning_test.sqlite"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["MYSQL_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["LLM_PROVIDER"] = "none"
os.environ["INTEGRATION_TOKEN"] = "test-integration-token"

from fastapi.testclient import TestClient

from app.database.mysql import Base, engine
from app.main import app


class PlanningFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.integration_headers = {"X-Integration-Token": "test-integration-token"}

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if TEST_DB.exists():
            TEST_DB.unlink()

    def test_standardized_planning_end_to_end(self):
        capabilities = self.client.get("/api/v1/capabilities")
        self.assertEqual(capabilities.status_code, 200)
        self.assertTrue(capabilities.json()["modules"]["course_planning"])
        self.assertFalse(capabilities.json()["modules"]["course_feedback"])

        empty_context_response = self.client.get(
            "/api/v1/planning/context",
            params={"tenant_id": "weouc", "user_id": "student-1"},
        )
        self.assertEqual(empty_context_response.status_code, 200)
        empty_context = empty_context_response.json()
        self.assertFalse(empty_context["available"])
        self.assertIn("course_offering_snapshot", empty_context["missing"])
        self.assertIn("programme_version", empty_context["missing"])

        programme_response = self.client.post(
            "/api/v1/integrations/programme-versions",
            headers=self.integration_headers,
            json={
                "tenant_id": "weouc",
                "programme_code": "CS",
                "programme_name": "计算机科学与技术",
                "version_code": "2024",
                "applicable_grades": ["2024"],
                "issuing_unit": "信息科学与工程学部",
                "rules": [
                    {
                        "rule_code": "GE-POOL",
                        "rule_type": "elective_pool",
                        "course_category": "通识选修",
                    }
                ],
            },
        )
        self.assertEqual(programme_response.status_code, 200, programme_response.text)
        programme_version_id = programme_response.json()["programme_version_id"]

        programme_options = self.client.get(
            "/api/v1/student/programmes",
            params={"tenant_id": "weouc", "grade": "2024级", "major": "计算机科学与技术"},
        )
        self.assertEqual(programme_options.status_code, 200, programme_options.text)
        self.assertEqual(programme_options.json()[0]["id"], programme_version_id)

        save_profile = self.client.put(
            "/api/v1/student/profile",
            json={
                "tenant_id": "weouc",
                "user_id": "student-1",
                "grade": "2024级",
                "department": "信息科学与工程学部",
                "major": "计算机科学与技术",
                "programme_version_id": programme_version_id,
            },
        )
        self.assertEqual(save_profile.status_code, 200, save_profile.text)
        self.assertEqual(save_profile.json()["programme_version_id"], programme_version_id)

        get_profile = self.client.get(
            "/api/v1/student/profile",
            params={"tenant_id": "weouc", "user_id": "student-1"},
        )
        self.assertEqual(get_profile.status_code, 200, get_profile.text)
        self.assertEqual(get_profile.json()["major"], "计算机科学与技术")

        generated_at = datetime.now(timezone.utc).isoformat()
        snapshot_payload = {
            "tenant_id": "weouc",
            "semester": "2026-2027-1",
            "snapshot_id": "weouc-2026-2027-1-v1",
            "generated_at": generated_at,
            "courses": [
                {
                    "external_offering_id": "section-c001",
                    "course_code": "C001",
                    "course_name": "大学英语Ⅲ",
                    "credits": 2,
                    "course_category": "通识选修",
                    "campus": "崂山校区",
                    "teacher_name": "张老师",
                    "schedules": [{"weekday": 2, "periods": [5, 6], "weeks": "1-16"}],
                    "remaining_capacity": 20,
                    "source_updated_at": generated_at,
                },
                {
                    "external_offering_id": "section-c002",
                    "course_code": "C002",
                    "course_name": "人工智能导论",
                    "credits": 2,
                    "course_category": "通识选修",
                    "campus": "崂山校区",
                    "teacher_name": "李老师",
                    "schedules": [{"weekday": 2, "periods": [5, 6], "weeks": "1-16"}],
                    "remaining_capacity": 30,
                    "source_updated_at": generated_at,
                },
                {
                    "external_offering_id": "section-c003",
                    "course_code": "C003",
                    "course_name": "海洋科学概论",
                    "credits": 2,
                    "course_category": "通识选修",
                    "campus": "鱼山校区",
                    "teacher_name": "王老师",
                    "schedules": [{"weekday": 2, "periods": [5, 6], "weeks": "1-16"}],
                    "remaining_capacity": 40,
                    "source_updated_at": generated_at,
                },
            ],
        }
        snapshot_response = self.client.post(
            "/api/v1/integrations/course-offering-snapshots",
            headers=self.integration_headers,
            json=snapshot_payload,
        )
        self.assertEqual(snapshot_response.status_code, 200, snapshot_response.text)
        snapshot_id = snapshot_response.json()["snapshot_db_id"]

        planning_context_response = self.client.get(
            "/api/v1/planning/context",
            params={"tenant_id": "weouc", "user_id": "student-1"},
        )
        self.assertEqual(
            planning_context_response.status_code,
            200,
            planning_context_response.text,
        )
        planning_context = planning_context_response.json()
        self.assertTrue(planning_context["available"])
        self.assertEqual(planning_context["snapshot"]["id"], snapshot_id)
        self.assertEqual(
            planning_context["programme"]["id"],
            programme_version_id,
        )
        self.assertTrue(planning_context["programme"]["confirmed"])

        replay = self.client.post(
            "/api/v1/integrations/course-offering-snapshots",
            headers=self.integration_headers,
            json=snapshot_payload,
        )
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertTrue(replay.json()["idempotent_replay"])
        self.assertEqual(replay.json()["snapshot_db_id"], snapshot_id)

        conflicting_payload = {**snapshot_payload, "courses": [*snapshot_payload["courses"]]}
        conflicting_payload["courses"][0] = {
            **conflicting_payload["courses"][0],
            "course_name": "被修改的课程名称",
        }
        conflict = self.client.post(
            "/api/v1/integrations/course-offering-snapshots",
            headers=self.integration_headers,
            json=conflicting_payload,
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)

        csv_content = "课程号,课程名称,学期,学分\nC001,大学英语Ⅲ,2025-2026-1,2\n"
        history_response = self.client.post(
            "/api/v1/academic-history/imports",
            headers={"X-Tenant-Id": "weouc", "X-User-Id": "student-1"},
            files={"file": ("history.csv", csv_content.encode("utf-8-sig"), "text/csv")},
        )
        self.assertEqual(history_response.status_code, 200, history_response.text)
        history = history_response.json()
        self.assertEqual(history["status"], "needs_confirmation")
        self.assertEqual(history["records"][0]["completion_status"], "assumed_passed")
        self.assertEqual(history["records"][0]["matched_course_id"], 1)

        confirm_history = self.client.post(
            f"/api/v1/academic-history/imports/{history['import_id']}/confirm",
            headers={"X-Tenant-Id": "weouc", "X-User-Id": "student-1"},
            json={"corrections": []},
        )
        self.assertEqual(confirm_history.status_code, 200, confirm_history.text)
        self.assertEqual(confirm_history.json()["status"], "confirmed")

        saved_history = self.client.get(
            "/api/v1/academic-history/records",
            headers={"X-Tenant-Id": "weouc", "X-User-Id": "student-1"},
        )
        self.assertEqual(saved_history.status_code, 200, saved_history.text)
        self.assertEqual(saved_history.json()["record_count"], 1)

        planning_response = self.client.post(
            "/api/v1/planning/sessions",
            json={
                "tenant_id": "weouc",
                "user_id": "student-1",
                "snapshot_id": snapshot_id,
                "programme_version_id": programme_version_id,
                "query": "推荐周二崂山校区、作业少的通识选修课",
            },
        )
        self.assertEqual(planning_response.status_code, 200, planning_response.text)
        planning = planning_response.json()
        self.assertEqual(planning["state"], "awaiting_confirmation")
        self.assertIn("workload", planning["requirements"]["unsupported_preferences"])

        recommendation_response = self.client.post(
            f"/api/v1/planning/sessions/{planning['session_id']}/requirements/confirm",
            json={
                "constraints": planning["requirements"]["constraints"],
                "preferences": planning["requirements"]["preferences"],
            },
        )
        self.assertEqual(
            recommendation_response.status_code, 200, recommendation_response.text
        )
        recommendation = recommendation_response.json()
        self.assertEqual(recommendation["total_candidates"], 1)
        self.assertEqual(recommendation["recommendations"][0]["course_code"], "C002")
        self.assertTrue(any("workload" in warning for warning in recommendation["warnings"]))
        evidence = recommendation["recommendations"][0]["evidence"][0]
        self.assertEqual(evidence["source_tier"], "official_structured_snapshot")
        self.assertEqual(evidence["field_completeness"], "complete")
        self.assertEqual(evidence["freshness"], "current")

        offering_id = recommendation["recommendations"][0]["offering_id"]
        course_detail = self.client.get(
            f"/api/v1/catalog/offerings/{offering_id}",
            params={"tenant_id": "weouc", "user_id": "student-1"},
        )
        self.assertEqual(course_detail.status_code, 200, course_detail.text)
        self.assertEqual(course_detail.json()["course_code"], "C002")
        self.assertEqual(course_detail.json()["snapshot"]["id"], snapshot_id)
        self.assertEqual(
            course_detail.json()["programme_relationship"]["type"],
            "elective_pool",
        )
        self.assertIsNone(course_detail.json()["history"])

        self.assertEqual(self.client.get("/prototype/history.html").status_code, 200)
        self.assertEqual(self.client.get("/prototype/course.html").status_code, 200)

        correction_parse = self.client.post(
            "/api/v1/planning/sessions",
            json={
                "tenant_id": "weouc",
                "user_id": "student-1",
                "snapshot_id": snapshot_id,
                "programme_version_id": programme_version_id,
                "query": "大学英语Ⅲ我挂了",
            },
        )
        self.assertEqual(correction_parse.status_code, 200, correction_parse.text)
        correction = correction_parse.json()
        self.assertEqual(correction["state"], "awaiting_history_confirmation")
        candidate = correction["requirements"]["history_correction_candidates"][0]
        self.assertEqual(candidate["proposed_status"], "failed")

        correction_confirm = self.client.post(
            "/api/v1/planning/history-corrections/confirm",
            json={
                "tenant_id": "weouc",
                "user_id": "student-1",
                "record_id": candidate["record_id"],
                "status": "failed",
            },
        )
        self.assertEqual(correction_confirm.status_code, 200, correction_confirm.text)
        self.assertEqual(correction_confirm.json()["completion_status"], "failed")

    def test_requirement_contract_rejects_unsupported_or_invalid_values(self):
        invalid_items = [
            {"type": "unknown_filter", "operator": "eq", "value": "x"},
            {"type": "weekday", "operator": "eq", "value": 8},
            {"type": "credits", "operator": "contains", "value": 2},
            {"type": "avoid_period", "operator": "neq", "value": 0},
            {"type": "campus", "operator": "contains", "value": ""},
        ]
        for item in invalid_items:
            response = self.client.post(
                "/api/v1/planning/sessions/missing/requirements/confirm",
                json={"constraints": [item], "preferences": []},
            )
            self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
