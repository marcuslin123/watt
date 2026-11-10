"""Private stdio server. A run's scope is supplied by Watt, never by the model."""
import json
import sys
from .investigation import Scope, TOOLS, read_tool


def main():
    scope = Scope.model_validate_json(sys.argv[1])
    calls = 0
    descriptions = {
        "bridge": "Read posted and normalized margin and export credits by plan for both months.",
        "adjustments": "Read prior-service adjustments posted in the compared months.",
        "usage": "Read valid matched contracts with decreased grid imports; does not establish a cause.",
        "documents": "Read applicable prepared evidence, with effective dates and source IDs.",
    }
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request.get("method")
        if method == "initialize":
            result = {"protocolVersion": request["params"]["protocolVersion"],
                      "capabilities": {"tools": {}}, "serverInfo": {"name": "watt", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": [{"name": name, "description": descriptions[name],
                                 "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                                 "annotations": {"readOnlyHint": True, "destructiveHint": False,
                                                 "openWorldHint": False}} for name in TOOLS]}
        elif method == "tools/call":
            calls += 1
            params = request.get("params", {})
            try:
                if calls > 20 or params.get("name") not in TOOLS or params.get("arguments"):
                    raise ValueError("Tool call not permitted")
                value = read_tool(scope, params["name"])
                result = {"content": [{"type": "text", "text": json.dumps(value, default=str)}]}
            except Exception:
                result = {"isError": True, "content": [{"type": "text", "text": "Scoped tool unavailable."}]}
        else:
            result = {}
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)


if __name__ == "__main__":
    main()
