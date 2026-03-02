"""Provisioning helpers: SSH, Ansible execution, etc."""
import subprocess


def run_ansible_playbook(host, playbook):
    cmd = [
        "ansible-playbook",
        "-i",
        f"{host['ip']},",
        playbook,
        "-u",
        host.get("user", "root"),
    ]
    if host.get("ssh_key"):
        cmd.extend(["--private-key", host["ssh_key"]])
    print("Running", " ".join(cmd))
    subprocess.check_call(cmd)
