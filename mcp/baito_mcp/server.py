"""バイト求人 統合 MCP サーバー

バイトル / マイナビバイト / タウンワーク の全ツールを単一の FastMCP
インスタンスに登録する。ツール名はサイト接頭辞で区別する:

  baitoru_search / baitoru_search_station / baitoru_search_with_station
  mynavi_search / mynavi_get_detail / mynavi_search_station / mynavi_get_filters
  townwork_search / townwork_search_with_station / townwork_search_station / townwork_get_job_count
"""

from fastmcp import FastMCP

from . import baitoru_tools, mynavi_tools, townwork_tools

mcp = FastMCP("baito")

baitoru_tools.register(mcp)
mynavi_tools.register(mcp)
townwork_tools.register(mcp)


def main():
    """stdio で起動する（Claude Desktop 用）。"""
    mcp.run()


if __name__ == "__main__":
    main()
