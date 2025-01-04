import subprocess
import os

def setup_git_repo(repo_path, remote_url, branch):
    if not os.path.exists(os.path.join(repo_path, '.git')):
        subprocess.run(['git', 'init'], cwd=repo_path, check=True)
        subprocess.run(['git', 'remote', 'add', 'origin', remote_url], cwd=repo_path, check=True)
        subprocess.run(['git', 'checkout', '-b', branch], cwd=repo_path, check=True)

def commit_and_push(repo_path, commit_message, branch):
    subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
    subprocess.run(['git', 'commit', '-m', commit_message], cwd=repo_path, check=True)
    subprocess.run(['git', 'push', 'origin', branch], cwd=repo_path, check=True)
