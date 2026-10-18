import asyncio
import json
from mcp import Client

# Sunucumuzun Streamable HTTP adresi
SERVER_URL = "http://localhost:8000/mcp"


async def main() -> None:
    print(f"🔌 DevPulse MCP Sunucusuna bağlanılıyor: {SERVER_URL} ...\n")

    # 1. MCP İstemci oturumunu başlatıyoruz
    async with Client(SERVER_URL) as client:
        print("✅ Bağlantı başarılı!\n")

        # ====================================================================
        # A) SUNUCUDAKİ ARAÇLARI (TOOLS) KEŞFETME
        # ====================================================================
        tools_response = await client.list_tools()
        tools = getattr(tools_response, "tools", tools_response)

        print(f"🛠  Sunucuda Bulunan Araçlar ({len(tools)} adet):")
        for tool in tools:
            print(f"   • {tool.name}: {tool.title or ''}")
        print("-" * 60)

        # ====================================================================
        # B) ARAÇLARI ÇAĞIRMA (call_tool) VE STRUCTURED CONTENT OKUMA
        # ====================================================================

        # 1. Kod Tabanı Analizi Aracını Çağır
        print("\n📊 1. `analyze_codebase` aracı çalıştırılıyor...")
        code_res = await client.call_tool("analyze_codebase", {"directory_path": "."})
        print(json.dumps(code_res.structured_content, indent=2, ensure_ascii=False))

        # 2. Bağımlılık Analizi Aracını Çağır (Pydantic Structured Output)
        print("\n📦 2. `inspect_dependencies` (Pydantic Model) aracı çalıştırılıyor...")
        dep_res = await client.call_tool("inspect_dependencies", {"directory_path": "."})
        print(json.dumps(dep_res.structured_content, indent=2, ensure_ascii=False))

        # 3. Git Durumu Aracını Çağır
        print("\n🌿 3. `git_repository_insights` aracı çalıştırılıyor...")
        git_res = await client.call_tool(
            "git_repository_insights",
            {"directory_path": ".", "commit_limit": 3},
        )
        print(json.dumps(git_res.structured_content, indent=2, ensure_ascii=False))

        # 4. TODO / Teknik Borç Tarama Aracını Çağır
        print("\n🔍 4. `scan_todos` aracı çalıştırılıyor (Sadece TODO etiketleri)...")
        todo_res = await client.call_tool(
            "scan_todos",
            {"directory_path": ".", "tag_filter": "TODO", "max_results": 10},
        )
        print(json.dumps(todo_res.structured_content, indent=2, ensure_ascii=False))
        print("-" * 60)

        # ====================================================================
        # C) KAYNAKLARI (RESOURCES) OKUMA
        # ====================================================================
        print("\n💻 5. `system://environment` kaynağı (Resource) okunuyor...")
        sys_resource = await client.read_resource("system://environment")
        contents = getattr(sys_resource, "contents", sys_resource)
        for item in contents:
            if hasattr(item, "text"):
                print(item.text)
        print("-" * 60)

        # ====================================================================
        # D) İSTEM ŞABLONUNU (PROMPT) ÇEKME
        # ====================================================================
        print("\n💬 6. `code_audit_prompt` şablonu (Prompt) alınıyor...")
        prompt_res = await client.get_prompt("code_audit_prompt", {"directory_path": "."})
        for msg in prompt_res.messages:
            text = getattr(msg.content, "text", str(msg.content))
            print(f"[{msg.role}]:\n{text}")

    print("\n🏁 Tüm MCP testleri başarıyla tamamlandı ve bağlantı kapatıldı.")


if __name__ == "__main__":
    asyncio.run(main())