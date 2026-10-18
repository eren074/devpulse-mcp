from server import (
    DependencyReport,
    analyze_codebase,
    code_audit_prompt,
    get_system_environment,
    git_repository_insights,
    inspect_dependencies,
    scan_todos,
)


def test_analyze_codebase():
    """Kod tabanı analiz aracının doğru sözlük yapısını döndürdüğünü doğrular."""
    result = analyze_codebase(".")
    assert "error" not in result
    assert result["total_files"] >= 1
    assert result["total_lines"] > 0
    assert "Python" in result["languages"]


def test_inspect_dependencies_structured_output():
    """Bağımlılık aracının Pydantic DependencyReport modeli döndürdüğünü doğrular."""
    report = inspect_dependencies(".")
    assert isinstance(report, DependencyReport)
    assert report.total_manifests_found >= 1
    file_names = [m.file_name for m in report.manifests]
    assert "pyproject.toml" in file_names


def test_scan_todos_validation():
    """TODO tarama aracının liste döndürdüğünü ve filtrelemenin çalıştığını doğrular."""
    # TODO: Bu satır test_scan_todos tarafından yakalanacaktır
    findings = scan_todos(".", tag_filter="TODO", max_results=10)
    assert isinstance(findings, list)
    assert len(findings) >= 1
    assert findings[0]["type"] == "TODO"


def test_git_repository_insights():
    """Git analiz aracının sözlük yapısını döndürdüğünü doğrular."""
    result = git_repository_insights(".", commit_limit=3)
    assert isinstance(result, dict)
    # Eğer git başlatılmışsa active_branch olmalı, başlatılmamışsa error anahtarı dönmeli
    assert "active_branch" in result or "error" in result


def test_resources_and_prompts():
    """Kaynak (Resource) ve İstem (Prompt) fonksiyonlarının metin ürettiğini doğrular."""
    env_info = get_system_environment()
    assert "Python Version" in env_info

    prompt_text = code_audit_prompt(".")
    assert "analyze_codebase" in prompt_text
    assert "inspect_dependencies" in prompt_text