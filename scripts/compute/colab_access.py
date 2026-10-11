#!/usr/bin/env python3
"""Colab CLI 0.7.4 with identity + Colab permission only.

Upstream issue: https://github.com/googlecolab/google-colab-cli/issues/116
Use this entry point for every project Colab command, including token refresh.
It does not relax scope validation or bypass the user's consent.
"""
from importlib.metadata import distribution
import os
from pathlib import Path

SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/colaboratory",
)


def main():
    package = distribution("google-colab-cli")
    if package.version != "0.7.4":
        raise RuntimeError("This compatibility launcher requires google-colab-cli==0.7.4")
    import colab_cli.auth as auth
    # A distinct file prevents the stock CLI from refreshing this token with
    # its broader scope list. Never copy or print the credential contents.
    auth.PUBLIC_SCOPES = list(SCOPES)
    auth.TOKEN_CONFIG_PATH = str(Path.home() / ".config/colab-cli/colab-only-token.json")
    os.umask(0o077)
    entry = next(e for e in package.entry_points if e.group == "console_scripts" and e.name == "colab")
    entry.load()()


if __name__ == "__main__":
    main()
