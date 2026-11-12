#!/usr/bin/env bash
# Run once on your own machine. Keeps the private signing key out of git.
set -euo pipefail
repo=soltros/ubuntu_packages
command -v gh >/dev/null
command -v gpg >/dev/null
gh auth status
key_home=$(mktemp -d)
chmod 700 "$key_home"
trap 'rm -rf "$key_home"' EXIT
# A dedicated unattended key: repository secret access controls its use.
gpg --homedir "$key_home" --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key 'Soltros Ubuntu Archive <packages@soltros.info>' rsa4096 sign 0
fingerprint=$(gpg --homedir "$key_home" --with-colons --list-secret-keys | awk -F: '$1=="fpr" {print $10; exit}')
gpg --homedir "$key_home" --armor --export-secret-keys "$fingerprint" | gh secret set APT_SIGNING_KEY --repo "$repo"
gh variable set APT_SIGNING_KEY_ID --repo "$repo" --body "$fingerprint"
printf 'Signing key configured: %s\nSave this fingerprint for client verification.\n' "$fingerprint"
# Export a local backup before the temporary keyring is removed.
backup="soltros-ubuntu-signing-${fingerprint}.asc"
(umask 077; gpg --homedir "$key_home" --armor --export-secret-keys "$fingerprint" > "$backup")
printf 'Private backup saved to %s. Store it securely; never commit it.\n' "$backup"
gh workflow run build.yml --repo "$repo"
