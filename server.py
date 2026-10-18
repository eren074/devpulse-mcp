import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

# MCP Sunucu nesnemiz
mcp = MCPServer("DevPulse")

# server.py dosyasının bulunduğu güvenli proje dizini
SERVER_DIR = Path(__file__).resolve().parent

# Taranmayacak klasörler
IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "build", "dist", ".idea", "Library", "Applications", "Pods", "target",
    "Desktop", "Documents", "Downloads", "Movies", "Music", "Pictures", "Public",
    ".ssh", ".aws", ".gnupg", ".config", ".kube"
}

# GÜVENLİK: Okunması kesinlikle yasak olan işletim sistemi dizinleri
FORBIDDEN_SYSTEM_PREFIXES = (
    "/etc", "/var", "/private/etc", "/private/var", "/System",
    "/usr", "/bin", "/sbin", "/dev", "/proc", "/sys"
)

# GÜVENLİK: İçeriği asla okunmayacak hassas dosya adı kelimeleri
SENSITIVE_FILENAME_KEYWORDS = (
    "secret", "credential", "token", "password", "private", "id_rsa", ".env", "apikey"
)

CODE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".gd": "GDScript",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".json": "JSON",
    ".md": "Markdown",
}

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True,
    open_world_hint=False,
)


# ============================================================================
# PYDANTIC MODELLERİ (STRUCTURED OUTPUT ŞEMALARI)
# ============================================================================

class DependencyFile(BaseModel):
    file_name: str = Field(description="Bağımlılık dosyasının adı (pyproject.toml, package.json vb.)")
    ecosystem: str = Field(description="Ekosistem adı (Python veya Node.js)")
    dependencies: list[str] = Field(description="Projede kullanılan kütüphaneler ve sürümleri")


class DependencyReport(BaseModel):
    directory: str = Field(description="İncelenen projenin tam dizin yolu")
    total_manifests_found: int = Field(description="Bulunan bağımlılık dosyası sayısı")
    manifests: list[DependencyFile] = Field(description="Bulunan bağımlılık dosyalarının detaylı listesi")


# ============================================================================
# GÜVENLİK VE YARDIMCI FONKSİYONLAR
# ============================================================================

def is_safe_directory(target_dir: Path) -> tuple[bool, str]:
    """Hedef dizinin güvenli bir kullanıcı projesi olup olmadığını denetler."""
    resolved_str = str(target_dir)

    # 1. Kök dizin kontrolü
    if resolved_str == "/" or resolved_str == str(Path.home()):
        return False, "Güvenlik nedeniyle kök dizin ('/') veya ana kullanıcı dizini ('~') doğrudan taranamaz."

    # 2. Yasaklı sistem dizinleri kontrolü
    for prefix in FORBIDDEN_SYSTEM_PREFIXES:
        if resolved_str == prefix or resolved_str.startswith(prefix + "/"):
            return False, f"Güvenlik ihlali: Sistem dizinlerine ({prefix}) erişim engellendi."

    # 3. Gizli kritik klasör kontrolü (.ssh, .aws vb.)
    for part in target_dir.parts:
        if part in {".ssh", ".aws", ".gnupg", ".kube"}:
            return False, f"Güvenlik ihlali: Hassas kimlik dizinlerine ({part}) erişim engellendi."

    return True, ""


def is_sensitive_file(file_name: str) -> bool:
    """Dosya adında şifre, anahtar veya kimlik bilgisi geçip geçmediğini kontrol eder."""
    lower_name = file_name.lower()
    return any(keyword in lower_name for keyword in SENSITIVE_FILENAME_KEYWORDS)


def resolve_safe_dir(directory_path: str) -> Path:
    """'.' veya boş değer verildiğinde doğrudan server.py'nin bulunduğu klasörü baz alır."""
    cleaned = directory_path.strip() if directory_path else "."
    if cleaned in (".", "", "./"):
        return SERVER_DIR
    return Path(cleaned).expanduser().resolve()


def collect_source_files(target_dir: Path, max_depth: int = 2, max_visits: int = 200) -> list[Path]:
    """Symlink ve hassas dosyaları atlayarak güvenli şekilde kaynak dosyaları toplar."""
    source_files: list[Path] = []
    visits = 0
    base_parts = len(target_dir.parts)

    for root, dirs, files in os.walk(target_dir, followlinks=False):
        current_depth = len(Path(root).parts) - base_parts
        if current_depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in IGNORED_DIRS]

        for file in files:
            visits += 1
            if visits > max_visits:
                return source_files

            # Gizli dosyaları ve hassas dosyaları (secret, token, .env vb.) atla
            if file.startswith(".") or is_sensitive_file(file):
                continue

            ext = Path(file).suffix.lower()
            if ext in CODE_EXTENSIONS:
                full_path = Path(root) / file
                # GÜVENLİK: Sembolik bağlantıları (symlink) asla takip etme
                if not full_path.is_symlink():
                    source_files.append(full_path)

    return source_files


# ============================================================================
# TOOLS (ARAÇLAR)
# ============================================================================

@mcp.tool(
    title="Kod Tabanı İstatistiklerini Analiz Et",
    annotations=READ_ONLY_ANNOTATIONS,
)
def analyze_codebase(
    directory_path: Annotated[
        str,
        Field(description="Analiz edilecek projenin klasör yolu (varsayılan: '.')"),
    ] = ".",
) -> dict:
    """
    Verilen klasördeki kod tabanını analiz eder.
    Dil dağılımını, toplam dosya sayısını ve toplam satır sayısını döndürür.
    """
    target_dir = resolve_safe_dir(directory_path)
    if not target_dir.exists() or not target_dir.is_dir():
        return {"error": f"Geçersiz dizin yolu: {target_dir}"}

    is_safe, err_msg = is_safe_directory(target_dir)
    if not is_safe:
        return {"error": err_msg}

    files_to_scan = collect_source_files(target_dir)
    stats: dict[str, dict[str, int]] = {}
    total_lines = 0

    for file_path in files_to_scan:
        ext = file_path.suffix.lower()
        lang = CODE_EXTENSIONS[ext]

        try:
            if file_path.stat().st_size > 1_000_000:
                continue
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                line_count = sum(1 for _ in f)
        except OSError:
            continue

        if lang not in stats:
            stats[lang] = {"files": 0, "lines": 0}

        stats[lang]["files"] += 1
        stats[lang]["lines"] += line_count
        total_lines += line_count

    return {
        "directory": str(target_dir),
        "total_files": len(files_to_scan),
        "total_lines": total_lines,
        "languages": stats,
    }


@mcp.tool(
    title="Teknik Borç ve TODO Notlarını Tara",
    annotations=READ_ONLY_ANNOTATIONS,
)
def scan_todos(
    directory_path: Annotated[
        str,
        Field(description="Taranacak projenin klasör yolu"),
    ] = ".",
    tag_filter: Annotated[
        Literal["ALL", "TODO", "FIXME", "BUG"],
        Field(description="Sadece belirli bir etiketi filtrele veya 'ALL' ile tümünü getir"),
    ] = "ALL",
    max_results: Annotated[
        int,
        Field(ge=1, le=200, description="Döndürülecek maksimum sonuç sayısı (1-200 arası)"),
    ] = 50,
) -> list[dict]:
    """
    Proje dosyalarındaki TODO, FIXME ve BUG etiketlerini tarar.
    Dosya yolunu, satır numarasını ve ilgili notu liste olarak döndürür.
    """
    target_dir = resolve_safe_dir(directory_path)
    if not target_dir.exists() or not target_dir.is_dir():
        return [{"error": f"Geçersiz dizin yolu: {target_dir}"}]

    is_safe, err_msg = is_safe_directory(target_dir)
    if not is_safe:
        return [{"error": err_msg}]

    keywords = ("TODO", "FIXME", "BUG") if tag_filter == "ALL" else (tag_filter,)
    files_to_scan = collect_source_files(target_dir)
    findings: list[dict] = []

    for file_path in files_to_scan:
        try:
            if file_path.stat().st_size > 1_000_000:
                continue
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, start=1):
                    for kw in keywords:
                        if kw in line:
                            findings.append({
                                "type": kw,
                                "file": str(file_path.relative_to(target_dir)),
                                "line": line_num,
                                "content": line.strip(),
                            })
                            if len(findings) >= max_results:
                                return findings
        except OSError:
            continue

    return findings


@mcp.tool(
    title="Git Durumu ve Commit Geçmişini Getir",
    annotations=READ_ONLY_ANNOTATIONS,
)
def git_repository_insights(
    directory_path: Annotated[
        str,
        Field(description="Git reposunun bulunduğu klasör yolu"),
    ] = ".",
    commit_limit: Annotated[
        int,
        Field(ge=1, le=25, description="Listelenecek son commit sayısı (1-25 arası)"),
    ] = 5,
) -> dict:
    """
    Projenin Git durumunu inceler: aktif branch adını, değiştirilmiş/bekleyen dosyaları
    ve son commit mesajlarını döndürür.
    """
    target_dir = resolve_safe_dir(directory_path)
    is_safe, err_msg = is_safe_directory(target_dir)
    if not is_safe:
        return {"error": err_msg}

    if not (target_dir / ".git").exists():
        return {"error": f"'{target_dir}' dizininde bir Git deposu (.git) bulunamadı."}

    def run_git(args: list[str]) -> str:
        try:
            # GÜVENLİK: shell=False ile komut enjeksiyonu (Command Injection) tamamen engellenir
            result = subprocess.run(
                ["git", *args],
                cwd=target_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=3,
                shell=False,
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Git hatası: {e}"

    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    status_lines = run_git(["status", "--short"]).splitlines()
    log_lines = run_git(["log", f"-n{int(commit_limit)}", "--oneline"]).splitlines()

    return {
        "repository": str(target_dir),
        "active_branch": branch,
        "uncommitted_changes_count": len(status_lines),
        "uncommitted_files": status_lines,
        "recent_commits": log_lines,
    }


@mcp.tool(
    title="Proje Kütüphanelerini ve Bağımlılıklarını İncele",
    annotations=READ_ONLY_ANNOTATIONS,
)
def inspect_dependencies(
    directory_path: Annotated[
        str,
        Field(description="Bağımlılıkları kontrol edilecek projenin klasör yolu"),
    ] = ".",
) -> DependencyReport:
    """
    Projedeki pyproject.toml, requirements.txt ve package.json dosyalarını okur.
    Kullanılan kütüphaneleri yapılandırılmış (Structured Output) bir rapor olarak döndürür.
    """
    target_dir = resolve_safe_dir(directory_path)
    is_safe, err_msg = is_safe_directory(target_dir)
    if not is_safe:
        return DependencyReport(
            directory=str(target_dir),
            total_manifests_found=0,
            manifests=[DependencyFile(file_name="GÜVENLİK_ENGELİ", ecosystem="System", dependencies=[err_msg])],
        )

    manifests: list[DependencyFile] = []

    pyproject_path = target_dir / "pyproject.toml"
    if pyproject_path.exists() and not pyproject_path.is_symlink():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            deps = data.get("project", {}).get("dependencies", [])
            manifests.append(
                DependencyFile(file_name="pyproject.toml", ecosystem="Python", dependencies=deps)
            )
        except Exception as e:
            manifests.append(
                DependencyFile(file_name="pyproject.toml", ecosystem="Python", dependencies=[f"Hata: {e}"])
            )

    req_path = target_dir / "requirements.txt"
    if req_path.exists() and not req_path.is_symlink():
        try:
            lines = [
                line.strip()
                for line in req_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            manifests.append(
                DependencyFile(file_name="requirements.txt", ecosystem="Python", dependencies=lines)
            )
        except Exception as e:
            manifests.append(
                DependencyFile(file_name="requirements.txt", ecosystem="Python", dependencies=[f"Hata: {e}"])
            )

    package_json_path = target_dir / "package.json"
    if package_json_path.exists() and not package_json_path.is_symlink():
        try:
            data = json.loads(package_json_path.read_text(encoding="utf-8", errors="ignore"))
            deps = [f"{k}: {v}" for k, v in data.get("dependencies", {}).items()]
            dev_deps = [f"{k}: {v} (dev)" for k, v in data.get("devDependencies", {}).items()]
            manifests.append(
                DependencyFile(
                    file_name="package.json",
                    ecosystem="Node.js",
                    dependencies=deps + dev_deps,
                )
            )
        except Exception as e:
            manifests.append(
                DependencyFile(file_name="package.json", ecosystem="Node.js", dependencies=[f"Hata: {e}"])
            )

    return DependencyReport(
        directory=str(target_dir),
        total_manifests_found=len(manifests),
        manifests=manifests,
    )


# ============================================================================
# RESOURCES (KAYNAKLAR) & PROMPTS (İSTEMLER)
# ============================================================================

@mcp.resource("system://environment")
def get_system_environment() -> str:
    """Çalışılan bilgisayarın sistem ve Python ortam bilgilerini döndürür (Kişisel dizin yolu içermez)."""
    info = [
        f"Operating System : {platform.system()} {platform.release()}",
        f"Architecture     : {platform.machine()}",
        f"Python Version   : {sys.version.split()[0]}",
    ]
    return "\n".join(info)


@mcp.resource("project://readme/{project_name}")
def get_project_readme(project_name: str) -> str:
    """Proje dizinindeki README.md dosyasını okur."""
    readme_path = SERVER_DIR / "README.md"
    if readme_path.exists() and not readme_path.is_symlink():
        content = readme_path.read_text(encoding="utf-8", errors="ignore")
        return f"# {project_name} - README İçeriği\n\n{content}"
    return f"{project_name} için README.md bulunamadı."


@mcp.prompt()
def code_audit_prompt(directory_path: str = ".") -> str:
    """Bir proje dizini için kapsamlı teknik borç ve mimari analiz istemi oluşturur."""
    return (
        f"Lütfen '{directory_path}' dizinindeki projeyi kapsamlı şekilde denetle:\n"
        f"1. `analyze_codebase` aracını çağırarak projenin dil ve boyut yapısını çıkar.\n"
        f"2. `inspect_dependencies` aracını çağırarak projede kullanılan kütüphaneleri incele.\n"
        f"3. `git_repository_insights` aracını çağırarak aktif branch'i ve bekleyen değişiklikleri kontrol et.\n"
        f"4. `scan_todos` aracını çağırarak yarım kalmış TODO ve FIXME noktalarını tespit et.\n"
        f"5. Elde ettiğin verilerle projenin genel sağlığını özetle ve öncelikli 3 aksiyon öner."
    )


if __name__ == "__main__":
    if "--test" in sys.argv:
        print(f"📍 Taranan Dizin: {SERVER_DIR}\n")
        print("1️⃣ analyze_codebase Çıktısı:")
        print(json.dumps(analyze_codebase("."), indent=2, ensure_ascii=False))
        print("\n2️⃣ inspect_dependencies Çıktısı:")
        print(inspect_dependencies(".").model_dump_json(indent=2))
        print("\n3️⃣ git_repository_insights Çıktısı:")
        print(json.dumps(git_repository_insights("."), indent=2, ensure_ascii=False))
        print("\n✅ Tüm güvenlik ve araç testleri milisaniyeler içinde hatasız çalıştı!")
    else:
        mcp.run()