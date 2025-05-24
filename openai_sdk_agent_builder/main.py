# main.py

import os
import subprocess
import openai
import asyncio
import json
import inspect
import re
import random
import string
from typing import Callable
from pathlib import Path
from dotenv import load_dotenv
from instructions import INSTRUCTION  # Keep instructions in separate file

from datetime import datetime
import re, random, string

def generate_repo_name(prompt: str) -> str:
    prompt = prompt.lower().strip()
    keywords = re.findall(r"\b[a-z]{3,}\b", prompt)
    if not keywords:
        keywords = ["app"]
    base = "_".join(keywords[:4])
    base = re.sub(r"_+", "_", base).strip("_")
    
    # 🗓️ YYMMDD
    now = datetime.now()
    date = now.strftime("%y%m%d")
    
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))
    return f"{base}_{date}_{rand}"

# 🛠️ Tools
def write_file(path: str, content: str) -> str:
    if not path or not isinstance(path, str):
        return "❌ Error in write_file: invalid or empty path"

    # Ensure path is under 'generated_workflows/'
    if not path.startswith("generated_workflows/"):
        path = os.path.join("generated_workflows", path)

    full_path = os.path.abspath(path)

    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return f"📄 File written: `{path}`"
    except Exception as e:
        return f"❌ Error in write_file: {e}"


def run_shell(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout or result.stderr

def create_repo(path: str) -> str:
    full_path = os.path.join("generated_workflows", path)
    os.makedirs(full_path, exist_ok=True)
    return f"🏗 Repo created: `{path}`"

def launch_ngrok(port: int = 5000) -> str:
    import time
    ngrok = subprocess.Popen(
        ["ngrok", "http", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    time.sleep(2)
    result = subprocess.run("curl http://localhost:4040/api/tunnels", shell=True, capture_output=True, text=True)
    try:
        tunnels = json.loads(result.stdout)
        url = tunnels["tunnels"][0]["public_url"]
        return f"🌐 Live: `{url}`"
    except Exception as e:
        return f"❌ Ngrok failed: {e}"

def push_to_github(repo_name: str, local_path: str) -> str:
    user = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    if not user or not token:
        return "❌ GitHub credentials not set"
    repo_url = f"https://{user}:{token}@github.com/{user}/{repo_name}.git"
    subprocess.run(f"""
        curl -s -H "Authorization: token {token}" \
        -d '{{"name":"{repo_name}","private":true}}' \
        https://api.github.com/user/repos
    """, shell=True)
    cmds = f"""
        cd {local_path} && \
        git init && \
        git remote add origin {repo_url} && \
        git add . && \
        git commit -m "Initial commit" && \
        git branch -M main && \
        git push -u origin main
    """
    result = subprocess.run(cmds, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return f"❌ Git push failed: {result.stderr.strip()}"
    return f"🚀 GitHub: https://github.com/{user}/{repo_name}"

# 🔧 Tool schema generation
def infer_type(annotation):
    if annotation == str: return "string"
    elif annotation == int: return "integer"
    elif annotation == float: return "number"
    elif annotation == bool: return "boolean"
    return "string"

def generate_tool_schemas():
    tool_funcs = {
        "generate_repo_name": generate_repo_name,
        "create_repo": create_repo,
        "write_file": write_file,
        "run_shell": run_shell,
        "launch_ngrok": launch_ngrok,
        "push_to_github": push_to_github,
    }
    tools = []
    for name, fn in tool_funcs.items():
        sig = inspect.signature(fn)
        properties = {}
        required = []
        for param in sig.parameters.values():
            properties[param.name] = {
                "type": infer_type(param.annotation),
                "description": f"{param.name} parameter"
            }
            if param.default is param.empty:
                required.append(param.name)
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": f"Tool: {name}",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        })
    return tools

# 🧠 Assistant setup
def setup():
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    if not assistant_id:
        raise RuntimeError("❌ OPENAI_ASSISTANT_ID not set in .env")
    return openai, assistant_id

def update_assistant(client, assistant_id, tools):
    client.beta.assistants.update(
        assistant_id=assistant_id,
        instructions=INSTRUCTION,
        tools=tools
    )
    print("✅ Assistant updated with instructions + tools")

# 🔁 Logging wrapper
async def call_log(cb: Callable, msg: str):
    msg = msg[:1900]
    try:
        if inspect.iscoroutinefunction(cb):
            await cb(msg)
        else:
            cb(msg)
    except Exception as e:
        print(f"❌ Log callback failed: {e}")

# 🧠 Main agent execution
async def run_agent(prompt: str, log_callback=print):
    client, assistant_id = setup()
    tools = generate_tool_schemas()
    update_assistant(client, assistant_id, tools)

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)

    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if status.status == "completed":
            await call_log(log_callback, "✅ Done")
            break

        elif status.status == "requires_action":
            tool_calls = status.required_action.submit_tool_outputs.tool_calls
            results = []

            for call in tool_calls:
                fn = call.function.name
                args = json.loads(call.function.arguments)

                try:
                    if fn == "generate_repo_name":
                        out = generate_repo_name(**args)
                    elif fn == "create_repo":
                        out = create_repo(**args)
                    elif fn == "write_file":
                        out = write_file(**args)
                    elif fn == "run_shell":
                        if set(args.keys()) != {"command"}:
                            out = "❌ Error: 'run_shell' must only receive a single 'command' argument"
                        else:
                            out = run_shell(**args)
                    elif fn == "launch_ngrok":
                        out = launch_ngrok(**args)
                    elif fn == "push_to_github":
                        out = push_to_github(**args)
                    else:
                        out = f"⚠️ Unknown tool: {fn}"
                except Exception as e:
                    out = f"❌ Error in {fn}: {e}"

                await call_log(log_callback, out)
                results.append({ "tool_call_id": call.id, "output": out })

            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=results
            )

        await asyncio.sleep(1)

# 🖥️ CLI entry
def run():
    prompt = input("🧠 What should I build? ")
    asyncio.run(run_agent(prompt))

if __name__ == "__main__":
    run()
