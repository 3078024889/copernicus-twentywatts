import unittest
from tw10.resource_meter import ResourceMeter, count_operation, measured_evaluation

class ResourceMeterIntegrationTests(unittest.TestCase):
    def test_explicit_operation_count_and_measurement_fields(self):
        with ResourceMeter(rss_interval_ms=1, operation_count_source="test_api_calls") as meter:
            count_operation(3)
            _ = [i * i for i in range(1000)]
            count_operation(2)
        report = meter.report()
        self.assertEqual(report["operation_count"], 5)
        self.assertEqual(report["operation_count_source"], "test_api_calls")
        self.assertIn("wall_seconds", report)
        self.assertIn("process_cpu_seconds", report)
        self.assertIn("peak_traced_bytes", report)
        self.assertIn("rss_sample_count", report)
        self.assertIn("operation_count_semantics", report)
        self.assertTrue(report["complete"])

    def test_decorator_attaches_measurement(self):
        @measured_evaluation
        def sample():
            count_operation(7)
            return {"mother_promotion": "LOCKED"}
        result = sample()
        self.assertEqual(result["resource_measurement"]["operation_count"], 7)
        self.assertIn("not FLOPs", result["operation_count_semantics"])
        self.assertEqual(result["mother_promotion"], "LOCKED")

    def test_counter_is_inactive_outside_meter(self):
        with ResourceMeter() as meter:
            count_operation(2)
        count_operation(100)
        self.assertEqual(meter.report()["operation_count"], 2)

if __name__ == "__main__":
    unittest.main()