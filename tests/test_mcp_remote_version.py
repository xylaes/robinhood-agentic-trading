import re
from pathlib import Path

def test_mcp_remote_version_pinned():
    """Verify that mcp-remote package invocations use pinned version @0.1.38 across codebase files."""
    files_to_check = [
        Path("trading_bot.py"),
        Path("portfolio_manager.py"),
        Path("test_connection.py")
    ]

    unpinned_pattern = re.compile(r'["\']mcp-remote["\']')
    pinned_pattern = re.compile(r'["\']mcp-remote@0\.1\.38["\']')

    for file_path in files_to_check:
        assert file_path.exists(), f"File {file_path} does not exist"
        content = file_path.read_text(encoding="utf-8")

        # Ensure no unpinned mcp-remote string exists
        assert not unpinned_pattern.search(content), f"Unpinned mcp-remote found in {file_path}"

        # Ensure pinned mcp-remote@0.1.38 string exists
        assert pinned_pattern.search(content), f"Pinned mcp-remote@0.1.38 not found in {file_path}"
