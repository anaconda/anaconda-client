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

Use `-o` / `--organization` when managing notices for an organization you belong to without passing the channel as a positional argument:

```bash
anaconda channel notice list -o myorg
```

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
3. **Verify** with `notice published` (what end users see).
4. **Archive** or **delete** when no longer needed.

## Subcommands

### `list` — admin view (paginated)

```bash
anaconda channel notice list user
anaconda channel notice list myorg
anaconda channel notice list user --status draft
anaconda channel notice list user --offset 20 --limit 20
```

Shows all notices for the channel owner, including drafts. Use `--status` to filter.

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
| `--expires-at` | Exact expiry (ISO 8601, e.g. `2026-09-16T12:00:00Z`) |

`--expires-after` and `--expires-at` are mutually exclusive.

After create, the CLI prints the server-assigned UUID and a `list` command to find notice IDs. Interactive sessions ask whether to publish immediately. Non-interactive runs also print the exact publish command to run next.

### `update` — partial update

```bash
anaconda channel notice update user 550e8400-e29b-41d4-a716-446655440000 --message "Updated text"
anaconda channel notice update user 550e8400-e29b-41d4-a716-446655440000 --expires-after 14
```

At least one of `--message`, `--level`, `--expires-at`, or `--expires-after` is required (non-interactive).

### `publish` — make a draft visible

```bash
anaconda channel notice publish user 550e8400-e29b-41d4-a716-446655440000
```

### `archive` — stop showing a published notice

```bash
anaconda channel notice archive user 550e8400-e29b-41d4-a716-446655440000
```

### `delete` — soft-delete

```bash
anaconda channel notice delete user 550e8400-e29b-41d4-a716-446655440000
anaconda channel notice delete user 550e8400-e29b-41d4-a716-446655440000 --force
```

Prompts for confirmation unless `--force` is passed.

### `published` — public view (what conda clients see)

```bash
anaconda channel notice published user
```

No authentication required. Returns published, non-expired notices only.

## Interactive create

When run without required flags in a terminal:

```bash
anaconda channel notice create mychannel
```

You are prompted for message, level, and expiry. Expiry accepts:

- Days: `30` or `30d`
- ISO 8601: `2026-09-16T12:00:00Z`

After three blank expiry attempts, you are offered a default period of 30 days.

## Examples

```bash
# Create and get publish instructions (non-interactive)
anaconda channel notice create mychannel \
  --message "New signing keys rolling out next week" \
  --expires-after 7

# Publish (use the UUID printed by create, or list to find it)
anaconda channel notice publish mychannel 550e8400-e29b-41d4-a716-446655440000

# Confirm what users see
anaconda channel notice published mychannel

# List drafts for an organization
anaconda channel notice list myorg --status draft
```

## API

These commands call the dot-org admin REST API (`/notices`, `/{owner}/notices`, etc.). Authentication uses your normal `anaconda login` token. Point at a specific site with `--site` / `-s` when needed.
