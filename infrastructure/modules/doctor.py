"""Check host health and suggest fixes."""
import subprocess


def run_checks(host):
    print(f"Running doctor checks on {host['ip']}")
    # dependency check example
    try:
        subprocess.check_call(["docker", "ps"], stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Docker seems broken – consider reinstalling.")
    # port conflict example
    # thermal throttling placeholder
    print("Doctor: service checks complete.")
