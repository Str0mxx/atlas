"""ATLAS Container & Orchestration Management testleri.

ContainerBuilder, ImageRegistry, ContainerRuntime,
PodManager, DeploymentController, ServiceExposer,
ResourceQuota, HelmManager, ContainerOrchestrator,
modeller ve config testleri.
"""

import time

import pytest

from app.core.container.container_builder import (
    ContainerBuilder,
)
from app.core.container.image_registry import (
    ImageRegistry,
)
from app.core.container.container_runtime import (
    ContainerRuntime,
)
from app.core.container.pod_manager import (
    PodManager,
)
from app.core.container.deployment_controller import (
    DeploymentController,
)
from app.core.container.service_exposer import (
    ServiceExposer,
)
from app.core.container.resource_quota import (
    ResourceQuota,
)
from app.core.container.helm_manager import (
    HelmManager,
)
from app.core.container.container_orchestrator import (
    ContainerOrchestrator,
)
from app.models.container_models import (
    ContainerStatus,
    DeploymentStrategy,
    ServiceType,
    ProbeType,
    ResourceType,
    ChartStatus,
    ContainerRecord,
    DeploymentRecord,
    HelmRelease,
    ContainerSnapshot,
)


# ===================== ContainerBuilder =====================

class TestContainerBuilder:
    """ContainerBuilder testleri."""

    def setup_method(self) -> None:
        self.cb = ContainerBuilder()

    def test_init(self) -> None:
        assert self.cb.build_count == 0
        assert self.cb.base_image_count == 0
        assert self.cb.template_count == 0

    def test_register_base_image(self) -> None:
        result = self.cb.register_base_image(
            "python", "3.11-slim", size_mb=120,
        )
        assert result["image"] == "python:3.11-slim"
        assert self.cb.base_image_count == 1

    def test_set_build_arg(self) -> None:
        self.cb.set_build_arg("ENV", "production")
        df = self.cb.generate_dockerfile()
        assert "ARG ENV=production" in df

    def test_generate_dockerfile_basic(self) -> None:
        df = self.cb.generate_dockerfile(
            base_image="python:3.11-slim",
            workdir="/app",
            cmd='["python", "main.py"]',
            expose_port=8000,
        )
        assert "FROM python:3.11-slim" in df
        assert "WORKDIR /app" in df
        assert "EXPOSE 8000" in df
        assert "CMD" in df

    def test_generate_dockerfile_with_packages(self) -> None:
        df = self.cb.generate_dockerfile(
            packages=["flask", "requests"],
        )
        assert "requirements.txt" in df
        assert "pip install" in df

    def test_generate_dockerfile_multi_stage(self) -> None:
        df = self.cb.generate_dockerfile(
            multi_stage=True,
            packages=["flask"],
        )
        assert "AS builder" in df
        assert "AS runtime" in df
        assert "COPY --from=builder" in df

    def test_generate_dockerfile_copy_files(self) -> None:
        df = self.cb.generate_dockerfile(
            copy_files=["src/", "config/"],
        )
        assert "COPY src/" in df
        assert "COPY config/" in df

    def test_build(self) -> None:
        df = self.cb.generate_dockerfile()
        result = self.cb.build(
            "myapp", "v1", df,
        )
        assert result["status"] == "success"
        assert result["layers"] > 0
        assert self.cb.build_count == 1

    def test_build_no_dockerfile(self) -> None:
        result = self.cb.build("myapp", "v1")
        assert result["status"] == "success"

    def test_optimize_layers(self) -> None:
        df = (
            "FROM python:3.11\n"
            "RUN apt-get update\n"
            "RUN apt-get install -y curl\n"
            "RUN pip install flask\n"
            "COPY . /app\n"
        )
        result = self.cb.optimize_layers(df)
        assert result["run_commands_merged"] == 3
        assert result["saved_layers"] > 0

    def test_save_template(self) -> None:
        result = self.cb.save_template(
            "python-web",
            "python:3.11-slim",
            packages=["flask"],
            cmd='["python", "app.py"]',
        )
        assert result["name"] == "python-web"
        assert self.cb.template_count == 1

    def test_get_template(self) -> None:
        self.cb.save_template(
            "node-api", "node:20-slim",
        )
        t = self.cb.get_template("node-api")
        assert t is not None
        assert t["base_image"] == "node:20-slim"

    def test_get_template_not_found(self) -> None:
        assert self.cb.get_template("ghost") is None

    def test_select_base_image(self) -> None:
        assert "python" in self.cb.select_base_image("python")
        assert "node" in self.cb.select_base_image("node")
        assert "golang" in self.cb.select_base_image("go")
        assert "rust" in self.cb.select_base_image("rust")
        assert "temurin" in self.cb.select_base_image("java")

    def test_select_base_image_minimal(self) -> None:
        img = self.cb.select_base_image("python", minimal=True)
        assert "slim" in img

    def test_select_base_image_unknown(self) -> None:
        img = self.cb.select_base_image("ruby")
        assert "ruby:latest" == img

    def test_get_builds(self) -> None:
        self.cb.build("app1", "v1")
        self.cb.build("app2", "v1")
        builds = self.cb.get_builds()
        assert len(builds) == 2

    def test_get_stats(self) -> None:
        stats = self.cb.get_stats()
        assert "builds" in stats
        assert "failures" in stats


# ===================== ImageRegistry =====================

class TestImageRegistry:
    """ImageRegistry testleri."""

    def setup_method(self) -> None:
        self.ir = ImageRegistry()

    def test_init(self) -> None:
        assert self.ir.image_count == 0
        assert self.ir.push_count == 0
        assert self.ir.pull_count == 0

    def test_push(self) -> None:
        result = self.ir.push(
            "myapp", "v1", size_mb=100,
        )
        assert result["status"] == "pushed"
        assert result["digest"].startswith("sha256:")
        assert self.ir.image_count == 1
        assert self.ir.push_count == 1

    def test_pull(self) -> None:
        self.ir.push("myapp", "v1")
        result = self.ir.pull("myapp", "v1")
        assert result is not None
        assert result["status"] == "pulled"
        assert self.ir.pull_count == 1

    def test_pull_not_found(self) -> None:
        assert self.ir.pull("ghost") is None

    def test_tag(self) -> None:
        self.ir.push("myapp", "v1")
        result = self.ir.tag(
            "myapp", "v1", "latest",
        )
        assert result is not None
        assert result["target"] == "latest"
        assert self.ir.image_count == 2

    def test_tag_not_found(self) -> None:
        assert self.ir.tag("ghost", "v1", "v2") is None

    def test_get_tags(self) -> None:
        self.ir.push("myapp", "v1")
        self.ir.push("myapp", "v2")
        tags = self.ir.get_tags("myapp")
        assert "v1" in tags
        assert "v2" in tags

    def test_get_tags_empty(self) -> None:
        assert self.ir.get_tags("ghost") == []

    def test_get_image(self) -> None:
        self.ir.push("myapp", "v1")
        img = self.ir.get_image("myapp", "v1")
        assert img is not None
        assert img["name"] == "myapp"

    def test_delete(self) -> None:
        self.ir.push("myapp", "v1")
        assert self.ir.delete("myapp", "v1") is True
        assert self.ir.image_count == 0

    def test_delete_not_found(self) -> None:
        assert self.ir.delete("ghost") is False

    def test_scan_clean(self) -> None:
        self.ir.push("myapp", "v1")
        result = self.ir.scan("myapp", "v1")
        assert result["clean"] is True
        assert self.ir.scan_count == 1

    def test_scan_with_vulnerabilities(self) -> None:
        self.ir.push("myapp", "v1")
        self.ir.add_vulnerability(
            "myapp", "v1", "CVE-2024-001",
            severity="high",
        )
        result = self.ir.scan("myapp", "v1")
        assert result["clean"] is False
        assert result["total_vulnerabilities"] == 1
        assert result["severity"]["high"] == 1

    def test_scan_not_found(self) -> None:
        result = self.ir.scan("ghost")
        assert result["status"] == "not_found"

    def test_cleanup_policy(self) -> None:
        result = self.ir.set_cleanup_policy(
            "myapp", max_tags=3,
        )
        assert result["max_tags"] == 3

    def test_run_cleanup(self) -> None:
        for i in range(5):
            self.ir.push("myapp", f"v{i}")
        self.ir.set_cleanup_policy(
            "myapp", max_tags=2,
        )
        result = self.ir.run_cleanup("myapp")
        assert result["cleaned"] == 3
        assert result["remaining"] == 2

    def test_run_cleanup_no_policy(self) -> None:
        result = self.ir.run_cleanup("ghost")
        assert result["cleaned"] == 0

    def test_list_images(self) -> None:
        self.ir.push("app1", "v1")
        self.ir.push("app2", "v1")
        images = self.ir.list_images()
        assert len(images) == 2


# ===================== ContainerRuntime =====================

class TestContainerRuntime:
    """ContainerRuntime testleri."""

    def setup_method(self) -> None:
        self.cr = ContainerRuntime()

    def test_init(self) -> None:
        assert self.cr.container_count == 0
        assert self.cr.running_count == 0

    def test_create(self) -> None:
        result = self.cr.create(
            "c1", "python:3.11",
            name="web",
        )
        assert result["status"] == "created"
        assert self.cr.container_count == 1

    def test_start(self) -> None:
        self.cr.create("c1", "python:3.11")
        result = self.cr.start("c1")
        assert result["status"] == "running"
        assert self.cr.running_count == 1

    def test_start_not_found(self) -> None:
        result = self.cr.start("ghost")
        assert "error" in result

    def test_start_already_running(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.start("c1")
        result = self.cr.start("c1")
        assert result["error"] == "already_running"

    def test_stop(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.start("c1")
        result = self.cr.stop("c1")
        assert result["status"] == "stopped"
        assert self.cr.running_count == 0

    def test_stop_not_running(self) -> None:
        self.cr.create("c1", "python:3.11")
        result = self.cr.stop("c1")
        assert result["error"] == "not_running"

    def test_restart(self) -> None:
        self.cr.create("c1", "python:3.11")
        result = self.cr.restart("c1")
        assert result["restarted"] is True

    def test_remove(self) -> None:
        self.cr.create("c1", "python:3.11")
        assert self.cr.remove("c1") is True
        assert self.cr.container_count == 0

    def test_remove_running_no_force(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.start("c1")
        assert self.cr.remove("c1") is False

    def test_remove_running_force(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.start("c1")
        assert self.cr.remove("c1", force=True) is True

    def test_set_resource_limits(self) -> None:
        self.cr.create("c1", "python:3.11")
        result = self.cr.set_resource_limits(
            "c1", cpu_limit="2.0",
            memory_limit="1Gi",
        )
        assert result["cpu_limit"] == "2.0"
        assert result["memory_limit"] == "1Gi"

    def test_create_network(self) -> None:
        result = self.cr.create_network(
            "mynet", driver="bridge",
        )
        assert result["name"] == "mynet"
        assert self.cr.network_count == 1

    def test_connect_network(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.create_network("mynet")
        result = self.cr.connect_network(
            "c1", "mynet",
        )
        assert result["network"] == "mynet"

    def test_create_volume(self) -> None:
        result = self.cr.create_volume(
            "data", size="10Gi",
        )
        assert result["name"] == "data"
        assert self.cr.volume_count == 1

    def test_mount_volume(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.create_volume("data")
        result = self.cr.mount_volume(
            "c1", "data", "/data",
        )
        assert result["path"] == "/data"

    def test_get_container(self) -> None:
        self.cr.create("c1", "python:3.11")
        c = self.cr.get_container("c1")
        assert c is not None
        assert c["image"] == "python:3.11"

    def test_list_containers(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.create("c2", "node:20")
        assert len(self.cr.list_containers()) == 2

    def test_list_containers_by_status(self) -> None:
        self.cr.create("c1", "python:3.11")
        self.cr.create("c2", "node:20")
        self.cr.start("c1")
        running = self.cr.list_containers(
            status="running",
        )
        assert len(running) == 1


# ===================== PodManager =====================

class TestPodManager:
    """PodManager testleri."""

    def setup_method(self) -> None:
        self.pm = PodManager()

    def test_init(self) -> None:
        assert self.pm.pod_count == 0
        assert self.pm.running_pod_count == 0

    def test_create_pod(self) -> None:
        result = self.pm.create_pod(
            "p1", "web-pod",
            labels={"app": "web"},
        )
        assert result["status"] == "pending"
        assert self.pm.pod_count == 1

    def test_add_container(self) -> None:
        self.pm.create_pod("p1", "web")
        result = self.pm.add_container(
            "p1", "app", "python:3.11",
            ports=[8000],
        )
        assert result["status"] == "added"

    def test_add_container_pod_not_found(self) -> None:
        result = self.pm.add_container(
            "ghost", "app", "python:3.11",
        )
        assert "error" in result

    def test_add_init_container(self) -> None:
        self.pm.create_pod("p1", "web")
        result = self.pm.add_init_container(
            "p1", "db-init", "postgres:15",
            command=["pg_isready"],
        )
        assert result["init_container"] == "db-init"

    def test_add_sidecar(self) -> None:
        self.pm.create_pod("p1", "web")
        result = self.pm.add_sidecar(
            "p1", "envoy", "envoyproxy/envoy",
            pattern="proxy",
        )
        assert result["pattern"] == "proxy"

    def test_set_probe(self) -> None:
        self.pm.create_pod("p1", "web")
        self.pm.add_container(
            "p1", "app", "python:3.11",
        )
        result = self.pm.set_probe(
            "p1", "app", "liveness",
            path="/healthz", port=8000,
        )
        assert result["probe"] == "liveness"
        assert self.pm.probe_count == 1

    def test_get_probe(self) -> None:
        self.pm.create_pod("p1", "web")
        self.pm.set_probe(
            "p1", "app", "readiness",
        )
        probe = self.pm.get_probe(
            "p1", "app", "readiness",
        )
        assert probe is not None
        assert probe["type"] == "readiness"

    def test_start_pod(self) -> None:
        self.pm.create_pod("p1", "web")
        self.pm.add_container(
            "p1", "app", "python:3.11",
        )
        self.pm.add_init_container(
            "p1", "init", "busybox",
        )
        result = self.pm.start_pod("p1")
        assert result["status"] == "running"
        assert self.pm.running_pod_count == 1

    def test_stop_pod(self) -> None:
        self.pm.create_pod("p1", "web")
        self.pm.add_container(
            "p1", "app", "python:3.11",
        )
        self.pm.start_pod("p1")
        result = self.pm.stop_pod("p1")
        assert result["status"] == "stopped"

    def test_restart_pod(self) -> None:
        self.pm.create_pod("p1", "web")
        self.pm.add_container(
            "p1", "app", "python:3.11",
        )
        result = self.pm.restart_pod("p1")
        assert result["restart_count"] == 1

    def test_delete_pod(self) -> None:
        self.pm.create_pod("p1", "web")
        self.pm.set_probe("p1", "app", "liveness")
        assert self.pm.delete_pod("p1") is True
        assert self.pm.pod_count == 0
        assert self.pm.probe_count == 0

    def test_delete_pod_not_found(self) -> None:
        assert self.pm.delete_pod("ghost") is False

    def test_get_pod(self) -> None:
        self.pm.create_pod("p1", "web")
        pod = self.pm.get_pod("p1")
        assert pod is not None
        assert pod["name"] == "web"

    def test_list_pods(self) -> None:
        self.pm.create_pod(
            "p1", "web", namespace="prod",
        )
        self.pm.create_pod(
            "p2", "api", namespace="dev",
        )
        all_pods = self.pm.list_pods()
        assert len(all_pods) == 2
        prod = self.pm.list_pods(namespace="prod")
        assert len(prod) == 1

    def test_total_containers(self) -> None:
        self.pm.create_pod("p1", "web")
        self.pm.add_container(
            "p1", "app", "python:3.11",
        )
        self.pm.add_sidecar(
            "p1", "proxy", "envoy",
        )
        assert self.pm.total_containers == 2


# ===================== DeploymentController =====================

class TestDeploymentController:
    """DeploymentController testleri."""

    def setup_method(self) -> None:
        self.dc = DeploymentController()

    def test_init(self) -> None:
        assert self.dc.deployment_count == 0
        assert self.dc.total_replicas == 0

    def test_create(self) -> None:
        result = self.dc.create(
            "web", "myapp:v1", replicas=3,
        )
        assert result["status"] == "available"
        assert result["replicas"] == 3
        assert self.dc.deployment_count == 1
        assert self.dc.total_replicas == 3

    def test_update_image(self) -> None:
        self.dc.create("web", "myapp:v1")
        result = self.dc.update(
            "web", image="myapp:v2",
        )
        assert result["revision"] == 2
        dep = self.dc.get("web")
        assert dep["image"] == "myapp:v2"

    def test_update_not_found(self) -> None:
        result = self.dc.update("ghost")
        assert "error" in result

    def test_rollback(self) -> None:
        self.dc.create("web", "myapp:v1")
        self.dc.update("web", image="myapp:v2")
        result = self.dc.rollback("web")
        assert result["rolled_back_to"] == 1
        dep = self.dc.get("web")
        assert dep["image"] == "myapp:v1"
        assert self.dc.rollback_count == 1

    def test_rollback_to_revision(self) -> None:
        self.dc.create("web", "myapp:v1")
        self.dc.update("web", image="myapp:v2")
        self.dc.update("web", image="myapp:v3")
        result = self.dc.rollback("web", to_revision=1)
        assert result["rolled_back_to"] == 1

    def test_rollback_not_found(self) -> None:
        result = self.dc.rollback("ghost")
        assert "error" in result

    def test_rollback_no_previous(self) -> None:
        self.dc.create("web", "myapp:v1")
        result = self.dc.rollback("web")
        assert result["error"] == "no_previous_revision"

    def test_scale(self) -> None:
        self.dc.create("web", "myapp:v1", replicas=1)
        result = self.dc.scale("web", 5)
        assert result["new_replicas"] == 5
        assert self.dc.total_replicas == 5
        assert self.dc.scale_count == 1

    def test_scale_not_found(self) -> None:
        result = self.dc.scale("ghost", 3)
        assert "error" in result

    def test_delete(self) -> None:
        self.dc.create("web", "myapp:v1")
        assert self.dc.delete("web") is True
        assert self.dc.deployment_count == 0

    def test_delete_not_found(self) -> None:
        assert self.dc.delete("ghost") is False

    def test_get_revision_history(self) -> None:
        self.dc.create("web", "myapp:v1")
        self.dc.update("web", image="myapp:v2")
        history = self.dc.get_revision_history("web")
        assert len(history) == 2

    def test_list_deployments(self) -> None:
        self.dc.create(
            "web", "myapp:v1", namespace="prod",
        )
        self.dc.create(
            "api", "api:v1", namespace="dev",
        )
        all_deps = self.dc.list_deployments()
        assert len(all_deps) == 2
        prod = self.dc.list_deployments(
            namespace="prod",
        )
        assert len(prod) == 1

    def test_get_history(self) -> None:
        self.dc.create("web", "myapp:v1")
        self.dc.update("web", image="myapp:v2")
        history = self.dc.get_history()
        assert len(history) >= 1


# ===================== ServiceExposer =====================

class TestServiceExposer:
    """ServiceExposer testleri."""

    def setup_method(self) -> None:
        self.se = ServiceExposer()

    def test_init(self) -> None:
        assert self.se.service_count == 0
        assert self.se.ingress_count == 0

    def test_create_service_clusterip(self) -> None:
        result = self.se.create_service(
            "web", "ClusterIP",
            ports=[{"port": 80, "target_port": 8000}],
        )
        assert result["type"] == "ClusterIP"
        assert self.se.service_count == 1

    def test_create_service_lb(self) -> None:
        result = self.se.create_service(
            "web", "LoadBalancer",
        )
        svc = self.se.get_service("web")
        assert svc["external_ip"] is not None

    def test_delete_service(self) -> None:
        self.se.create_service("web")
        assert self.se.delete_service("web") is True
        assert self.se.service_count == 0

    def test_delete_service_not_found(self) -> None:
        assert self.se.delete_service("ghost") is False

    def test_add_endpoint(self) -> None:
        self.se.create_service("web")
        result = self.se.add_endpoint(
            "web", "10.0.0.5", 8000,
        )
        assert result["endpoint"]["ip"] == "10.0.0.5"

    def test_add_endpoint_not_found(self) -> None:
        result = self.se.add_endpoint(
            "ghost", "10.0.0.5", 8000,
        )
        assert "error" in result

    def test_create_ingress(self) -> None:
        self.se.create_service("web")
        result = self.se.create_ingress(
            "web-ingress", "myapp.example.com",
            "web", 80,
        )
        assert result["host"] == "myapp.example.com"
        assert self.se.ingress_count == 1

    def test_create_ingress_tls(self) -> None:
        self.se.create_service("web")
        result = self.se.create_ingress(
            "web-tls", "myapp.example.com",
            "web", 443, tls=True,
        )
        assert result["tls"] is True

    def test_delete_ingress(self) -> None:
        self.se.create_ingress(
            "ing1", "host.com", "svc", 80,
        )
        assert self.se.delete_ingress("ing1") is True
        assert self.se.ingress_count == 0

    def test_set_tls(self) -> None:
        result = self.se.set_tls(
            "web-cert",
            issuer="letsencrypt",
        )
        assert result["issuer"] == "letsencrypt"
        assert self.se.tls_count == 1

    def test_add_dns_record(self) -> None:
        result = self.se.add_dns_record(
            "myapp.example.com", "A",
            "203.0.113.1",
        )
        assert result["hostname"] == "myapp.example.com"
        assert self.se.dns_count == 1

    def test_get_service(self) -> None:
        self.se.create_service("web")
        svc = self.se.get_service("web")
        assert svc is not None

    def test_get_ingress(self) -> None:
        self.se.create_ingress(
            "ing1", "host.com", "svc", 80,
        )
        ing = self.se.get_ingress("ing1")
        assert ing is not None

    def test_list_services(self) -> None:
        self.se.create_service("web", "ClusterIP")
        self.se.create_service("api", "LoadBalancer")
        all_svcs = self.se.list_services()
        assert len(all_svcs) == 2
        lb = self.se.list_services(
            service_type="LoadBalancer",
        )
        assert len(lb) == 1


# ===================== ResourceQuota =====================

class TestResourceQuota:
    """ResourceQuota testleri."""

    def setup_method(self) -> None:
        self.rq = ResourceQuota()

    def test_init(self) -> None:
        assert self.rq.quota_count == 0
        assert self.rq.limit_range_count == 0

    def test_set_quota(self) -> None:
        result = self.rq.set_quota(
            "prod",
            cpu_limit="8",
            memory_limit="16Gi",
        )
        assert result["namespace"] == "prod"
        assert self.rq.quota_count == 1

    def test_get_quota(self) -> None:
        self.rq.set_quota("prod")
        q = self.rq.get_quota("prod")
        assert q is not None
        assert q["cpu_limit"] == "4"

    def test_get_quota_not_found(self) -> None:
        assert self.rq.get_quota("ghost") is None

    def test_delete_quota(self) -> None:
        self.rq.set_quota("prod")
        assert self.rq.delete_quota("prod") is True
        assert self.rq.quota_count == 0

    def test_delete_quota_not_found(self) -> None:
        assert self.rq.delete_quota("ghost") is False

    def test_update_usage(self) -> None:
        self.rq.set_quota("prod")
        result = self.rq.update_usage(
            "prod", cpu=2.0, memory=4096.0,
        )
        assert result["cpu"] == 2.0

    def test_check_quota_allowed(self) -> None:
        self.rq.set_quota(
            "prod", cpu_limit="4",
            memory_limit="8Gi",
        )
        self.rq.update_usage(
            "prod", cpu=1.0, memory=2048.0,
        )
        result = self.rq.check_quota(
            "prod",
            request_cpu=1.0,
            request_memory=1024.0,
        )
        assert result["allowed"] is True

    def test_check_quota_exceeded(self) -> None:
        self.rq.set_quota(
            "prod", cpu_limit="4",
            memory_limit="8Gi",
        )
        self.rq.update_usage(
            "prod", cpu=3.5, memory=7000.0,
        )
        result = self.rq.check_quota(
            "prod",
            request_cpu=1.0,
            request_memory=2000.0,
        )
        assert result["allowed"] is False

    def test_check_quota_no_quota(self) -> None:
        result = self.rq.check_quota("dev")
        assert result["allowed"] is True

    def test_set_limit_range(self) -> None:
        result = self.rq.set_limit_range(
            "prod",
            min_cpu="100m", max_cpu="2",
        )
        assert result["namespace"] == "prod"
        assert self.rq.limit_range_count == 1

    def test_get_limit_range(self) -> None:
        self.rq.set_limit_range("prod")
        lr = self.rq.get_limit_range("prod")
        assert lr is not None
        assert lr["min"]["cpu"] == "100m"

    def test_set_priority_class(self) -> None:
        result = self.rq.set_priority_class(
            "high-priority", 1000,
        )
        assert result["value"] == 1000
        assert self.rq.priority_class_count == 1

    def test_get_priority_class(self) -> None:
        self.rq.set_priority_class(
            "critical", 10000,
        )
        pc = self.rq.get_priority_class("critical")
        assert pc is not None
        assert pc["value"] == 10000

    def test_get_usage(self) -> None:
        self.rq.set_quota("prod")
        self.rq.update_usage(
            "prod", cpu=1.0, memory=2048.0,
        )
        usage = self.rq.get_usage("prod")
        assert usage["cpu"] == 1.0

    def test_parse_memory_gi(self) -> None:
        assert self.rq._parse_memory("8Gi") == 8192.0

    def test_parse_memory_mi(self) -> None:
        assert self.rq._parse_memory("512Mi") == 512.0

    def test_parse_memory_ki(self) -> None:
        result = self.rq._parse_memory("1024Ki")
        assert result == 1.0


# ===================== HelmManager =====================

class TestHelmManager:
    """HelmManager testleri."""

    def setup_method(self) -> None:
        self.hm = HelmManager()

    def test_init(self) -> None:
        assert self.hm.chart_count == 0
        assert self.hm.release_count == 0
        assert self.hm.repo_count == 0

    def test_add_repo(self) -> None:
        result = self.hm.add_repo(
            "bitnami",
            "https://charts.bitnami.com/bitnami",
        )
        assert result["name"] == "bitnami"
        assert self.hm.repo_count == 1

    def test_register_chart(self) -> None:
        result = self.hm.register_chart(
            "myapp", version="1.0.0",
            values={"replicas": 1},
        )
        assert result["version"] == "1.0.0"
        assert self.hm.chart_count == 1

    def test_get_chart(self) -> None:
        self.hm.register_chart("myapp")
        chart = self.hm.get_chart("myapp")
        assert chart is not None

    def test_get_chart_not_found(self) -> None:
        assert self.hm.get_chart("ghost") is None

    def test_install(self) -> None:
        self.hm.register_chart(
            "myapp",
            values={"replicas": 1},
        )
        result = self.hm.install(
            "myapp-prod", "myapp",
            values={"replicas": 3},
        )
        assert result["status"] == "deployed"
        assert result["revision"] == 1
        assert self.hm.release_count == 1
        assert self.hm.install_count == 1

    def test_install_merges_values(self) -> None:
        self.hm.register_chart(
            "myapp",
            values={"replicas": 1, "debug": False},
        )
        self.hm.install(
            "myapp-prod", "myapp",
            values={"replicas": 3},
        )
        vals = self.hm.get_values("myapp-prod")
        assert vals["replicas"] == 3
        assert vals["debug"] is False

    def test_upgrade(self) -> None:
        self.hm.register_chart("myapp")
        self.hm.install("myapp-prod", "myapp")
        result = self.hm.upgrade(
            "myapp-prod",
            values={"replicas": 5},
        )
        assert result["revision"] == 2
        assert self.hm.upgrade_count == 1

    def test_upgrade_not_found(self) -> None:
        result = self.hm.upgrade("ghost")
        assert "error" in result

    def test_rollback(self) -> None:
        self.hm.register_chart(
            "myapp",
            values={"replicas": 1},
        )
        self.hm.install("myapp-prod", "myapp")
        self.hm.upgrade(
            "myapp-prod",
            values={"replicas": 5},
        )
        result = self.hm.rollback("myapp-prod")
        assert result["rolled_back_to"] == 1
        vals = self.hm.get_values("myapp-prod")
        assert vals["replicas"] == 1

    def test_rollback_to_revision(self) -> None:
        self.hm.register_chart("myapp")
        self.hm.install("rel1", "myapp")
        self.hm.upgrade("rel1", values={"v": 2})
        self.hm.upgrade("rel1", values={"v": 3})
        result = self.hm.rollback("rel1", to_revision=1)
        assert result["rolled_back_to"] == 1

    def test_rollback_not_found(self) -> None:
        result = self.hm.rollback("ghost")
        assert "error" in result

    def test_uninstall(self) -> None:
        self.hm.register_chart("myapp")
        self.hm.install("rel1", "myapp")
        assert self.hm.uninstall("rel1") is True
        assert self.hm.release_count == 0

    def test_uninstall_not_found(self) -> None:
        assert self.hm.uninstall("ghost") is False

    def test_get_release(self) -> None:
        self.hm.register_chart("myapp")
        self.hm.install("rel1", "myapp")
        rel = self.hm.get_release("rel1")
        assert rel is not None
        assert rel["status"] == "deployed"

    def test_get_release_history(self) -> None:
        self.hm.register_chart("myapp")
        self.hm.install("rel1", "myapp")
        self.hm.upgrade("rel1")
        history = self.hm.get_release_history("rel1")
        assert len(history) == 2

    def test_get_values(self) -> None:
        self.hm.register_chart(
            "myapp", values={"port": 8000},
        )
        self.hm.install("rel1", "myapp")
        vals = self.hm.get_values("rel1")
        assert vals["port"] == 8000

    def test_get_values_not_found(self) -> None:
        assert self.hm.get_values("ghost") == {}

    def test_list_releases(self) -> None:
        self.hm.register_chart("myapp")
        self.hm.install(
            "rel1", "myapp", namespace="prod",
        )
        self.hm.install(
            "rel2", "myapp", namespace="dev",
        )
        all_rels = self.hm.list_releases()
        assert len(all_rels) == 2
        prod = self.hm.list_releases(
            namespace="prod",
        )
        assert len(prod) == 1


# ===================== ContainerOrchestrator =====================

class TestContainerOrchestrator:
    """ContainerOrchestrator testleri."""

    def setup_method(self) -> None:
        self.orch = ContainerOrchestrator()

    def test_init(self) -> None:
        assert self.orch.is_initialized is False
        assert self.orch.autoscale_count == 0
        assert self.orch.event_count == 0

    def test_initialize(self) -> None:
        result = self.orch.initialize()
        assert result["status"] == "initialized"
        assert result["components"] == 8
        assert self.orch.is_initialized is True

    def test_build_and_push(self) -> None:
        result = self.orch.build_and_push(
            "myapp", "v1",
        )
        assert "build" in result
        assert "push" in result
        assert self.orch.event_count == 1

    def test_deploy(self) -> None:
        result = self.orch.deploy(
            "web", "myapp:v1",
            replicas=3,
            service_port=8000,
        )
        assert "deployment" in result
        assert "service" in result
        assert self.orch.event_count == 1

    def test_deploy_no_service(self) -> None:
        result = self.orch.deploy(
            "worker", "worker:v1",
        )
        assert "deployment" in result
        assert "service" not in result

    def test_set_autoscale(self) -> None:
        result = self.orch.set_autoscale(
            "web", min_replicas=2,
            max_replicas=10, target_cpu=75,
        )
        assert result["min"] == 2
        assert result["max"] == 10
        assert self.orch.autoscale_count == 1

    def test_check_autoscale_up(self) -> None:
        self.orch.deployments.create(
            "web", "myapp:v1", replicas=2,
        )
        self.orch.set_autoscale(
            "web", min_replicas=1,
            max_replicas=5, target_cpu=70,
        )
        result = self.orch.check_autoscale(
            "web", current_cpu=90,
        )
        assert result["action"] == "scale_up"

    def test_check_autoscale_down(self) -> None:
        self.orch.deployments.create(
            "web", "myapp:v1", replicas=5,
        )
        self.orch.set_autoscale(
            "web", min_replicas=1,
            max_replicas=10, target_cpu=70,
        )
        result = self.orch.check_autoscale(
            "web", current_cpu=20,
        )
        assert result["action"] == "scale_down"

    def test_check_autoscale_no_rule(self) -> None:
        result = self.orch.check_autoscale(
            "ghost", current_cpu=50,
        )
        assert result["action"] == "none"

    def test_get_snapshot(self) -> None:
        snap = self.orch.get_snapshot()
        assert "builds" in snap
        assert "images" in snap
        assert "containers" in snap
        assert "pods" in snap
        assert "deployments" in snap
        assert "services" in snap
        assert "helm_releases" in snap
        assert "initialized" in snap

    def test_get_analytics(self) -> None:
        analytics = self.orch.get_analytics()
        assert "builder" in analytics
        assert "registry" in analytics
        assert "runtime" in analytics
        assert "pods" in analytics
        assert "deployments" in analytics
        assert "services" in analytics
        assert "helm" in analytics

    def test_components(self) -> None:
        assert self.orch.builder is not None
        assert self.orch.registry is not None
        assert self.orch.runtime is not None
        assert self.orch.pods is not None
        assert self.orch.deployments is not None
        assert self.orch.services is not None
        assert self.orch.quotas is not None
        assert self.orch.helm is not None

    def test_get_events(self) -> None:
        self.orch.build_and_push("app", "v1")
        events = self.orch.get_events()
        assert len(events) >= 1


# ===================== Models =====================

class TestContainerModels:
    """Model testleri."""

    def test_container_status_enum(self) -> None:
        assert ContainerStatus.CREATED == "created"
        assert ContainerStatus.RUNNING == "running"
        assert ContainerStatus.STOPPED == "stopped"
        assert ContainerStatus.PAUSED == "paused"
        assert ContainerStatus.RESTARTING == "restarting"
        assert ContainerStatus.FAILED == "failed"

    def test_deployment_strategy_enum(self) -> None:
        assert DeploymentStrategy.ROLLING == "rolling"
        assert DeploymentStrategy.RECREATE == "recreate"
        assert DeploymentStrategy.BLUE_GREEN == "blue_green"
        assert DeploymentStrategy.CANARY == "canary"
        assert DeploymentStrategy.AB_TESTING == "ab_testing"
        assert DeploymentStrategy.SHADOW == "shadow"

    def test_service_type_enum(self) -> None:
        assert ServiceType.CLUSTER_IP == "ClusterIP"
        assert ServiceType.NODE_PORT == "NodePort"
        assert ServiceType.LOAD_BALANCER == "LoadBalancer"
        assert ServiceType.EXTERNAL_NAME == "ExternalName"
        assert ServiceType.HEADLESS == "Headless"
        assert ServiceType.INGRESS == "Ingress"

    def test_probe_type_enum(self) -> None:
        assert ProbeType.LIVENESS == "liveness"
        assert ProbeType.READINESS == "readiness"
        assert ProbeType.STARTUP == "startup"
        assert ProbeType.HTTP == "http"
        assert ProbeType.TCP == "tcp"
        assert ProbeType.EXEC == "exec"

    def test_resource_type_enum(self) -> None:
        assert ResourceType.CPU == "cpu"
        assert ResourceType.MEMORY == "memory"
        assert ResourceType.STORAGE == "storage"
        assert ResourceType.GPU == "gpu"
        assert ResourceType.NETWORK == "network"
        assert ResourceType.EPHEMERAL == "ephemeral"

    def test_chart_status_enum(self) -> None:
        assert ChartStatus.DEPLOYED == "deployed"
        assert ChartStatus.PENDING == "pending"
        assert ChartStatus.FAILED == "failed"
        assert ChartStatus.SUPERSEDED == "superseded"
        assert ChartStatus.UNINSTALLED == "uninstalled"
        assert ChartStatus.UPGRADING == "upgrading"

    def test_container_record(self) -> None:
        r = ContainerRecord(
            name="web", image="python:3.11",
            status=ContainerStatus.RUNNING,
        )
        assert r.name == "web"
        assert r.container_id

    def test_container_record_defaults(self) -> None:
        r = ContainerRecord()
        assert r.status == ContainerStatus.CREATED
        assert r.cpu_limit == ""

    def test_deployment_record(self) -> None:
        r = DeploymentRecord(
            name="web", replicas=3,
        )
        assert r.replicas == 3
        assert r.deployment_id

    def test_deployment_record_defaults(self) -> None:
        r = DeploymentRecord()
        assert r.strategy == DeploymentStrategy.ROLLING
        assert r.revision == 1

    def test_helm_release(self) -> None:
        r = HelmRelease(
            name="myapp", chart="myapp",
            version="1.0.0",
        )
        assert r.version == "1.0.0"
        assert r.release_id

    def test_helm_release_defaults(self) -> None:
        r = HelmRelease()
        assert r.status == ChartStatus.DEPLOYED
        assert r.version == "0.1.0"

    def test_container_snapshot(self) -> None:
        s = ContainerSnapshot(
            total_containers=10,
            running_containers=8,
        )
        assert s.total_containers == 10
        assert s.timestamp is not None

    def test_container_snapshot_defaults(self) -> None:
        s = ContainerSnapshot()
        assert s.total_containers == 0
        assert s.total_deployments == 0


# ===================== Config =====================

class TestContainerConfig:
    """Config testleri."""

    def test_container_enabled(self) -> None:
        from app.config import settings
        assert isinstance(
            settings.container_enabled, bool,
        )

    def test_default_cpu_limit(self) -> None:
        from app.config import settings
        assert isinstance(
            settings.default_cpu_limit, str,
        )

    def test_default_memory_limit(self) -> None:
        from app.config import settings
        assert isinstance(
            settings.default_memory_limit, str,
        )

    def test_registry_url(self) -> None:
        from app.config import settings
        assert isinstance(
            settings.registry_url, str,
        )

    def test_auto_cleanup(self) -> None:
        from app.config import settings
        assert isinstance(
            settings.auto_cleanup, bool,
        )


# ===================== Imports =====================

class TestContainerImports:
    """Import testleri."""

    def test_import_all(self) -> None:
        from app.core.container import (
            ContainerBuilder,
            ContainerOrchestrator,
            ContainerRuntime,
            DeploymentController,
            HelmManager,
            ImageRegistry,
            PodManager,
            ResourceQuota,
            ServiceExposer,
        )
        assert ContainerBuilder is not None
        assert ContainerOrchestrator is not None
        assert ContainerRuntime is not None
        assert DeploymentController is not None
        assert HelmManager is not None
        assert ImageRegistry is not None
        assert PodManager is not None
        assert ResourceQuota is not None
        assert ServiceExposer is not None
