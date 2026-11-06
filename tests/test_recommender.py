import unittest
from pathlib import Path

from app import create_app
from backend.chatbot import handle_chat
from backend.recommender import load_schemes, recommend_schemes


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "government_schemes.csv"


class RecommenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemes = load_schemes(DATA_PATH)

    def test_dataset_has_100_distinct_records_and_categories(self):
        self.assertEqual(len(self.schemes), 100)
        self.assertEqual(len({item["scheme_id"] for item in self.schemes}), 100)
        self.assertEqual(len({item["scheme_name"] for item in self.schemes}), 100)
        self.assertGreaterEqual(len({item["category"] for item in self.schemes}), 8)

    def test_recommendations_explain_matches_and_unknowns(self):
        results = recommend_schemes(self.schemes, {
            "interests": ["Agriculture"], "age": 35, "state": "Maharashtra", "occupation": "Farmer"
        })
        self.assertTrue(results)
        self.assertTrue(any("Kisan Samman Nidhi" in item["scheme_name"] for item in results))
        self.assertTrue(all(item["relevance_score"] > 0 and item["recommendation_reasons"] for item in results))
        self.assertTrue(any(item["verification_notes"] for item in results))

    def test_explicit_age_limit_excludes_ineligible_candidate(self):
        scheme = {
            "scheme_id": "TEST", "scheme_name": "Age-limited programme", "government_department": "Test",
            "category": "Education and scholarships", "description": "Test", "eligibility_criteria": "Unknown - verify",
            "minimum_age": "18", "maximum_age": "25", "gender_eligibility": "All genders",
            "income_limit": "Unknown - verify", "state_eligibility": "All India",
            "education_requirement": "Unknown - verify", "occupation_requirement": "Unknown - verify",
            "benefits": "Unknown - verify", "application_process": "Unknown - verify",
            "official_website": "https://example.gov.in", "required_documents": "Unknown - verify",
            "verification_status": "Test", "source_note": "Test",
        }
        self.assertEqual(recommend_schemes([scheme], {"age": 40}), [])

    def test_invalid_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Age must be between"):
            recommend_schemes(self.schemes, {"age": 121})

    def test_category_does_not_match_unrelated_eligibility_prose(self):
        results = recommend_schemes(self.schemes, {"category": "General"})
        self.assertTrue(results)
        self.assertNotIn("EDU010", {item["scheme_id"] for item in results})

    def test_employment_status_can_match_occupation_when_unspecified(self):
        results = recommend_schemes(self.schemes, {"employment_status": "Student"})
        self.assertIn("EDU001", {item["scheme_id"] for item in results})


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.schemes = load_schemes(DATA_PATH)
        self.client = create_app(DATA_PATH).test_client()

    def test_home_and_scheme_list(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.get("/api/schemes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 100)

    def test_recommend_validation_and_response(self):
        self.assertEqual(self.client.post("/api/recommend", json={}).status_code, 400)
        response = self.client.post("/api/recommend", json={"profile": {"interests": ["Agriculture"]}})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.get_json()["count"], 0)

    def test_chat_flow_and_details(self):
        response = self.client.post("/api/chat", json={"message": "", "profile": {}, "stage": "start"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stage"], "interests")
        self.assertEqual(self.client.get("/api/scheme/AGR001").status_code, 200)
        self.assertEqual(self.client.get("/api/scheme/not-real").status_code, 404)

    def test_complete_conversation_returns_explained_recommendations(self):
        profile = {}
        start = self.client.post("/api/chat", json={"message": "", "profile": profile, "stage": "start"})
        self.assertEqual(start.status_code, 200)
        stage = start.get_json()["stage"]
        answers = ["Agriculture", "35", "Maharashtra", "Woman", "500000", "Secondary", "Farmer", "Farmer", "Prefer not to say"]
        for answer in answers:
            response = self.client.post("/api/chat", json={"message": answer, "profile": profile, "stage": stage})
            self.assertEqual(response.status_code, 200)
            result = response.get_json()
            profile = result["profile"]
            stage = result["stage"]
        self.assertEqual(stage, "complete")
        self.assertIn("recommendations", result)
        follow_up = self.client.post("/api/chat", json={
            "message": "Why was this recommended?", "profile": profile, "stage": "complete"
        })
        self.assertEqual(follow_up.status_code, 200)
        self.assertIn("verification", follow_up.get_json()["reply"].lower())

    def test_chat_rejects_malformed_answers_without_advancing(self):
        invalid_answers = [
            ("interests", "hello"),
            ("interests", "sports"),
            ("age", "I am 35, my phone is 123456"),
            ("state", "Narnia"),
            ("gender", "Other"),
            ("education", "Doctorate"),
            ("occupation", "12345"),
        ]
        for stage, message in invalid_answers:
            with self.subTest(stage=stage, message=message):
                result = handle_chat(message, {}, stage, self.schemes)
                self.assertEqual(result["stage"], stage)
                self.assertNotIn(stage, result["profile"])
                self.assertTrue(result["reply"])

    def test_numeric_answers_are_whole_and_not_partially_extracted(self):
        age = handle_chat("35 years old", {}, "age", self.schemes)
        self.assertEqual(age["profile"]["age"], 35)
        income = handle_chat("Rs. 5,00,000 per year", {}, "annual_income", self.schemes)
        self.assertEqual(income["profile"]["annual_income"], 500000)
        invalid = handle_chat("income is 500000 maybe", {}, "annual_income", self.schemes)
        self.assertEqual(invalid["stage"], "annual_income")
        self.assertNotIn("annual_income", invalid["profile"])

    def test_location_is_normalized_and_typed_skip_works(self):
        location = handle_chat("I live in maharashtra", {}, "state", self.schemes)
        self.assertEqual(location["profile"]["state"], "Maharashtra")
        skipped = handle_chat("skip", {}, "annual_income", self.schemes)
        self.assertEqual(skipped["stage"], "education")
        self.assertNotIn("annual_income", skipped["profile"])

    def test_unrecognized_follow_up_does_not_claim_to_answer(self):
        response = handle_chat("how are you", {}, "complete", self.schemes)
        self.assertIn("explain why", response["reply"])
        self.assertEqual(response["stage"], "complete")

    def test_chat_rejects_malformed_input(self):
        self.assertEqual(self.client.post("/api/chat", data="bad", content_type="application/json").status_code, 400)


if __name__ == "__main__":
    unittest.main()