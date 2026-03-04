import argparse
import json
import os
import sys

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def run(server_command: str, server_args: list[str], server_env: dict[str, str], tool_name: str, tool_args: dict):
    params = StdioServerParameters(
        command=server_command,
        args=server_args,
        env={**os.environ, **server_env},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=tool_args)
            print(result.model_dump_json())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-command", required=True)
    parser.add_argument("--server-args-json", required=True)
    parser.add_argument("--server-env-json", required=True)
    parser.add_argument("--tool-name", required=True)
    parser.add_argument("--tool-args-json", required=True)
    args = parser.parse_args()

    try:
        anyio.run(
            run,
            args.server_command,
            json.loads(args.server_args_json),
            json.loads(args.server_env_json),
            args.tool_name,
            json.loads(args.tool_args_json),
            backend="asyncio",
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
