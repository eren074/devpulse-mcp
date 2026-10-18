# 🚀 DevPulse MCP — Kod Tabanı ve Teknik Borç Analiz Sunucusu

**DevPulse MCP**, resmi [Model Context Protocol (MCP) Python SDK (v2)](https://github.com/modelcontextprotocol/python-sdk) kullanılarak geliştirilmiş açık kaynaklı bir MCP sunucusu ve istemcisidir.

---

## 🎯 Projenin Amacı Nedir?

Yapay zeka asistanları (Claude Desktop, Cursor, VS Code Copilot vb.) bir yazılım projesini incelerken genellikle hangi dillerin kullanıldığını, hangi kütüphanelerin yüklü olduğunu, unutulmuş `TODO`/`FIXME` notlarını veya Git geçmişini tek seferde göremez.

**DevPulse MCP'nin amacı**, yerel bilgisayarınızdaki yazılım projelerinin röntgenini çekmek ve bu verileri standart **MCP protokolü** üzerinden yapay zeka modellerine güvenli, hızlı ve yapılandırılmış (tip güvenli) bir şekilde sunmaktır.

---

## ⚙️ Ne İşe Yarar? (Özellikler ve Araçlar)

Sunucu, yapay zeka asistanlarına **4 ana araç (`Tool`)**, **2 sistem kaynağı (`Resource`)** ve **1 hazır denetim şablonu (`Prompt`)** kazandırır:

### 🛠️ 1. Araçlar (Tools)
* **`analyze_codebase` (Kod Tabanı İstatistikleri):**
  Proje klasöründeki tüm kaynak kod dosyalarını tarar; hangi programlama dilinden kaç dosya ve toplam kaç satır kod bulunduğunu hesaplar.
* **`inspect_dependencies` (Bağımlılık ve Kütüphane Analizi):**
  Projedeki `pyproject.toml`, `requirements.txt` (Python) ve `package.json` (Node.js) dosyalarını otomatik okur. Kullanılan kütüphaneleri **Pydantic Structured Output (`DependencyReport`)** şemasıyla doğrulanmış olarak döndürür.
* **`scan_todos` (Teknik Borç Tarayıcı):**
  Kod dosyalarının içinde unutulmuş `TODO`, `FIXME` ve `BUG` etiketlerini tarar; hangi dosyanın kaçıncı satırında ne yazdığını listeler.
* **`git_repository_insights` (Git Geçmişi ve Durum Analizi):**
  Projenin aktif Git dalını (`branch`), henüz kaydedilmemiş (`uncommitted`) dosya değişikliklerini ve son commit mesajlarını raporlar.

### 📦 2. Kaynaklar (Resources)
* **`system://environment`:** Çalışılan ortamın işletim sistemi, mimari ve Python sürüm bilgisini sunar.
* **`project://readme/{project_name}`:** Projenin `README.md` dosyasını LLM'e bağlam (context) olarak okur.

### 💬 3. Hazır İstem Şablonu (Prompt)
* **`code_audit_prompt`:** Yapay zekanın yukarıdaki tüm araçları sırasıyla çalıştırarak projede kapsamlı bir mimari denetim yapmasını sağlayan hazır mühendislik şablonudur.

---

## 🔒 Güvenlik Mimarisi (Security by Design)

DevPulse MCP, yerel dosya sistemiyle çalıştığı için katı güvenlik önlemleriyle donatılmıştır:
- **Salt Okunur Çalışma (`read_only_hint=True`):** Hiçbir dosyayı değiştirmez, silmez veya dış internete veri göndermez (`open_world_hint=False`).
- **Path Traversal & Sistem Dizini Engeli:** `/etc`, `/var`, `/System` gibi işletim sistemi dizinlerine ve `.ssh`, `.aws`, `.gnupg` gibi anahtar klasörlerine erişimi otomatik reddeder.
- **Hassas Dosya ve Symlink Koruması:** `.env`, `secret`, `token`, `credentials` içeren dosya adlarını ve sembolik bağlantıları (`symlink`) tarama dışı bırakır.
- **Komut Enjeksiyonu (Command Injection) Koruması:** Git alt süreçleri `shell=False` ve zaman aşımı (`timeout`) sınırıyla izole çalıştırılır.
- **DoS / Kilitlenme Koruması:** Maksimum klasör derinliği (`max_depth=2`), dosya boyutu sınırı (`1 MB`) ve dosya sayısı sınırı ile büyük dizinlerde zaman aşımını önler.

---

## 💻 Bilgisayara Nasıl Kurulur ve Çalıştırılır?

### Gereksinimler
- **Python 3.11** veya daha güncel bir sürüm
- **[uv](https://docs.astral.sh/uv/)** (Modern Python paket yöneticisi)

### Adım 1: Projeyi İndirin ve Bağımlılıkları Kurun

Terminalinizi açın ve aşağıdaki komutları sırasıyla çalıştırın:

```bash
# 1. Eğer bilgisayarınızda 'uv' yüklü değilse kurun (macOS / Linux):
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# 2. Repoyu bilgisayarınıza klonlayın ve klasöre girin:
git clone [https://github.com/eren074/devpulse-mcp.git](https://github.com/eren074/devpulse-mcp.git)
cd devpulse-mcp

# 3. Bağımlılıkları sanal ortama yükleyin:
uv sync
```

### Adım 2: Sunucuyu Test Edin

Projeyi kurduktan sonra doğru çalıştığını doğrulamak için 3 farklı test yöntemini kullanabilirsiniz:

```bash
# Yöntem A: Terminalde 1 saniyelik hızlı tanı testi
uv run python server.py --test

# Yöntem B: Otomatik birim testlerini (pytest) çalıştırma
uv run pytest -v

# Yöntem C: MCP Inspector ile tarayıcıda görsel test (Node.js / npx gerektirir)
uv run mcp dev server.py
```

---

## 🔌 Python İstemcisi (`client.py`) ile Kod İçinden Kullanım

Bu repo aynı zamanda sunucuya **Streamable HTTP** protokolüyle bağlanan örnek bir Python istemcisi (`client.py`) içerir. Denemek için iki ayrı terminal açın:

**1. Terminal (Sunucuyu Başlatın):**
```bash
uv run mcp run server.py --transport streamable-http
```

**2. Terminal (İstemciyi Çalıştırın):**
```bash
uv run python client.py
```

---

## 🤖 Cursor, VS Code veya Claude Desktop'a Nasıl Bağlanır?

Sunucuyu kullandığınız yapay zeka uygulamasına bağlamak için uygulamanın MCP ayar dosyasına aşağıdaki JSON bloğunu eklemeniz yeterlidir ( `/TAM/DOSYA/YOLU/devpulse-mcp` kısmına projeyi indirdiğiniz klasörün tam yolunu yazın):

### Cursor (`.cursor/mcp.json`) veya Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "devpulse": {
      "command": "uv",
      "args": [
        "--directory",
        "/TAM/DOSYA/YOLU/devpulse-mcp",
        "run",
        "server.py"
      ]
    }
  }
}
```

### VS Code GitHub Copilot (`.vscode/mcp.json`)
```json
{
  "servers": {
    "devpulse": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/TAM/DOSYA/YOLU/devpulse-mcp",
        "run",
        "server.py"
      ]
    }
  }
}
```

Bağlantıyı yaptıktan sonra yapay zeka asistanınıza şu soruyu sorarak sunucuyu kullanmaya başlayabilirsiniz:
> *"DevPulse araçlarını kullanarak projemin dil dağılımını, bağımlılıklarını, Git durumunu ve unutulmuş TODO notlarını analiz et."*

---

## 📄 Lisans
Bu proje MIT Lisansı altında lisanslanmıştır.