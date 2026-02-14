"""ATLAS API Management & Gateway testleri."""

import time

import pytest

from app.models.api_mgmt import (
    APIStatus,
    HTTPMethod,
    RateLimitStrategy,
    VersioningStrategy,
    ValidationLevel,
    ResponseFormat,
    APIRecord,
    RouteRecord,
    AnalyticsRecord,
    APIGatewaySnapshot,
)
from app.core.api_mgmt import (
    APIRegistry,
    RequestRouter,
    APIRateLimiter,
    RequestValidator,
    ResponseTransformer,
    APIVersioner,
    DocumentationGenerator,
    APIAnalyticsCollector,
    APIGateway,
)


# ==================== Model Testleri ====================


class TestAPIModels:
    """Model testleri."""

    def test_api_status_enum(self):
        assert APIStatus.ACTIVE == "active"
        assert APIStatus.DISABLED == "disabled"
        assert APIStatus.DEPRECATED == "deprecated"

    def test_http_method_enum(self):
        assert HTTPMethod.GET == "GET"
        assert HTTPMethod.POST == "POST"
        assert HTTPMethod.PUT == "PUT"
        assert HTTPMethod.DELETE == "DELETE"

    def test_rate_limit_strategy_enum(self):
        assert RateLimitStrategy.SLIDING_WINDOW == "sliding_window"
        assert RateLimitStrategy.TOKEN_BUCKET == "token_bucket"

    def test_versioning_strategy_enum(self):
        assert VersioningStrategy.URL == "url"
        assert VersioningStrategy.HEADER == "header"
        assert VersioningStrategy.QUERY == "query"

    def test_validation_level_enum(self):
        assert ValidationLevel.STRICT == "strict"
        assert ValidationLevel.LENIENT == "lenient"

    def test_response_format_enum(self):
        assert ResponseFormat.JSON == "json"
        assert ResponseFormat.XML == "xml"

    def test_api_record_defaults(self):
        r = APIRecord(name="test", base_path="/api")
        assert r.name == "test"
        assert r.base_path == "/api"
        assert r.api_id
        assert r.status == APIStatus.ACTIVE

    def test_route_record_defaults(self):
        r = RouteRecord(
            path="/api/test",
            target="handler",
            method="GET",
        )
        assert r.path == "/api/test"
        assert r.target == "handler"
        assert r.route_id
        assert r.active is True

    def test_analytics_record_defaults(self):
        r = AnalyticsRecord(
            path="/test",
            method="GET",
        )
        assert r.path == "/test"
        assert r.request_id

    def test_gateway_snapshot_defaults(self):
        s = APIGatewaySnapshot()
        assert s.total_apis == 0
        assert s.total_routes == 0


# ==================== APIRegistry Testleri ====================


class TestAPIRegistry:
    """APIRegistry testleri."""

    def test_register(self):
        reg = APIRegistry()
        api = reg.register("test", "/api")
        assert api.name == "test"
        assert api.base_path == "/api"
        assert reg.api_count == 1

    def test_register_with_version(self):
        reg = APIRegistry()
        api = reg.register("v2", "/api", version="v2")
        assert api.version == "v2"

    def test_add_endpoint(self):
        reg = APIRegistry()
        api = reg.register("svc", "/api")
        result = reg.add_endpoint(api.api_id, "/users")
        assert result is not None
        eps = reg.get_endpoints(api.api_id)
        assert any(e["path"] == "/users" for e in eps)

    def test_add_endpoint_nonexistent(self):
        reg = APIRegistry()
        assert reg.add_endpoint("nope", "/a") is None

    def test_deprecate(self):
        reg = APIRegistry()
        api = reg.register("old", "/api")
        assert reg.deprecate(api.api_id) is True
        fetched = reg.get_api(api.api_id)
        assert fetched.status == APIStatus.DEPRECATED

    def test_deprecate_nonexistent(self):
        reg = APIRegistry()
        assert reg.deprecate("nope") is False

    def test_disable_enable(self):
        reg = APIRegistry()
        api = reg.register("svc", "/api")
        assert reg.disable(api.api_id) is True
        fetched = reg.get_api(api.api_id)
        assert fetched.status == APIStatus.DISABLED
        assert reg.enable(api.api_id) is True
        fetched = reg.get_api(api.api_id)
        assert fetched.status == APIStatus.ACTIVE

    def test_disable_nonexistent(self):
        reg = APIRegistry()
        assert reg.disable("nope") is False

    def test_enable_nonexistent(self):
        reg = APIRegistry()
        assert reg.enable("nope") is False

    def test_discover(self):
        reg = APIRegistry()
        reg.register("a", "/a")
        reg.register("b", "/b")
        all_apis = reg.discover()
        assert len(all_apis) == 2

    def test_discover_filter_active(self):
        reg = APIRegistry()
        reg.register("a", "/a")
        api_b = reg.register("b", "/b")
        reg.disable(api_b.api_id)
        active = reg.discover(status="active")
        assert len(active) == 1
        assert active[0].name == "a"

    def test_get_api(self):
        reg = APIRegistry()
        api = reg.register("x", "/x")
        fetched = reg.get_api(api.api_id)
        assert fetched is not None
        assert fetched.name == "x"

    def test_get_api_nonexistent(self):
        reg = APIRegistry()
        assert reg.get_api("nope") is None

    def test_remove(self):
        reg = APIRegistry()
        api = reg.register("del", "/x")
        assert reg.remove(api.api_id) is True
        assert reg.api_count == 0

    def test_remove_nonexistent(self):
        reg = APIRegistry()
        assert reg.remove("nope") is False

    def test_endpoint_count(self):
        reg = APIRegistry()
        api = reg.register("svc", "/x")
        reg.add_endpoint(api.api_id, "/a")
        reg.add_endpoint(api.api_id, "/b")
        assert reg.endpoint_count == 2


# ==================== RequestRouter Testleri ====================


class TestRequestRouter:
    """RequestRouter testleri."""

    def test_add_route(self):
        router = RequestRouter()
        route = router.add_route("/api/users", "handler_a")
        assert route.path == "/api/users"
        assert route.target == "handler_a"
        assert router.route_count == 1

    def test_resolve_basic(self):
        router = RequestRouter()
        router.add_route("/api/users", "handler_a")
        result = router.resolve("/api/users")
        assert result["resolved"] is True
        assert result["target"] == "handler_a"

    def test_resolve_not_found(self):
        router = RequestRouter()
        result = router.resolve("/nope")
        assert result["resolved"] is False

    def test_resolve_with_version(self):
        router = RequestRouter()
        router.add_route("/users", "v1_handler", version="v1")
        router.add_route("/users", "v2_handler", version="v2")
        r = router.resolve("/users", version="v2")
        assert r["resolved"] is True
        assert r["target"] == "v2_handler"

    def test_resolve_by_method(self):
        router = RequestRouter()
        router.add_route("/users", "get_h", method="GET")
        router.add_route("/users", "post_h", method="POST")
        r = router.resolve("/users", method="POST")
        assert r["target"] == "post_h"

    def test_resolve_with_weight(self):
        router = RequestRouter()
        router.add_route("/api", "low", weight=10)
        router.add_route("/api", "high", weight=200)
        r = router.resolve("/api")
        assert r["target"] == "high"

    def test_fallback(self):
        router = RequestRouter()
        router.set_fallback("/api", "fallback_target")
        r = router.resolve("/api")
        assert r["resolved"] is True
        assert r["fallback"] is True
        assert r["target"] == "fallback_target"

    def test_disable_route(self):
        router = RequestRouter()
        route = router.add_route("/x", "h")
        assert router.disable_route(route.route_id) is True
        r = router.resolve("/x")
        assert r["resolved"] is False

    def test_enable_route(self):
        router = RequestRouter()
        route = router.add_route("/x", "h")
        router.disable_route(route.route_id)
        router.enable_route(route.route_id)
        r = router.resolve("/x")
        assert r["resolved"] is True

    def test_remove_route(self):
        router = RequestRouter()
        route = router.add_route("/x", "h")
        assert router.remove_route(route.route_id) is True
        assert router.route_count == 0

    def test_remove_nonexistent(self):
        router = RequestRouter()
        assert router.remove_route("nope") is False

    def test_add_backend(self):
        router = RequestRouter()
        b = router.add_backend("svc", "http://a:8000")
        assert b["url"] == "http://a:8000"
        assert router.backend_count == 1

    def test_load_balance(self):
        router = RequestRouter()
        router.add_backend("svc", "http://a", weight=10)
        router.add_backend("svc", "http://b", weight=100)
        r = router.load_balance("svc")
        assert r["success"] is True
        assert r["url"] == "http://b"

    def test_load_balance_no_healthy(self):
        router = RequestRouter()
        router.add_backend("svc", "http://a", healthy=False)
        r = router.load_balance("svc")
        assert r["success"] is False

    def test_load_balance_nonexistent(self):
        router = RequestRouter()
        r = router.load_balance("nope")
        assert r["success"] is False

    def test_active_route_count(self):
        router = RequestRouter()
        r1 = router.add_route("/a", "h1")
        router.add_route("/b", "h2")
        router.disable_route(r1.route_id)
        assert router.active_route_count == 1

    def test_disable_nonexistent(self):
        router = RequestRouter()
        assert router.disable_route("nope") is False

    def test_enable_nonexistent(self):
        router = RequestRouter()
        assert router.enable_route("nope") is False


# ==================== APIRateLimiter Testleri ====================


class TestAPIRateLimiter:
    """APIRateLimiter testleri."""

    def test_check_allowed(self):
        rl = APIRateLimiter(default_limit=10)
        r = rl.check("key1")
        assert r["allowed"] is True
        assert r["limit"] == 10

    def test_check_exceeded(self):
        rl = APIRateLimiter(default_limit=2)
        rl.check("k")
        rl.check("k")
        r = rl.check("k")
        assert r["allowed"] is False

    def test_set_limit(self):
        rl = APIRateLimiter(default_limit=10)
        rl.set_limit("vip", 1000)
        r = rl.check("vip")
        assert r["limit"] == 1000

    def test_set_user_limit(self):
        rl = APIRateLimiter()
        rl.set_user_limit("u1", 50)
        r = rl.check_user("u1")
        assert r["limit"] == 50

    def test_set_endpoint_limit(self):
        rl = APIRateLimiter()
        rl.set_endpoint_limit("/api", 200)
        r = rl.check_endpoint("/api")
        assert r["limit"] == 200

    def test_check_with_cost(self):
        rl = APIRateLimiter(default_limit=5)
        r = rl.check("k", cost=3)
        assert r["allowed"] is True
        r = rl.check("k", cost=3)
        assert r["allowed"] is False

    def test_init_token_bucket(self):
        rl = APIRateLimiter()
        b = rl.init_token_bucket("tb1", capacity=10)
        assert b["capacity"] == 10
        assert b["tokens"] == 10
        assert rl.bucket_count == 1

    def test_consume_token(self):
        rl = APIRateLimiter()
        rl.init_token_bucket("tb", 5)
        r = rl.consume_token("tb", 3)
        assert r["allowed"] is True
        assert r["remaining"] == 2

    def test_consume_token_insufficient(self):
        rl = APIRateLimiter()
        rl.init_token_bucket("tb", 2)
        r = rl.consume_token("tb", 5)
        assert r["allowed"] is False

    def test_consume_nonexistent_bucket(self):
        rl = APIRateLimiter()
        r = rl.consume_token("nope")
        assert r["allowed"] is False

    def test_reset_window(self):
        rl = APIRateLimiter(default_limit=2)
        rl.check("k")
        rl.check("k")
        assert rl.reset("k") is True
        r = rl.check("k")
        assert r["allowed"] is True

    def test_reset_bucket(self):
        rl = APIRateLimiter()
        rl.init_token_bucket("tb", 5)
        rl.consume_token("tb", 5)
        rl.reset("tb")
        r = rl.consume_token("tb", 1)
        assert r["allowed"] is True

    def test_reset_nonexistent(self):
        rl = APIRateLimiter()
        assert rl.reset("nope") is False

    def test_get_status(self):
        rl = APIRateLimiter(default_limit=10)
        rl.check("k")
        rl.check("k")
        s = rl.get_status("k")
        assert s["key"] == "k"
        assert s["limit"] == 10
        assert s["current"] == 2
        assert s["remaining"] == 8

    def test_user_limit_count(self):
        rl = APIRateLimiter()
        rl.set_user_limit("a", 10)
        rl.set_user_limit("b", 20)
        assert rl.user_limit_count == 2

    def test_endpoint_limit_count(self):
        rl = APIRateLimiter()
        rl.set_endpoint_limit("/a", 10)
        assert rl.endpoint_limit_count == 1


# ==================== RequestValidator Testleri ====================


class TestRequestValidator:
    """RequestValidator testleri."""

    def test_validate_no_schema(self):
        v = RequestValidator()
        r = v.validate_schema("/api/test", {"a": 1})
        assert r["valid"] is True

    def test_validate_schema_pass(self):
        v = RequestValidator()
        v.register_schema("/users", {
            "required": ["name", "email"],
            "types": {"name": "string", "email": "string"},
        })
        r = v.validate_schema("/users", {
            "name": "Ali",
            "email": "ali@x.com",
        })
        assert r["valid"] is True

    def test_validate_schema_missing_field(self):
        v = RequestValidator()
        v.register_schema("/users", {
            "required": ["name"],
        })
        r = v.validate_schema("/users", {})
        assert r["valid"] is False
        assert any("missing_field:name" in e for e in r["errors"])

    def test_validate_schema_type_error(self):
        v = RequestValidator()
        v.register_schema("/users", {
            "types": {"age": "int"},
        })
        r = v.validate_schema("/users", {"age": "abc"})
        assert r["valid"] is False
        assert any("type_error:age" in e for e in r["errors"])

    def test_validate_type_float(self):
        v = RequestValidator()
        v.register_schema("/data", {
            "types": {"score": "float"},
        })
        r = v.validate_schema("/data", {"score": 3.14})
        assert r["valid"] is True
        r2 = v.validate_schema("/data", {"score": "x"})
        assert r2["valid"] is False

    def test_validate_params_pass(self):
        v = RequestValidator()
        r = v.validate_params(
            {"page": "2", "limit": "10"},
            {"page": {"required": True, "min": 1, "max": 100}},
        )
        assert r["valid"] is True

    def test_validate_params_missing(self):
        v = RequestValidator()
        r = v.validate_params(
            {},
            {"page": {"required": True}},
        )
        assert r["valid"] is False

    def test_validate_params_below_min(self):
        v = RequestValidator()
        r = v.validate_params(
            {"age": "5"},
            {"age": {"min": 18}},
        )
        assert r["valid"] is False

    def test_validate_params_above_max(self):
        v = RequestValidator()
        r = v.validate_params(
            {"qty": "200"},
            {"qty": {"max": 100}},
        )
        assert r["valid"] is False

    def test_validate_params_pattern(self):
        v = RequestValidator()
        r = v.validate_params(
            {"code": "AB123"},
            {"code": {"pattern": r"^[A-Z]{2}\d{3}$"}},
        )
        assert r["valid"] is True

    def test_validate_params_pattern_mismatch(self):
        v = RequestValidator()
        r = v.validate_params(
            {"code": "123"},
            {"code": {"pattern": r"^[A-Z]+$"}},
        )
        assert r["valid"] is False

    def test_validate_headers_pass(self):
        v = RequestValidator()
        v.set_required_headers("/api", ["Authorization"])
        r = v.validate_headers(
            {"Authorization": "Bearer x"},
            endpoint="/api",
        )
        assert r["valid"] is True

    def test_validate_headers_missing(self):
        v = RequestValidator()
        v.set_required_headers("/api", ["Authorization"])
        r = v.validate_headers({}, endpoint="/api")
        assert r["valid"] is False

    def test_validate_headers_case_insensitive(self):
        v = RequestValidator()
        v.set_required_headers("/api", ["Content-Type"])
        r = v.validate_headers(
            {"content-type": "application/json"},
            endpoint="/api",
        )
        assert r["valid"] is True

    def test_validate_body_json(self):
        v = RequestValidator()
        r = v.validate_body({"key": "value"})
        assert r["valid"] is True

    def test_validate_body_invalid(self):
        v = RequestValidator()
        r = v.validate_body("not json")
        assert r["valid"] is False

    def test_validate_body_list(self):
        v = RequestValidator()
        r = v.validate_body([1, 2, 3])
        assert r["valid"] is True

    def test_validate_body_none_non_json(self):
        v = RequestValidator()
        r = v.validate_body(None, content_type="text/plain")
        assert r["valid"] is False

    def test_register_custom_validator(self):
        v = RequestValidator()
        v.register_validator("is_positive", lambda x: x > 0)
        r = v.run_custom("is_positive", 5)
        assert r["valid"] is True

    def test_custom_validator_fail(self):
        v = RequestValidator()
        v.register_validator("is_positive", lambda x: x > 0)
        r = v.run_custom("is_positive", -1)
        assert r["valid"] is False

    def test_custom_validator_not_found(self):
        v = RequestValidator()
        r = v.run_custom("nope", 1)
        assert r["valid"] is False

    def test_custom_validator_exception(self):
        v = RequestValidator()
        v.register_validator("bad", lambda x: 1 / 0)
        r = v.run_custom("bad", 1)
        assert r["valid"] is False

    def test_schema_count(self):
        v = RequestValidator()
        v.register_schema("/a", {})
        v.register_schema("/b", {})
        assert v.schema_count == 2

    def test_validator_count(self):
        v = RequestValidator()
        v.register_validator("a", lambda x: True)
        assert v.validator_count == 1

    def test_validation_and_failure_counts(self):
        v = RequestValidator()
        v.register_schema("/x", {"required": ["a"]})
        v.validate_schema("/x", {"a": 1})
        v.validate_schema("/x", {})
        assert v.validation_count == 2
        assert v.failure_count == 1


# ==================== ResponseTransformer Testleri ====================


class TestResponseTransformer:
    """ResponseTransformer testleri."""

    def test_filter_fields(self):
        t = ResponseTransformer()
        data = {"a": 1, "b": 2, "c": 3}
        r = t.filter_fields(data, ["a", "c"])
        assert r == {"a": 1, "c": 3}

    def test_exclude_fields(self):
        t = ResponseTransformer()
        data = {"a": 1, "b": 2, "c": 3}
        r = t.exclude_fields(data, ["b"])
        assert r == {"a": 1, "c": 3}

    def test_mask_field(self):
        t = ResponseTransformer()
        r = t.mask_field("1234567890")
        assert r.endswith("7890")
        assert r.startswith("******")

    def test_mask_field_short(self):
        t = ResponseTransformer()
        r = t.mask_field("ab", visible_chars=4)
        assert r == "**"

    def test_mask_data(self):
        t = ResponseTransformer()
        data = {"name": "Ali", "ssn": "1234567890"}
        r = t.mask_data(data, ["ssn"])
        assert r["name"] == "Ali"
        assert "1234567890" not in r["ssn"]

    def test_mask_data_non_string(self):
        t = ResponseTransformer()
        data = {"count": 42}
        r = t.mask_data(data, ["count"])
        assert r["count"] == 42

    def test_paginate(self):
        t = ResponseTransformer()
        items = list(range(50))
        r = t.paginate(items, page=2, page_size=10)
        assert len(r["data"]) == 10
        assert r["data"][0] == 10
        assert r["pagination"]["total_items"] == 50
        assert r["pagination"]["total_pages"] == 5

    def test_paginate_with_links(self):
        t = ResponseTransformer()
        items = list(range(30))
        r = t.paginate(items, page=2, page_size=10, base_url="/api")
        assert "_links" in r
        assert "prev" in r["_links"]
        assert "next" in r["_links"]
        assert "first" in r["_links"]
        assert "last" in r["_links"]

    def test_paginate_first_page_no_prev(self):
        t = ResponseTransformer()
        items = list(range(30))
        r = t.paginate(items, page=1, page_size=10, base_url="/api")
        assert "prev" not in r["_links"]

    def test_paginate_last_page_no_next(self):
        t = ResponseTransformer()
        items = list(range(20))
        r = t.paginate(items, page=2, page_size=10, base_url="/api")
        assert "next" not in r["_links"]

    def test_add_links(self):
        t = ResponseTransformer()
        data = {"id": 1}
        r = t.add_links(data, {"self": "/api/1"})
        assert r["_links"]["self"] == "/api/1"

    def test_rename_fields(self):
        t = ResponseTransformer()
        data = {"old_name": "Ali", "age": 30}
        r = t.rename_fields(data, {"old_name": "name"})
        assert "name" in r
        assert "old_name" not in r
        assert r["age"] == 30

    def test_wrap_response(self):
        t = ResponseTransformer()
        r = t.wrap_response({"id": 1})
        assert r["status"] == "success"
        assert r["data"]["id"] == 1

    def test_wrap_response_with_message(self):
        t = ResponseTransformer()
        r = t.wrap_response({"id": 1}, message="ok")
        assert r["message"] == "ok"

    def test_to_format(self):
        t = ResponseTransformer()
        r = t.to_format({"a": 1}, fmt="xml")
        assert r["format"] == "xml"
        assert r["data"]["a"] == 1

    def test_transformation_count(self):
        t = ResponseTransformer()
        t.filter_fields({"a": 1}, ["a"])
        t.exclude_fields({"a": 1}, [])
        t.wrap_response({})
        assert t.transformation_count == 3

    def test_mask_rule_count(self):
        t = ResponseTransformer()
        assert t.mask_rule_count == 0


# ==================== APIVersioner Testleri ====================


class TestAPIVersioner:
    """APIVersioner testleri."""

    def test_register_version(self):
        v = APIVersioner()
        r = v.register_version("v1", "First version")
        assert r["version"] == "v1"
        assert v.version_count == 1

    def test_first_registered_is_active(self):
        v = APIVersioner()
        v.register_version("v1")
        assert v.active_version == "v1"

    def test_set_active(self):
        v = APIVersioner()
        v.register_version("v1")
        v.register_version("v2")
        assert v.set_active("v2") is True
        assert v.active_version == "v2"

    def test_set_active_nonexistent(self):
        v = APIVersioner()
        assert v.set_active("nope") is False

    def test_deprecate_version(self):
        v = APIVersioner()
        v.register_version("v1")
        assert v.deprecate_version("v1") is True
        assert v.is_deprecated("v1") is True
        assert v.deprecated_count == 1

    def test_deprecate_nonexistent(self):
        v = APIVersioner()
        assert v.deprecate_version("nope") is False

    def test_resolve_url(self):
        v = APIVersioner(strategy=VersioningStrategy.URL)
        r = v.resolve_version({"path": "/v2/users"})
        assert r == "v2"

    def test_resolve_header(self):
        v = APIVersioner(strategy=VersioningStrategy.HEADER)
        v.register_version("v1")
        r = v.resolve_version({
            "headers": {"API-Version": "v3"},
        })
        assert r == "v3"

    def test_resolve_query(self):
        v = APIVersioner(strategy=VersioningStrategy.QUERY)
        v.register_version("v1")
        r = v.resolve_version({
            "params": {"version": "v4"},
        })
        assert r == "v4"

    def test_resolve_default(self):
        v = APIVersioner(strategy=VersioningStrategy.HEADER)
        v.register_version("v1")
        r = v.resolve_version({"headers": {}})
        assert r == "v1"

    def test_is_compatible(self):
        v = APIVersioner()
        v.register_version("v1", endpoints=["/a", "/b"])
        v.register_version("v2", endpoints=["/a", "/b", "/c"])
        r = v.is_compatible("v1", "v2")
        assert r["compatible"] is True
        assert "/c" in r["added_endpoints"]

    def test_is_compatible_breaking(self):
        v = APIVersioner()
        v.register_version("v1", endpoints=["/a", "/b"])
        v.register_version("v2", endpoints=["/a"])
        r = v.is_compatible("v1", "v2")
        assert r["compatible"] is False
        assert "/b" in r["missing_endpoints"]

    def test_is_compatible_not_found(self):
        v = APIVersioner()
        r = v.is_compatible("v1", "v2")
        assert r["compatible"] is False

    def test_add_migration(self):
        v = APIVersioner()
        m = v.add_migration("v1", "v2", ["step1"])
        assert m["from"] == "v1"
        assert v.migration_count == 1

    def test_get_migration_path(self):
        v = APIVersioner()
        v.add_migration("v1", "v2", ["step1"])
        path = v.get_migration_path("v1", "v2")
        assert len(path) == 1
        assert path[0]["from"] == "v1"

    def test_get_migration_path_none(self):
        v = APIVersioner()
        path = v.get_migration_path("v1", "v2")
        assert len(path) == 0

    def test_get_version(self):
        v = APIVersioner()
        v.register_version("v1", "desc")
        info = v.get_version("v1")
        assert info is not None
        assert info["description"] == "desc"

    def test_get_version_none(self):
        v = APIVersioner()
        assert v.get_version("nope") is None

    def test_list_versions(self):
        v = APIVersioner()
        v.register_version("v1")
        v.register_version("v2")
        lst = v.list_versions()
        assert len(lst) == 2


# ==================== DocumentationGenerator Testleri ====================


class TestDocumentationGenerator:
    """DocumentationGenerator testleri."""

    def test_add_endpoint(self):
        doc = DocumentationGenerator()
        r = doc.add_endpoint("/users", "GET", summary="List users")
        assert r["path"] == "/users"
        assert doc.endpoint_count == 1

    def test_add_schema(self):
        doc = DocumentationGenerator()
        s = doc.add_schema("User", {"name": {"type": "string"}})
        assert s["name"] == "User"
        assert doc.schema_count == 1

    def test_add_example(self):
        doc = DocumentationGenerator()
        doc.add_endpoint("/users", "GET")
        e = doc.add_example(
            "GET:/users",
            response={"users": []},
        )
        assert e["response"]["users"] == []
        assert doc.example_count == 1

    def test_add_tag(self):
        doc = DocumentationGenerator()
        doc.add_tag("users", "User operations")
        assert doc.tag_count == 1

    def test_generate_openapi(self):
        doc = DocumentationGenerator(title="Test", version="2.0")
        doc.add_endpoint("/users", "GET", summary="List")
        doc.add_endpoint("/users", "POST", summary="Create")
        spec = doc.generate_openapi()
        assert spec["openapi"] == "3.0.0"
        assert spec["info"]["title"] == "Test"
        assert "/users" in spec["paths"]
        assert "get" in spec["paths"]["/users"]
        assert "post" in spec["paths"]["/users"]

    def test_generate_openapi_with_schemas(self):
        doc = DocumentationGenerator()
        doc.add_schema("User", {"name": {"type": "string"}})
        spec = doc.generate_openapi()
        assert "components" in spec
        assert "User" in spec["components"]["schemas"]

    def test_generate_openapi_with_tags(self):
        doc = DocumentationGenerator()
        doc.add_tag("users", "User ops")
        spec = doc.generate_openapi()
        assert len(spec["tags"]) == 1

    def test_generate_markdown(self):
        doc = DocumentationGenerator(title="My API")
        doc.add_endpoint("/users", "GET", summary="List users")
        md = doc.generate_markdown()
        assert "# My API" in md
        assert "GET /users" in md
        assert "List users" in md

    def test_generate_markdown_with_tags(self):
        doc = DocumentationGenerator()
        doc.add_tag("auth", "Auth operations")
        md = doc.generate_markdown()
        assert "auth" in md

    def test_generate_markdown_with_params(self):
        doc = DocumentationGenerator()
        doc.add_endpoint(
            "/users", "GET",
            parameters=[{"name": "page", "type": "integer"}],
        )
        md = doc.generate_markdown()
        assert "page" in md

    def test_get_playground_config(self):
        doc = DocumentationGenerator()
        doc.add_endpoint("/users", "GET")
        doc.add_example("GET:/users", response={"data": []})
        cfg = doc.get_playground_config("GET:/users")
        assert cfg["found"] is True
        assert cfg["try_it"] is True
        assert len(cfg["examples"]) == 1

    def test_get_playground_not_found(self):
        doc = DocumentationGenerator()
        cfg = doc.get_playground_config("nope")
        assert cfg["found"] is False

    def test_search_endpoints(self):
        doc = DocumentationGenerator()
        doc.add_endpoint("/users", "GET", summary="List users")
        doc.add_endpoint("/orders", "GET", summary="List orders")
        results = doc.search_endpoints("users")
        assert len(results) == 1
        assert results[0]["path"] == "/users"

    def test_search_by_description(self):
        doc = DocumentationGenerator()
        doc.add_endpoint("/x", "GET", description="manage inventory")
        results = doc.search_endpoints("inventory")
        assert len(results) == 1

    def test_get_endpoint(self):
        doc = DocumentationGenerator()
        doc.add_endpoint("/users", "GET")
        ep = doc.get_endpoint("GET:/users")
        assert ep is not None
        assert ep["path"] == "/users"

    def test_get_endpoint_none(self):
        doc = DocumentationGenerator()
        assert doc.get_endpoint("nope") is None


# ==================== APIAnalyticsCollector Testleri ====================


class TestAPIAnalyticsCollector:
    """APIAnalyticsCollector testleri."""

    def test_record_request(self):
        a = APIAnalyticsCollector()
        r = a.record_request("/users", "GET", 200, 15.5)
        assert r["endpoint"] == "/users"
        assert a.request_count == 1

    def test_record_with_client(self):
        a = APIAnalyticsCollector()
        a.record_request("/users", "GET", 200, 10.0, client_id="c1")
        assert a.client_count == 1

    def test_record_error(self):
        a = APIAnalyticsCollector()
        a.record_request("/fail", "POST", 500, 100.0)
        assert a.error_count == 1

    def test_get_endpoint_stats(self):
        a = APIAnalyticsCollector()
        a.record_request("/users", "GET", 200, 10.0)
        a.record_request("/users", "GET", 200, 20.0)
        a.record_request("/users", "GET", 500, 5.0)
        s = a.get_endpoint_stats("/users")
        assert s["total"] == 3
        assert s["errors"] == 1
        assert s["avg_time"] > 0

    def test_get_endpoint_stats_empty(self):
        a = APIAnalyticsCollector()
        s = a.get_endpoint_stats("/nope")
        assert s["total"] == 0

    def test_get_top_endpoints(self):
        a = APIAnalyticsCollector()
        for _ in range(10):
            a.record_request("/hot", "GET", 200, 5.0)
        for _ in range(3):
            a.record_request("/cold", "GET", 200, 5.0)
        top = a.get_top_endpoints(2)
        assert len(top) == 2
        assert top[0]["endpoint"] == "/hot"
        assert top[0]["total"] == 10

    def test_get_error_summary(self):
        a = APIAnalyticsCollector()
        a.record_request("/a", "GET", 200, 5.0)
        a.record_request("/a", "GET", 404, 5.0)
        a.record_request("/a", "GET", 500, 5.0)
        summary = a.get_error_summary()
        assert summary["total_errors"] == 2
        assert 404 in summary["by_status_code"]
        assert 500 in summary["by_status_code"]

    def test_get_client_stats(self):
        a = APIAnalyticsCollector()
        a.record_request("/x", "GET", 200, 5.0, client_id="c1")
        a.record_request("/y", "GET", 200, 5.0, client_id="c1")
        s = a.get_client_stats("c1")
        assert s is not None
        assert s["request_count"] == 2

    def test_get_client_stats_none(self):
        a = APIAnalyticsCollector()
        assert a.get_client_stats("nope") is None

    def test_get_response_time_stats(self):
        a = APIAnalyticsCollector()
        a.record_request("/a", "GET", 200, 10.0)
        a.record_request("/a", "GET", 200, 20.0)
        a.record_request("/a", "GET", 200, 30.0)
        s = a.get_response_time_stats()
        assert s["avg"] == 20.0
        assert s["min"] == 10.0
        assert s["max"] == 30.0
        assert s["count"] == 3

    def test_get_response_time_empty(self):
        a = APIAnalyticsCollector()
        s = a.get_response_time_stats()
        assert s["count"] == 0

    def test_get_usage_patterns(self):
        a = APIAnalyticsCollector()
        a.record_request("/a", "GET", 200, 5.0, client_id="c1")
        a.record_request("/b", "POST", 201, 5.0, client_id="c2")
        p = a.get_usage_patterns()
        assert p["total_requests"] == 2
        assert p["unique_clients"] == 2
        assert "GET" in p["method_distribution"]
        assert "POST" in p["method_distribution"]
        assert "2xx" in p["status_distribution"]

    def test_cleanup(self):
        a = APIAnalyticsCollector()
        a.record_request("/a", "GET", 200, 5.0)
        # Yapay olarak eski timestamp
        a._requests[0]["timestamp"] = time.time() - 100000
        removed = a.cleanup(max_age_hours=1)
        assert removed == 1
        assert a.request_count == 0

    def test_endpoint_stat_count(self):
        a = APIAnalyticsCollector()
        a.record_request("/a", "GET", 200, 5.0)
        a.record_request("/b", "POST", 200, 5.0)
        assert a.endpoint_stat_count == 2


# ==================== APIGateway Testleri ====================


class TestAPIGateway:
    """APIGateway testleri."""

    def test_init(self):
        gw = APIGateway("Test GW")
        assert gw.name == "Test GW"
        assert gw.registry is not None
        assert gw.router is not None

    def test_register_api(self):
        gw = APIGateway()
        r = gw.register_api(
            "users-svc",
            "http://users:8000",
            endpoints=["/users", "/users/me"],
        )
        assert r["endpoints_added"] == 2
        assert gw.registry.api_count == 1
        assert gw.router.route_count == 2

    def test_handle_request_success(self):
        gw = APIGateway()
        gw.register_api(
            "svc", "http://svc:8000",
            endpoints=["/api/data"],
        )
        r = gw.handle_request("/api/data", "GET", client_id="c1")
        assert r["status_code"] == 200
        assert r["body"]["status"] == "success"

    def test_handle_request_not_found(self):
        gw = APIGateway()
        r = gw.handle_request("/nope")
        assert r["status_code"] == 404

    def test_handle_request_rate_limited(self):
        gw = APIGateway()
        gw.rate_limiter = APIRateLimiter(
            default_limit=1,
        )
        gw.register_api("svc", "http://x", endpoints=["/a"])
        gw.handle_request("/a", client_id="c1")
        r = gw.handle_request("/a", client_id="c1")
        assert r["status_code"] == 429

    def test_add_middleware(self):
        gw = APIGateway()
        mw = gw.add_middleware("auth", priority=10)
        assert mw["name"] == "auth"
        assert gw.middleware_count == 1

    def test_middleware_ordering(self):
        gw = APIGateway()
        gw.add_middleware("logging", priority=100)
        gw.add_middleware("auth", priority=10)
        gw.add_middleware("cors", priority=50)
        assert gw._middleware[0]["name"] == "auth"
        assert gw._middleware[1]["name"] == "cors"
        assert gw._middleware[2]["name"] == "logging"

    def test_configure_cors(self):
        gw = APIGateway()
        cors = gw.configure_cors(origins=["http://localhost"])
        assert "http://localhost" in cors["origins"]
        assert gw.cors_enabled is True

    def test_cors_not_enabled_by_default(self):
        gw = APIGateway()
        assert gw.cors_enabled is False

    def test_get_health(self):
        gw = APIGateway()
        h = gw.get_health()
        assert h["status"] == "healthy"
        assert h["uptime"] >= 0

    def test_get_analytics(self):
        gw = APIGateway()
        gw.register_api("svc", "http://x", endpoints=["/a"])
        gw.handle_request("/a", client_id="c1")
        a = gw.get_analytics()
        assert a["requests"] == 1

    def test_snapshot(self):
        gw = APIGateway()
        gw.register_api("svc", "http://x", endpoints=["/a"])
        s = gw.snapshot()
        assert s["apis"] == 1
        assert s["routes"] == 1

    def test_handle_tracks_analytics(self):
        gw = APIGateway()
        gw.register_api("svc", "http://x", endpoints=["/a"])
        gw.handle_request("/a", client_id="c1")
        gw.handle_request("/a", client_id="c2")
        gw.handle_request("/nope")
        assert gw.analytics.request_count == 3
        assert gw.analytics.error_count == 1  # 404

    def test_handle_request_headers(self):
        gw = APIGateway()
        gw.register_api("svc", "http://x", endpoints=["/a"])
        r = gw.handle_request("/a")
        assert "X-Gateway" in r["headers"]

    def test_register_api_versions(self):
        gw = APIGateway()
        gw.register_api("svc", "http://x", version="v2", endpoints=["/b"])
        assert gw.versioner.version_count == 1

    def test_register_api_docs(self):
        gw = APIGateway()
        gw.register_api("svc", "http://x", endpoints=["/c", "/d"])
        assert gw.docs.endpoint_count == 2


# ==================== Config Testleri ====================


class TestAPIConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.api_gateway_enabled is True
        assert s.default_rate_limit == 100
        assert s.request_timeout == 30
        assert s.enable_documentation is True
        assert s.analytics_retention_days == 30
