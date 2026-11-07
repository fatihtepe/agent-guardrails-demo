import unittest

from app.inventory import Service, total_replicas, validate


class TestInventory(unittest.TestCase):
    def test_valid_service(self):
        self.assertEqual(validate(Service("api", 2, "prod")), [])

    def test_prod_needs_two_replicas(self):
        self.assertIn("prod services need at least 2 replicas", validate(Service("api", 1, "prod")))

    def test_bad_env(self):
        self.assertTrue(validate(Service("api", 1, "qa")))

    def test_staging_max_three_replicas(self):
        self.assertEqual(validate(Service("api", 3, "staging")), [])
        self.assertIn("staging services may not exceed 3 replicas", validate(Service("api", 4, "staging")))

    def test_total_replicas(self):
        services = [Service("a", 2, "prod"), Service("b", 3, "prod"), Service("c", 5, "dev")]
        self.assertEqual(total_replicas(services, "prod"), 5)


if __name__ == "__main__":
    unittest.main()
