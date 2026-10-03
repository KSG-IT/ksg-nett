import json
import re

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from common.middleware import RequestLogMiddleware
from users.tests.factories import UserFactory

LOGGER = "ksg_nett.requests"


def graphql_body(operation_name="Dashboard", **extra):
    return json.dumps(
        {
            "operationName": operation_name,
            "query": f"query {operation_name} {{ __typename }}",
            "variables": {"secret": "do-not-log"},
            **extra,
        }
    )


class RequestLogMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def run_middleware(self, request, status=200, body=b"x" * 30, user=None):
        def view(request):
            if user is not None:
                request.user = user
            return HttpResponse(body, status=status)

        return RequestLogMiddleware(view)(request)

    def test__graphql_request__logs_operation_status_size_and_time(self):
        request = self.factory.post(
            "/graphql/", graphql_body("MyUpcomingShifts"), "application/json"
        )

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self.run_middleware(request)

        [line] = logs.output
        self.assertIn("DEBUG", line)
        self.assertIn("POST /graphql/", line)
        self.assertIn("op=MyUpcomingShifts", line)
        self.assertIn("status=200", line)
        self.assertIn("resp=30B", line)
        self.assertRegex(line, r"ms=\d+")
        self.assertIn("user=anon", line)

    def test__never_logs_tokens_or_variables(self):
        request = self.factory.post(
            "/graphql/",
            graphql_body(),
            "application/json",
            HTTP_AUTHORIZATION="Bearer secret-token-value",
        )

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self.run_middleware(request)

        output = "\n".join(logs.output)
        self.assertNotIn("secret-token-value", output)
        self.assertNotIn("do-not-log", output)

    def test__logs_the_user_id_when_logged_in(self):
        user = UserFactory.create()
        request = self.factory.post("/graphql/", graphql_body(), "application/json")

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self.run_middleware(request, user=user)

        self.assertIn(f"user={user.id}", logs.output[0])

    def test__operation_from_query_string(self):
        request = self.factory.post(
            "/graphql/?op=AllShifts",
            json.dumps({"query": "{ __typename }"}),
            "application/json",
        )

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self.run_middleware(request)

        self.assertIn("op=AllShifts", logs.output[0])

    def test__request_id_from_varnish_is_logged_and_returned(self):
        request = self.factory.post(
            "/graphql/",
            graphql_body(),
            "application/json",
            HTTP_X_VARNISH="448054052",
        )

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            response = self.run_middleware(request)

        self.assertEqual(response["X-Request-ID"], "448054052")
        self.assertIn("rid=448054052", logs.output[0])

    def test__request_id_is_generated_without_varnish(self):
        request = self.factory.get("/health-check")

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            response = self.run_middleware(request)

        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{12}$")
        self.assertIn(f"rid={response['X-Request-ID']}", logs.output[0])

    def test__server_error_is_logged_as_warning(self):
        request = self.factory.post("/graphql/", graphql_body(), "application/json")

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self.run_middleware(request, status=503)

        self.assertTrue(logs.output[0].startswith("WARNING"))
        self.assertIn("status=503", logs.output[0])

    @override_settings(REQUEST_LOG_SLOW_MS=0)
    def test__slow_request_is_logged_as_warning(self):
        request = self.factory.post("/graphql/", graphql_body(), "application/json")

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self.run_middleware(request)

        self.assertTrue(logs.output[0].startswith("WARNING"))

    def test__file_upload_body_is_not_read(self):
        request = self.factory.post(
            "/graphql/",
            {"operations": graphql_body("PatchUser"), "map": "{}"},
        )

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            self.run_middleware(request)

        # The view can still read the multipart form after the middleware.
        self.assertIn("operations", request.POST)
        self.assertIn("op=-", logs.output[0])

    def test__invalid_json_does_not_break_the_request(self):
        request = self.factory.post("/graphql/", "{not json", "application/json")

        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            response = self.run_middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("op=-", logs.output[0])


class RequestLogMiddlewareInstalledTest(TestCase):
    def test__graphql_endpoint_returns_a_request_id(self):
        with self.assertLogs(LOGGER, level="DEBUG") as logs:
            response = self.client.post(
                "/graphql/",
                graphql_body("Probe"),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(re.match(r"^[0-9a-f]{12}$", response["X-Request-ID"]))
        self.assertTrue(any("op=Probe" in line for line in logs.output))
