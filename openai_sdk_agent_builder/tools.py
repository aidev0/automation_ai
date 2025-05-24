# Tools
import os
import subprocess

def write_file(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return f"📄 {os.path.basename(path)} written"

def run_shell(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout or result.stderr

def create_repo(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return f"🏗 Repo created: {os.path.basename(path)}"

def launch_ngrok(port: int = 5000) -> str:
    result = subprocess.run(f"ngrok http {port} --log=stdout", shell=True, capture_output=True, text=True)
    return result.stdout

def push_to_github(repo_name: str, local_path: str) -> str:
    user = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    repo_url = f"https://{user}:{token}@github.com/{user}/{repo_name}.git"
    subprocess.run(f"""
        curl -s -H "Authorization: token {token}" \
        -d '{{"name":"{repo_name}","private":true}}' \
        https://api.github.com/user/repos
    """, shell=True)
    cmds = [
        f"cd {local_path}",
        "git init",
        f"git remote add origin {repo_url}",
        "git add .",
        'git commit -m "Initial commit"',
        "git branch -M main",
        "git push -u origin main"
    ]
    subprocess.run(" && ".join(cmds), shell=True)
    return f"🚀 Pushed to GitHub: {repo_name}"
