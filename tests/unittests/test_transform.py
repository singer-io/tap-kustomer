import unittest

from tap_kustomer.transform import (
    convert,
    convert_array,
    convert_json,
    denest,
    denest_node_all_elements,
    denest_targeted_nodes,
    transform_json,
)


class TestConvert(unittest.TestCase):
    """Tests for camelCase to snake_case conversion."""

    def test_simple_camel_case(self):
        self.assertEqual(convert("camelCase"), "camel_case")

    def test_multiple_humps(self):
        self.assertEqual(convert("camelCaseString"), "camel_case_string")

    def test_already_snake_case(self):
        self.assertEqual(convert("snake_case"), "snake_case")

    def test_all_lowercase(self):
        self.assertEqual(convert("lowercase"), "lowercase")

    def test_abbreviation(self):
        self.assertEqual(convert("getHTTPResponse"), "get_http_response")

    def test_single_word(self):
        self.assertEqual(convert("Name"), "name")

    def test_leading_uppercase_word(self):
        self.assertEqual(convert("firstName"), "first_name")

    def test_numbers_in_name(self):
        self.assertEqual(convert("field2Value"), "field2_value")


class TestConvertArray(unittest.TestCase):
    """Tests for convert_array function."""

    def test_simple_values(self):
        self.assertEqual(convert_array([1, "abc", True]), [1, "abc", True])

    def test_nested_dict_in_array(self):
        result = convert_array([{"camelKey": "val"}])
        self.assertEqual(result, [{"camel_key": "val"}])

    def test_nested_list_in_array(self):
        result = convert_array([[{"innerKey": 1}]])
        self.assertEqual(result, [[{"inner_key": 1}]])

    def test_empty_array(self):
        self.assertEqual(convert_array([]), [])

    def test_mixed_types(self):
        result = convert_array([1, {"myKey": "v"}, [2], "str"])
        self.assertEqual(result, [1, {"my_key": "v"}, [2], "str"])


class TestConvertJson(unittest.TestCase):
    """Tests for convert_json function."""

    def test_flat_dict(self):
        result = convert_json({"firstName": "John", "lastName": "Doe"})
        self.assertEqual(result, {"first_name": "John", "last_name": "Doe"})

    def test_nested_dict(self):
        result = convert_json({"outerKey": {"innerKey": "val"}})
        self.assertEqual(result, {"outer_key": {"inner_key": "val"}})

    def test_dict_with_list_value(self):
        result = convert_json({"myList": [{"itemKey": 1}]})
        self.assertEqual(result, {"my_list": [{"item_key": 1}]})

    def test_non_dict_input_list(self):
        result = convert_json([{"camelKey": "val"}])
        self.assertEqual(result, [{"camel_key": "val"}])

    def test_empty_dict(self):
        self.assertEqual(convert_json({}), {})

    def test_deep_nesting(self):
        data = {"levelOne": {"levelTwo": {"levelThree": "value"}}}
        expected = {"level_one": {"level_two": {"level_three": "value"}}}
        self.assertEqual(convert_json(data), expected)


class TestDenestNodeAllElements(unittest.TestCase):
    """Tests for denest_node_all_elements function."""

    def test_denest_all_keys(self):
        new_json = {
            "data": [
                {
                    "id": "123",
                    "attributes": {
                        "name": "Test",
                        "email": "test@example.com",
                    },
                }
            ]
        }
        denest_node_all_elements(0, new_json["data"][0], "attributes", "data", new_json)
        self.assertEqual(new_json["data"][0]["name"], "Test")
        self.assertEqual(new_json["data"][0]["email"], "test@example.com")
        self.assertNotIn("attributes", new_json["data"][0])


class TestDenestTargetedNodes(unittest.TestCase):
    """Tests for denest_targeted_nodes function."""

    def test_denest_relationship_data(self):
        new_json = {
            "data": [
                {
                    "id": "123",
                    "relationships": {
                        "org": {
                            "data": {"type": "org", "id": "org-1"},
                            "links": {"self": "/v1/orgs/org-1"},
                        },
                        "team": {
                            "data": {"type": "team", "id": "team-1"},
                        },
                    },
                }
            ]
        }
        denest_targeted_nodes(0, "data", new_json["data"][0], new_json, "relationships.data")
        self.assertEqual(new_json["data"][0]["org"], {"type": "org", "id": "org-1"})
        self.assertEqual(new_json["data"][0]["team"], {"type": "team", "id": "team-1"})
        self.assertNotIn("relationships", new_json["data"][0])

    def test_sla_key_renamed_to_sla_data(self):
        new_json = {
            "data": [
                {
                    "id": "123",
                    "sla": {"version": 4, "matchedAt": "2019-01-01"},
                    "relationships": {
                        "sla": {
                            "data": {"type": "sla", "id": "sla-1"},
                        },
                    },
                }
            ]
        }
        denest_targeted_nodes(0, "data", new_json["data"][0], new_json, "relationships.data")
        # 'sla' relationship renamed to 'sla_data' to avoid collision
        self.assertIn("sla_data", new_json["data"][0])
        self.assertEqual(new_json["data"][0]["sla_data"], {"type": "sla", "id": "sla-1"})
        # Original 'sla' attribute preserved
        self.assertIn("sla", new_json["data"][0])
        self.assertEqual(new_json["data"][0]["sla"]["version"], 4)

    def test_target_key_missing_from_record(self):
        new_json = {
            "data": [{"id": "123", "other": {"foo": {"data": {"id": "x"}}}}]
        }
        # relationships key doesn't exist - should just pop it (KeyError-safe via 'if target_key in record')
        denest_targeted_nodes(0, "data", new_json["data"][0], new_json, "other.data")
        self.assertEqual(new_json["data"][0]["foo"], {"id": "x"})
        self.assertNotIn("other", new_json["data"][0])

    def test_non_dict_value_skipped(self):
        new_json = {
            "data": [
                {
                    "id": "123",
                    "relationships": {
                        "messages": {
                            "links": {"self": "/v1/messages"},
                        },
                    },
                }
            ]
        }
        # 'messages' value has no 'data' key, so nothing gets denested for it
        denest_targeted_nodes(0, "data", new_json["data"][0], new_json, "relationships.data")
        self.assertNotIn("relationships", new_json["data"][0])
        self.assertNotIn("messages", new_json["data"][0])


class TestDenest(unittest.TestCase):
    """Tests for denest function."""

    def test_denest_all_elements(self):
        data = {
            "data": [
                {"id": "1", "attributes": {"name": "A", "status": "active"}},
                {"id": "2", "attributes": {"name": "B", "status": "done"}},
            ]
        }
        result = denest(data, "data", "attributes")
        self.assertEqual(result["data"][0]["name"], "A")
        self.assertEqual(result["data"][1]["status"], "done")
        self.assertNotIn("attributes", result["data"][0])

    def test_denest_targeted(self):
        data = {
            "data": [
                {
                    "id": "1",
                    "relationships": {
                        "org": {"data": {"type": "org", "id": "org-1"}},
                    },
                }
            ]
        }
        result = denest(data, "data", "relationships.data")
        self.assertEqual(result["data"][0]["org"], {"type": "org", "id": "org-1"})

    def test_denest_multiple_keys_comma_separated(self):
        data = {
            "data": [
                {
                    "id": "1",
                    "attributes": {"name": "Test"},
                    "relationships": {
                        "org": {"data": {"id": "org-1"}},
                    },
                }
            ]
        }
        result = denest(data, "data", "attributes,relationships.data")
        self.assertEqual(result["data"][0]["name"], "Test")
        self.assertEqual(result["data"][0]["org"], {"id": "org-1"})
        self.assertNotIn("attributes", result["data"][0])
        self.assertNotIn("relationships", result["data"][0])

    def test_denest_empty_data_key(self):
        data = {"data": []}
        result = denest(data, "data", "attributes")
        self.assertEqual(result["data"], [])

    def test_denest_missing_data_key(self):
        data = {"other": "val"}
        result = denest(data, "data", "attributes")
        self.assertEqual(result, {"other": "val"})


class TestTransformJson(unittest.TestCase):
    """Tests for transform_json function."""

    def test_converts_keys_and_returns_data_key(self):
        data = {"data": [{"firstName": "John", "lastName": "Doe"}]}
        config = {}
        result = transform_json(data, config, "data")
        self.assertEqual(result, [{"first_name": "John", "last_name": "Doe"}])

    def test_no_data_key_returns_full_converted(self):
        data = {"firstName": "John"}
        config = {}
        result = transform_json(data, config, "")
        self.assertEqual(result, {"first_name": "John"})

    def test_with_denest_config(self):
        data = {
            "data": [
                {
                    "id": "1",
                    "attributes": {"displayName": "Test User", "active": True},
                }
            ]
        }
        config = {"denest": ["attributes"]}
        result = transform_json(data, config, "data")
        self.assertEqual(result[0]["display_name"], "Test User")
        self.assertEqual(result[0]["active"], True)
        self.assertNotIn("attributes", result[0])

    def test_with_denest_targeted(self):
        data = {
            "data": [
                {
                    "id": "1",
                    "relationships": {
                        "org": {"data": {"type": "org", "id": "org-1"}},
                    },
                }
            ]
        }
        config = {"denest": ["relationships.data"]}
        result = transform_json(data, config, "data")
        self.assertEqual(result[0]["org"], {"type": "org", "id": "org-1"})

    def test_no_denest_key_in_config(self):
        data = {"results": [{"camelKey": "val"}]}
        config = {"api_method": "GET"}
        result = transform_json(data, config, "results")
        self.assertEqual(result, [{"camel_key": "val"}])

    def test_full_customer_like_record(self):
        """End-to-end: camelCase conversion + attributes denest + relationships.data denest."""
        data = {
            "data": [
                {
                    "type": "customer",
                    "id": "abc123",
                    "attributes": {
                        "displayName": "Test User",
                        "createdAt": "2020-01-01T00:00:00Z",
                        "sla": {"version": 4, "matchedAt": "2020-01-01"},
                    },
                    "relationships": {
                        "org": {
                            "data": {"type": "org", "id": "org-1"},
                            "links": {"self": "/v1/orgs/org-1"},
                        },
                        "sla": {
                            "data": {"type": "sla", "id": "sla-1"},
                            "links": {"self": "/v1/slas/sla-1"},
                        },
                    },
                }
            ]
        }
        config = {"denest": ["attributes", "relationships.data"]}
        result = transform_json(data, config, "data")

        # camelCase converted
        self.assertEqual(result[0]["display_name"], "Test User")
        self.assertEqual(result[0]["created_at"], "2020-01-01T00:00:00Z")
        # attributes denested
        self.assertNotIn("attributes", result[0])
        # relationships denested with data target
        self.assertEqual(result[0]["org"], {"type": "org", "id": "org-1"})
        # sla collision: relationship sla renamed to sla_data
        self.assertEqual(result[0]["sla_data"], {"type": "sla", "id": "sla-1"})
        # original sla from attributes preserved
        self.assertIn("sla", result[0])


if __name__ == "__main__":
    unittest.main()
