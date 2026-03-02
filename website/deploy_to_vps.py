#!/usr/bin/env python3
"""Deploy website files to titanxanti.site VPS via SFTP."""
import os
import stat
import paramiko

VPS_HOST = "187.77.186.252"
VPS_USER = "root"
VPS_PASS = "Chilaw@123@llm"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
REMOTE_STAGE = "/tmp/website"
DEPLOY_SCRIPT = "/tmp/website/deploy.sh"

def upload_dir(sftp, local_path, remote_path):
    os.makedirs(local_path, exist_ok=True)
    try:
        sftp.stat(remote_path)
    except FileNotFoundError:
        sftp.mkdir(remote_path)

    for item in os.listdir(local_path):
        local_item = os.path.join(local_path, item)
        remote_item = remote_path + "/" + item
        if os.path.isdir(local_item):
            try:
                sftp.stat(remote_item)
            except FileNotFoundError:
                sftp.mkdir(remote_item)
            upload_dir(sftp, local_item, remote_item)
        else:
            print(f"  Uploading: {item}")
            sftp.put(local_item, remote_item)


def main():
    print(f"Connecting to {VPS_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=30)
    print("Connected!")

    print(f"\nUploading website files to {REMOTE_STAGE}...")
    sftp = ssh.open_sftp()
    try:
        sftp.stat(REMOTE_STAGE)
    except FileNotFoundError:
        sftp.mkdir(REMOTE_STAGE)
    upload_dir(sftp, LOCAL_DIR, REMOTE_STAGE)
    sftp.close()
    print("Upload complete!")

    print("\nMaking deploy.sh executable...")
    _, stdout, stderr = ssh.exec_command(f"chmod +x {DEPLOY_SCRIPT}")
    stdout.channel.recv_exit_status()

    print("Running deploy.sh on VPS (this may take a few minutes)...\n")
    _, stdout, stderr = ssh.exec_command(
        f"bash {DEPLOY_SCRIPT} 2>&1", get_pty=True
    )
    for line in iter(stdout.readline, ""):
        print(line, end="")

    err = stderr.read().decode()
    if err:
        print("\nSTDERR:", err)

    ssh.close()
    print("\nDeployment complete!")


if __name__ == "__main__":
    main()
