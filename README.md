<!-- SPDX-FileCopyrightText: 2026 Matej Kovac -->
<!-- SPDX-License-Identifier: MIT -->

# User Role

Manage a single local user account, including optional subordinate UID/GID ranges for rootless containers.

## Usage

```yaml
- name: Create user
  ansible.builtin.include_role:
    name: local_user
  vars:
    local_user_name: alice
    local_user_group: alice
    local_user_shell: /bin/bash
    local_user_create_home: true
    local_user_groups: [sudo]
    local_user_subuid_count: 65536
    local_user_subgid_count: 65536
```

Remove a user:

```yaml
- name: Remove user
  ansible.builtin.include_role:
    name: local_user
  vars:
    local_user_name: alice
    local_user_state: absent
    local_user_remove: true
```

## Variables

All variables map directly to `ansible.builtin.user` arguments unless noted.
Unset optional values default to `omit`.

| Variable | Default | Description |
|---|---|---|
| `local_user_state` | `present` | `present` or `absent` |
| `local_user_name` | required | Account name |
| `local_user_group` | `users` | Primary group |
| `local_user_groups` | `[]` | Supplementary groups |
| `local_user_groups_append` | `false` | Append to existing groups |
| `local_user_comment` | `ansible managed user` | GECOS field |
| `local_user_home` | omit | Home directory path |
| `local_user_create_home` | `true` | Create home directory |
| `local_user_move_home` | `false` | Move home when changed |
| `local_user_shell` | `/bin/bash` | Login shell |
| `local_user_uid` | omit | Fixed UID |
| `local_user_uid_min` / `local_user_uid_max` | omit | UID range for allocation |
| `local_user_non_unique` | `false` | Allow duplicate UID |
| `local_user_password` | omit | Password hash |
| `local_user_update_password` | `always` | `always` or `on_create` |
| `local_user_password_lock` | omit | Lock password |
| `local_user_password_expire_min/max/warn` | omit | Password expiry |
| `local_user_password_expire_account_disable` | omit | Disable on expiry |
| `local_user_expires` | omit | Account expiry (epoch) |
| `local_user_force` | `false` | Force removal |
| `local_user_remove` | `false` | Remove home on absent |
| `local_user_profile` | omit | SELinux profile |
| `local_user_role` | omit | SELinux role |
| `local_user_seuser` | omit | SELinux user |
| `local_user_skeleton` | omit | Skeleton directory |
| `local_user_umask` | omit | Home umask |
| `local_user_subuid_count` | unset | Subordinate UID range size |
| `local_user_subgid_count` | unset | Subordinate GID range size |

## Subordinate ID allocation

When `local_user_subuid_count` or `local_user_subgid_count` is set, the role runs
`files/allocate-subids.py` to allocate non-overlapping ranges in
`/etc/subuid` and `/etc/subgid` under a file lock. Existing ranges for the
user are reused when still valid; otherwise the first free gap is used.

## Security considerations

- Accounts are created locked unless `local_user_password` is provided.
- Home directory permissions follow `ansible.builtin.user` defaults.
- Subordinate ID files are updated atomically with preserved ownership and
  mode.

## Dependencies

None (uses `ansible.builtin.user`, `ansible.builtin.group`, `ansible.builtin.script`, `ansible.builtin.lineinfile`).

## Installation

No Galaxy account needed. Add to `requirements.yml`:

```yaml
roles:
  - name: local_user
    src: https://github.com/multicast/ansible-role-local-user.git
    version: master
```

And run:

```bash
ansible-galaxy role install -r requirements.yml --verbose --verbose

# alternatively without the file:
ansible-galaxy role install git+https://github.com/multicast/ansible-role-local-user.git
mv roles/ansible-role-local-user roles/local_user
```

## Requirements

- Ansible 2.15+
- Target: Linux (Debian/Ubuntu/EL) with `/etc/login.defs` and `/etc/subuid`

## License

MIT
