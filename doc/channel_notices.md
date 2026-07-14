# Channel notices

Channel notices are short messages shown to conda users who consume packages from your channel. Use the Anaconda CLI to create, publish, and manage notices for a channel owner account.

## Command path

```bash
anaconda channel notice <subcommand> ...
```

Notices are nested under the `channel` command (same group as repocore channel management). For local development with the standalone client:

```bash
ANACONDA_CLIENT_FORCE_STANDALONE=1 binstar channel notice <subcommand> ...
```

## Channel argument

`<channel>` is the **owner login** (user or organization account), for example `user` or `myorg`. It is not a repocore namespace path such as `myorg/dev`.

Pass the owner login as a positional argument:

```bash
anaconda channel notice list myorg
```

Or use `-n` / `--namespace` instead of the positional channel:

```bash
anaconda channel notice list --namespace myorg
```

For lifecycle commands (`get`, `update`, `publish`, `archive`, `delete`), you can pass the notice UUID as the only positional argument when using `--namespace`:

```bash
anaconda channel notice archive -n myorg 550e8400-e29b-41d4-a716-446655440000
```

Either a positional channel or `--namespace` is required.

## Notice IDs

The server assigns a UUID when you create a notice. The CLI prints the new ID on success:

```text
Notice '550e8400-e29b-41d4-a716-446655440000' created successfully (draft).
Find notice IDs with: anaconda channel notice list mychannel
```

Use `list` to look up IDs for existing notices. Commands that target a single notice (`get`, `update`, `publish`, `archive`, `delete`) require a valid UUID.

## Notice lifecycle

| Status | Meaning |
|--------|---------|
| **draft** | Created but not visible to conda clients |
| **published** | Live on the channel until `expires_at` |
| **archived** | No longer shown to users; retained for admin history |
| **deleted** | Soft-deleted |

Typical workflow:

1. **Create** a draft notice (note the printed UUID).
2. **Publish** it (or confirm when prompted interactively).
3. **Verify** with `notice list <channel> --status published`.
4. **Archive** or **delete** when no longer needed.

Publish and archive are idempotent (re-running returns success, not conflict).

## Subcommands

### `list` — admin view (paginated)

```bash
anaconda channel notice list user
anaconda channel notice list myorg
anaconda channel notice list user --status draft
anaconda channel notice list user --status published
anaconda channel notice list user --offset 20 --limit 20
```

Calls `GET /{channel}/notices`. Shows all notices for the channel owner, including drafts. Use `--status` to filter (`draft`, `published`, or `archived`).

### `get` — single notice details

```bash
anaconda channel notice get user 550e8400-e29b-41d4-a716-446655440000
```

### `create` — create a draft

```bash
anaconda channel notice create mychannel \
  --message "Scheduled maintenance tonight" \
  --level warning \
  --expires-after 30
```

| Option | Description |
|--------|-------------|
| `--message` | Notice text (required, max 256 characters) |
| `--level` | `info` (default), `warning`, or `critical` |
| `--expires-after DAYS` | Expire N days from now |
| `--expires-at` | Exact expiry (ISO 8601, e.g. `2026-09-16T12:00:00+00:00`) |

`--expires-after` and `--expires-at` are mutually exclusive. Do not send `notice_id` — the server assigns a UUID.

After create, the CLI prints the server-assigned UUID and a `list` command to find notice IDs. Interactive sessions ask whether to publish immediately. Non-interactive runs also print the exact publish command to run next.

### `update` — partial update

```bash
anaconda channel notice update user 550e8400-e29b-41d4-a716-446655440000 --message "Updated text"
anaconda channel notice update user 550e8400-e29b-41d4-a716-446655440000 --expires-after 14
anaconda channel notice update user 550e8400-e29b-41d4-a716-446655440000 --status published
```

At least one of `--message`, `--level`, `--expires-at`, `--expires-after`, or `--status` is required (non-interactive). `--status` accepts `published` or `archived` only; use `publish`, `archive`, or `delete` for lifecycle changes.

### `publish` — make a notice visible to channel users

```bash
anaconda channel notice publish user 550e8400-e29b-41d4-a716-446655440000
```

Publishes a **draft** or **archived** notice so conda clients can see it. Idempotent — re-publishing an already-published notice also succeeds.

### `archive` — stop showing a notice to channel users

```bash
anaconda channel notice archive user 550e8400-e29b-41d4-a716-446655440000
```

Archives a **published** notice (or no-ops if already **archived**). Removes it from the public channel view while retaining it in admin history.

### `delete` — soft-delete

```bash
anaconda channel notice delete user 550e8400-e29b-41d4-a716-446655440000
anaconda channel notice delete user 550e8400-e29b-41d4-a716-446655440000 --force
```

Prompts for confirmation unless `--force` is passed.

## Interactive create

When run without required flags in a terminal:

```bash
anaconda channel notice create mychannel
```

You are prompted for message, level, and expiry. Expiry accepts:

- Days: `30` or `30d`
- ISO 8601: `2026-09-16T12:00:00+00:00`

After three blank expiry attempts, you are offered a default period of 30 days.

## Examples

```bash
# Create and get publish instructions (non-interactive)
anaconda channel notice create mychannel \
  --message "New signing keys rolling out next week" \
  --expires-after 7

# Publish (use the UUID printed by create, or list to find it)
anaconda channel notice publish mychannel 550e8400-e29b-41d4-a716-446655440000

# List published notices
anaconda channel notice list mychannel --status published

# List drafts for an organization
anaconda channel notice list myorg --status draft
```

## API

Admin commands use your configured API site (`--site` / login default) via `GET /{owner}/notices`, `POST /{owner}/notices`, and related endpoints. Authentication uses your normal `anaconda login` token.
