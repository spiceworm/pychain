#!/usr/bin/env python3
"""
Script used to generate docker-compose files with a variable number
of client node containers dictated by `client_count` argument.
"""
import argparse
import os
import subprocess
import tempfile


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("client_count", type=int)
    parser.add_argument("-e", "--environment", action="append", default=[])
    return parser.parse_args()


def main(args: argparse.Namespace):
    header = """
version: "3.7"
services:
    """
    boot_node_template = """
    boot_{n}:
        image: pychain_node
        build:
            context: '.'
            dockerfile: './apps/node/Dockerfile'
        networks:
            default:
                aliases:
                    - 'boot.com'
    """

    client_node_template = """
    client_{n}:
        image: pychain_node
        build:
            context: '.'
            dockerfile: './apps/node/Dockerfile'
        environment:
            BOOT_NODE: 'boot.com'
{env}
            # NETWORK_SYNC_INTERVAL: '5'
    """

    environment = []
    for env in args.environment:
        var, val = env.split("=")
        environment.append(f"            {var}: '{val}'")
    environment_variables = "\n".join(environment)

    with tempfile.NamedTemporaryFile("w", dir=".", delete=False) as f:
        f.write(header)
        f.write(boot_node_template.format(n="1"))

        for i in range(1, args.client_count + 1):
            f.write(client_node_template.format(n=str(i), env=environment_variables))

    try:
        subprocess.run(["docker-compose", "-f", f.name, "down"])
        subprocess.run(["docker-compose", "-f", f.name, "up", "--build"])
    except Exception:
        pass
    finally:
        os.remove(f.name)


if __name__ == "__main__":
    main(parse_args())
