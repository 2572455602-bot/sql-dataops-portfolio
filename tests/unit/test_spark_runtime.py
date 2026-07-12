import os

from ecommerce_dataops.spark_runtime import configure_java


def test_project_local_java_home_overrides_stale_environment(tmp_path, monkeypatch):
    java_home = tmp_path / ".tools" / "jdk-17"
    java_binary = java_home / "bin" / "java"
    java_binary.parent.mkdir(parents=True)
    java_binary.write_text("placeholder", encoding="utf-8")
    java_home_file = tmp_path / ".tools" / "java_home"
    java_home_file.write_text(str(java_home), encoding="utf-8")

    monkeypatch.setenv("JAVA_HOME", "/tmp/not-a-jdk")
    monkeypatch.setenv("PATH", "/usr/bin")
    configure_java(tmp_path)

    assert os.environ["JAVA_HOME"] == str(java_home)
    assert os.environ["PATH"].startswith(f"{java_home / 'bin'}:")
