import unittest

from app import app


class CompilerWorkflowTests(unittest.TestCase):
	def setUp(self):
		self.client = app.test_client()

	def compile(self, source):
		return self.client.post("/compile", json={"source": source})

	def test_homepage_and_static_assets_load(self):
		page = self.client.get("/")
		self.assertEqual(page.status_code, 200)
		self.assertIn(b"Variable declaration", page.data)
		script = self.client.get("/static/script.js")
		stylesheet = self.client.get("/static/style.css")
		self.assertEqual(script.status_code, 200)
		self.assertEqual(stylesheet.status_code, 200)
		self.assertIn(b"fetch(\"/compile\"", script.data)
		self.assertIn(b"--forest", stylesheet.data)
		script.close()
		stylesheet.close()

	def test_full_compilation_returns_tokens_ast_and_symbols(self):
		response = self.compile("int age = 20;\nfloat mark = 95.5;\nage = 21;")
		data = response.get_json()
		self.assertEqual(response.status_code, 200)
		self.assertTrue(data["success"])
		self.assertEqual(data["phase"], "complete")
		self.assertEqual(data["ast"]["type"], "Program")
		self.assertEqual(data["stats"]["statement_count"], 3)
		self.assertEqual(data["symbols"]["age"]["value"], 21)
		self.assertEqual(data["symbols"]["mark"]["type"], "float")
		self.assertTrue(any(token["type"] == "NUMBER" for token in data["tokens"]))

	def test_empty_program_is_valid(self):
		data = self.compile("").get_json()
		self.assertTrue(data["success"])
		self.assertEqual(data["stats"]["statement_count"], 0)
		self.assertEqual(data["symbols"], {})

	def test_syntax_error_has_phase_and_location(self):
		data = self.compile("int amount = 3").get_json()
		self.assertFalse(data["success"])
		self.assertEqual(data["phase"], "syntax")
		self.assertEqual(data["error"]["line"], 1)
		self.assertIn("Expected ';'", data["error"]["message"])

	def test_lexical_error_is_reported(self):
		data = self.compile("int count = 2 @ 4;").get_json()
		self.assertEqual(data["phase"], "lexical")
		self.assertEqual(data["error"]["column"], 15)

	def test_semantic_errors_cover_undeclared_duplicate_and_type_mismatch(self):
		undeclared = self.compile("score = 4;").get_json()
		self.assertEqual(undeclared["phase"], "semantic")
		self.assertIn("not declared", undeclared["error"]["message"])

		duplicate = self.compile("int score; int score;").get_json()
		self.assertIn("already declared", duplicate["error"]["message"])

		mismatch = self.compile("bool ready = 8;").get_json()
		self.assertIn("Cannot assign int to bool", mismatch["error"]["message"])

	def test_variable_references_and_numeric_widening(self):
		data = self.compile("int count = 12; float weight = count; weight = 13.5;").get_json()
		self.assertTrue(data["success"])
		self.assertEqual(data["symbols"]["weight"]["value"], 13.5)

	def test_request_validation(self):
		missing = self.client.post("/compile", json={})
		self.assertEqual(missing.status_code, 400)
		oversized = self.compile("x" * 20001)
		self.assertEqual(oversized.status_code, 413)


if __name__ == "__main__":
	unittest.main()
