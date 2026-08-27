"""Tests for the Kubernetes cluster simulator."""

from __future__ import annotations

import pytest

from services.kubernetes.simulator import (
    ContainerStatus,
    DeploymentInfo,
    K8sSimulator,
    PodInfo,
    PodPhase,
)


class TestK8sSimulator:
    """Tests for K8sSimulator."""

    def test_simulate_missing_env_var(self, k8s_simulator):
        """Missing env var scenario generates CrashLoopBackOff state."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="missing_env_var",
        )

        assert result["scenario"] == "missing_env_var"
        assert "DATABASE_URL" in result["description"]
        assert "pod" in result
        assert "deployment" in result
        assert "cluster_events" in result
        assert "kubernetes_logs" in result

        # Pod should be in CrashLoopBackOff
        pod = result["pod"]
        assert pod["metadata"]["namespace"] == "default"
        assert pod["metadata"]["labels"]["app"] == "sentinel-api"

        # Main container should not be ready
        containers = pod["spec"]["containers"]
        main_container = next(c for c in containers if c["name"] == "sentinel-api")
        assert main_container["ready"] is False
        assert main_container["state_reason"] == "CrashLoopBackOff"
        assert main_container["restart_count"] > 0

    def test_simulate_oom(self, k8s_simulator):
        """OOM scenario generates OOMKilled state."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="out_of_memory",
        )

        assert result["scenario"] == "out_of_memory"
        pod = result["pod"]
        containers = pod["spec"]["containers"]
        main_container = next(c for c in containers if c["name"] == "sentinel-api")
        assert main_container["exit_code"] == 137
        assert main_container["state_reason"] == "OOMKilled"

    def test_simulate_image_pull_error(self, k8s_simulator):
        """Image pull error scenario generates ImagePullBackOff."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="image_pull_error",
        )

        assert result["scenario"] == "image_pull_error"
        pod = result["pod"]
        containers = pod["spec"]["containers"]
        main_container = next(c for c in containers if c["name"] == "sentinel-api")
        assert "INVALID" in main_container["image"]
        assert main_container["state_reason"] == "ImagePullBackOff"

    def test_simulate_app_error(self, k8s_simulator):
        """Application error scenario generates exit code 1."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="application_error",
        )

        assert result["scenario"] == "application_error"
        pod = result["pod"]
        containers = pod["spec"]["containers"]
        main_container = next(c for c in containers if c["name"] == "sentinel-api")
        assert main_container["exit_code"] == 1

    def test_deployment_state_reflects_failure(self, k8s_simulator):
        """Deployment state shows 0 ready replicas on failure."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="missing_env_var",
        )

        deployment = result["deployment"]
        assert deployment["spec"]["replicas"] == 3
        assert deployment["status"]["ready_replicas"] == 0
        assert deployment["status"]["available_replicas"] == 0

    def test_cluster_events_present(self, k8s_simulator):
        """Cluster events include warning events about the failure."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="missing_env_var",
        )

        events = result["cluster_events"]
        assert len(events) > 0

        warning_events = [e for e in events if e.get("type") == "Warning"]
        assert len(warning_events) > 0

    def test_kubernetes_logs_generated(self, k8s_simulator):
        """Missing env var scenario generates application logs."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="missing_env_var",
        )

        logs = result["kubernetes_logs"]
        assert len(logs) > 0
        assert any("DATABASE_URL" in log["message"] for log in logs)
        assert any(log["level"] == "ERROR" for log in logs)

    def test_configmap_status(self, k8s_simulator):
        """Missing env var scenario shows configmap status."""
        result = k8s_simulator.simulate_crashloop_backoff(
            service_name="sentinel-api",
            failure_reason="missing_env_var",
        )

        configmap = result["configmap_status"]
        assert configmap["name"] == "app-config"
        assert configmap["exists"] is True
        assert "DATABASE_URL" in configmap["missing_keys"]

    def test_different_service_names(self, k8s_simulator):
        """Simulator works with different service names."""
        for service in ["api-gateway", "worker-service", "auth-service"]:
            result = k8s_simulator.simulate_crashloop_backoff(
                service_name=service,
                failure_reason="missing_env_var",
            )
            assert result["pod"]["metadata"]["labels"]["app"] == service


class TestPodPhase:
    """Tests for PodPhase enum."""

    def test_all_phases(self):
        assert PodPhase.PENDING.value == "Pending"
        assert PodPhase.RUNNING.value == "Running"
        assert PodPhase.SUCCEEDED.value == "Succeeded"
        assert PodPhase.FAILED.value == "Failed"
        assert PodPhase.UNKNOWN.value == "Unknown"
