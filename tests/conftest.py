import os
import subprocess
import pytest


@pytest.fixture
def tmp_git_repo(tmp_path):
    """Repo Git minimal initialisé dans un dossier temporaire."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True, capture_output=True
    )
    # Premier commit pour avoir HEAD
    (tmp_path / "README.md").write_text("# Test repo")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True
    )
    return tmp_path


@pytest.fixture
def tmp_repo_with_conflict(tmp_git_repo):
    """Repo avec un conflit de merge prêt à résoudre."""
    repo = tmp_git_repo

    # Branche main : modifier fichier
    (repo / "file.txt").write_text("version main\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "main change"],
        cwd=repo, check=True, capture_output=True
    )

    # Branche feature : modifier même fichier
    subprocess.run(
        ["git", "checkout", "-b", "feature"],
        cwd=repo, check=True, capture_output=True
    )
    (repo / "file.txt").write_text("version feature\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feature change"],
        cwd=repo, check=True, capture_output=True
    )

    # Retour sur main + merge → conflit
    subprocess.run(
        ["git", "checkout", "master"],
        cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "merge", "feature", "--no-ff"],
        cwd=repo, capture_output=True  # pas check=True, va échouer
    )
    return repo
